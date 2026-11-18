"""Read-only readiness check through the configured WDA userspace tunnel."""
import argparse
import json

from iphone_assistant.wda import WDABackend


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    backend = WDABackend()
    ready = backend.ready()
    print(json.dumps({'status': 'ready' if ready else 'not_ready', 'wda_ready': ready}))
    if not ready:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
