from typing import List, Any, Dict, Callable
import structlog
import inspect


class Mapper:
    """Maps OSC messages to ATEM switcher commands"""
    
    def __init__(self, switcher):
        """Initialize the mapper with an ATEM switcher instance
        
        Args:
            switcher: PyATEMMax.ATEMMax instance for controlling the switcher
        """
        self.switcher = switcher
        self.logger = structlog.get_logger("mapper")
        self._method_cache = {}
        self._discover_atem_methods()
    
    def _discover_atem_methods(self):
        """Discover all available ATEM methods and cache them"""
        for attr_name in dir(self.switcher):
            attr = getattr(self.switcher, attr_name)
            if callable(attr) and not attr_name.startswith('_'):
                # Store method reference and signature info
                try:
                    sig = inspect.signature(attr)
                    self._method_cache[attr_name.lower()] = {
                        'method': attr,
                        'signature': sig,
                        'name': attr_name
                    }
                except (ValueError, TypeError):
                    # Skip methods we can't inspect
                    pass
        
        self.logger.info("Discovered ATEM methods", method_count=len(self._method_cache))
    
    def _find_method(self, osc_address: str) -> Dict:
        """Find the best matching ATEM method for an OSC address
        
        Args:
            osc_address: OSC address like "/cut", "/setCutTransition", "/setPreviewInput"
            
        Returns:
            Dict with method info or None if not found
        """
        # Remove leading slash and convert to lowercase
        clean_address = osc_address.lstrip('/').lower()
        
        # Direct match first
        if clean_address in self._method_cache:
            return self._method_cache[clean_address]
        
        # Try with common prefixes
        prefixes = ['exec', 'set', 'get']
        for prefix in prefixes:
            prefixed = f"{prefix}{clean_address}"
            if prefixed in self._method_cache:
                return self._method_cache[prefixed]
        
        # Try partial matches (find methods containing the address)
        for method_name, method_info in self._method_cache.items():
            if clean_address in method_name:
                return method_info
        
        return None
    
    def handle_osc_message(self, address: str, *args: List[Any]) -> None:
        """Generic OSC message handler that routes to appropriate ATEM methods
        """
        self.logger.info("OSC message received", address=address, args=args)
        
        # If address begins with "/raw", handle it directly
        if address.startswith("/raw"):
            # Remove "/raw" prefix and handle as raw OSC message
            raw_address = address[4:]
            return self.handle_raw_osc_message(raw_address, *args)
        

    def handle_raw_osc_message(self, address: str, *args: List[Any]) -> None:
        """Parse and handle raw OSC messages, routing to ATEM methods
        
        Args:
            address: OSC address (e.g., "/cut", "/setPreviewInput")
            *args: Arguments from the OSC message
        """
        self.logger.info("Raw OSC message received", address=address, args=args)
        
        # Handle special cases first
        if address == "/ping":
            self.logger.info("Ping received", address=address)
            return
        
        # Find matching ATEM method
        method_info = self._find_method(address)
        if not method_info:
            self.logger.warning("No matching ATEM method found", address=address)
            return
        
        method = method_info['method']
        signature = method_info['signature']
        method_name = method_info['name']
        
        try:
            # Analyze the method signature to determine how to call it
            params = list(signature.parameters.keys())
            
            # Special handling for common ATEM patterns
            if len(params) == 1 and len(args) >= 1:
                # Single parameter methods
                method_type = "Single parameter"
                result = method(args[0])
            elif len(params) == len(args):
                # Direct parameter mapping
                method_type = "Direct parameters"
                result = method(*args)
            elif len(params) == 0:
                # No parameter methods
                method_type = "No parameters"
                result = method()
            else:
                # Try to call with available args, let the method handle errors
                method_type = "Partial parameters"
                result = method(*args[:len(params)])
            
            self.logger.info("ATEM method executed successfully", 
                           address=address,
                           method=method_name,
                           args=args,
                           method_type=method_type,
                           result=result,
                           params=params)
            
        except Exception as e:
            self.logger.error("Error executing ATEM method", 
                            address=address,
                            method=method_name,
                            args=args,
                            error=str(e),
                            error_type=type(e).__name__)
            raise
    
    def get_available_methods(self) -> List[str]:
        """Get list of all available ATEM methods that can be called via OSC"""
        return [f"/{name}" for name in self._method_cache.keys()]