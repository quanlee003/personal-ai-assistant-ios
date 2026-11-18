"""Single Settings smoke test, opt-in only. Local USB tunnel, no AI or TTS."""
import argparse
import json
from pathlib import Path
from uuid import uuid4
from iphone_assistant.wda import WDABackend as WDA


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-settings', action='store_true')
    args = parser.parse_args()
    wda = WDA()
    status = wda.request('GET', '/status')['value']
    if status.get('ready') is not True:
        raise RuntimeError('WDA not ready')
    if not args.execute_settings:
        print(json.dumps({'status': 'dry_run', 'wda_ready': True, 'action': 'open Settings'}))
        return
    folder = Path(__file__).resolve().parents[1] / 'captures' / ('direct-' + uuid4().hex[:8])
    folder.mkdir(parents=True)
    result = {'status': 'error', 'action': 'open Settings', 'action_attempted': False}
    try:
        result['before_sha256'] = wda.screenshot(folder / 'before.png')
        result['action_attempted'] = True
        response = wda.request('POST', '/session', {'capabilities': {'alwaysMatch': {
            'bundleId': 'com.apple.Preferences', 'shouldTerminateApp': False}}})
        result['status'] = 'action_sent'
        result['session_id'] = response.get('sessionId')
        result['after_sha256'] = wda.screenshot(folder / 'after.png')
        result['image_changed'] = result['before_sha256'] != result['after_sha256']
        # A successful API and changed pixels do not themselves verify Settings.
        result['status'] = 'verification_uncertain'
    except Exception as exc:
        result['error_type'] = type(exc).__name__
        result['status'] = 'verification_uncertain' if result['action_attempted'] else 'error'
    (folder / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    print('Evidence:', folder)


if __name__ == '__main__':
    main()
