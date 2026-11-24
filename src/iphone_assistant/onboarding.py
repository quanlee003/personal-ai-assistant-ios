"""Local setup progress, never permission to collect usage reports."""
import json

from .direct_cli import PROJECT_ROOT


class SetupPreferences:
    def __init__(self, path=None):
        self.path = path or PROJECT_ROOT / 'runtime/setup-preferences.json'
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            values = data.get('screen_time_prompt_dismissed', []) if isinstance(data, dict) else []
            self.dismissed = {v for v in values if isinstance(v, str)} if isinstance(values, list) else set()
        except (OSError, ValueError, TypeError):
            self.dismissed = set()

    def finish(self, device_key):
        updated = self.dismissed | {device_key}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'screen_time_prompt_dismissed': sorted(updated)}), encoding='utf-8')
        temporary.replace(self.path)
        self.dismissed = updated


def setup_step(readiness, catalog, dismissed):
    if readiness is None or catalog is None:
        return 'checking'
    if catalog.get('status') != 'scanned':
        return 'connection'
    if not readiness.phone:
        return 'phone'
    if not readiness.microphone:
        return 'microphone'
    if not readiness.services:
        return 'services'
    if catalog.get('device_key') not in dismissed:
        return 'personalization'
    return 'ready'
