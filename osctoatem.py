import PyATEMMax
from pythonosc.dispatcher import Dispatcher
import click
from pythonosc.osc_server import BlockingOSCUDPServer
from mapper import Mapper
import structlog

@click.command()
@click.option('--port', '-p', default=1337, type=int, help='Port to listen for OSC messages on (default: 1337)')
@click.option('--switcher', '-s', required=True, help='IP address of the ATEM switcher to connect to')
@click.option('--skip-connect-check', is_flag=True, help='Skip connection check to ATEM switcher')
def main(port, switcher, skip_connect_check):
    """OSC to ATEM Bridge - Receive OSC messages and control ATEM switcher"""
    
    # Initialize logger
    logger = structlog.get_logger("osctoatem")
    
    # Initialize ATEM switcher connection
    atem = PyATEMMax.ATEMMax()
    
    try:
        logger.info("Connecting to ATEM switcher", switcher_ip=switcher)
        atem.connect(switcher)
        if not skip_connect_check:
            # Wait for connection to be established
            atem.waitForConnection()
        logger.info("Connected to ATEM switcher successfully", switcher_ip=switcher)
    except Exception as e:
        logger.error("Failed to connect to ATEM switcher", 
                    switcher_ip=switcher, 
                    error=str(e),
                    error_type=type(e).__name__)
        return
    
    # Create dispatcher with switcher reference
    dispatcher = Dispatcher()
    mapper = Mapper(atem)
    
    # Map all OSC messages to the generic handler
    dispatcher.set_default_handler(mapper.handle_osc_message)
    logger.info("OSC dispatcher created", port=port)

    try:
        server = BlockingOSCUDPServer(("0.0.0.0", port), dispatcher)
        logger.info("OSC server started", port=port, bind_address="0.0.0.0")
    
        logger.info("OSC to ATEM bridge running", status="ready")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error("Server error occurred", 
                    error=str(e),
                    error_type=type(e).__name__)
    finally:
        # Disconnect from switcher
        if atem:
            atem.disconnect()
            logger.info("Disconnected from ATEM switcher")


if __name__ == '__main__':
    main()