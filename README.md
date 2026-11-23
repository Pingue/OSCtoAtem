# OSCtoAtem
OSC to Atem Bridge

## Docker

Images are published to `ghcr.io/pingue/osctoatem`. The ATEM switcher address is required:

```bash
docker run --rm -p 1337:1337/udp ghcr.io/pingue/osctoatem --switcher 192.168.1.10
```

Add `--hyperdeck <ip>` to control a HyperDeck too. The image is pinned to Python 3.12 because
`pyperdeck` needs `telnetlib`, which was removed in Python 3.13.

## Releases

Pushes to `main` are tested, then a semantic version is worked out from the
[Conventional Commits](https://www.conventionalcommits.org/) since the last tag: `feat` bumps
minor, `fix`/`perf` bump patch, and `!` or a `BREAKING CHANGE:` footer bumps major. Other types
(`docs`, `ci`, `chore`, ...) don't release. When there is something to release it publishes the
Docker image, tags the commit `vX.Y.Z` and creates a GitHub release.
