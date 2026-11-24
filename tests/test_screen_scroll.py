import unittest
from unittest.mock import Mock, patch
from threading import Event
from types import SimpleNamespace

from iphone_assistant.screen_scroll import scroll_screen, scroll_snapshot, moved
from iphone_assistant.direct import parse_direct_command
from iphone_assistant.intent import ModelIntent, validate_intent, IntentError


def xml(offset=0):
    return '<root><XCUIElementTypeTable visible="true">' + ''.join(
        f'<XCUIElementTypeStaticText label="row{i}" visible="true" y="{100+i*60+offset}"/>'
        for i in range(4)) + '</XCUIElementTypeTable></root>'


class ScrollTests(unittest.TestCase):
    def setUp(self):
        self.backend = Mock()
        self.backend.request.return_value = {'value': False}
        self.backend.active_bundle.return_value = 'example.app'
        self.scrolls = 0
        self.offset = -40
        self.backend.session_request.side_effect = self.request

    def request(self, method, path, payload=None):
        if path == '/source':
            return {'value': xml(self.offset if self.scrolls else 0)}
        self.assertEqual((method, path), ('POST', '/wda/scroll'))
        self.scrolls += 1
        return {'value': None}

    def run_scroll(self, direction='down', **kw):
        with patch('iphone_assistant.screen_scroll.time.sleep'):
            return scroll_screen(direction, backend_factory=lambda: self.backend, **kw)

    def test_down_and_up(self):
        self.assertEqual(self.run_scroll().status, 'verified_match')
        self.assertEqual(self.scrolls, 1)
        self.scrolls = 0; self.offset = 40
        self.assertEqual(self.run_scroll('up').status, 'verified_match')
        self.assertEqual(self.scrolls, 1)

    def test_edge_does_not_retry_or_claim_success(self):
        self.offset = 0
        self.assertEqual(self.run_scroll().status, 'verification_uncertain')
        self.assertEqual(self.scrolls, 1)

    def test_wrong_direction_is_not_verified(self):
        self.offset = 40
        self.assertEqual(self.run_scroll().status, 'verification_uncertain')

    def test_timeout_is_not_replayed(self):
        original = self.request
        def request(m, p, v=None):
            if p == '/wda/scroll':
                self.scrolls += 1
                raise TimeoutError()
            return original(m, p, v)
        self.backend.session_request.side_effect = request
        result = self.run_scroll()
        self.assertEqual(result.status, 'verification_uncertain')
        self.assertFalse(result.action_acknowledged)
        self.assertEqual(self.scrolls, 1)

    def test_cancel_preview_and_invalid_direction_do_not_connect(self):
        stop = Event(); stop.set()
        self.assertEqual(self.run_scroll(stop_event=stop).status, 'canceled')
        self.assertEqual(self.run_scroll(dry_run=True).status, 'dry_run')
        self.assertEqual(self.run_scroll('left').status, 'needs_clarification')
        self.backend.request.assert_not_called()

    def test_foreground_change_blocks_scroll(self):
        self.backend.active_bundle.side_effect = ['example.app', 'other.app']
        self.assertEqual(self.run_scroll().status, 'target_not_found')
        self.assertEqual(self.scrolls, 0)

    def test_multiple_regions_or_no_region_rejected(self):
        self.assertIsNone(scroll_snapshot('<root>' + xml() + xml() + '</root>'))
        self.assertIsNone(scroll_snapshot('<root/>'))

    def test_text_changes_alone_do_not_verify(self):
        before = scroll_snapshot(xml())
        after = scroll_snapshot(xml().replace('row', 'new'))
        self.assertFalse(moved(before, after, 'down'))

    def test_parser_and_intent(self):
        self.assertEqual(parse_direct_command('scroll down').arguments, {'direction': 'down'})
        item = ModelIntent(decision='action', action='scroll', direction='none', value='up', message='')
        self.assertEqual(validate_intent(item).command.arguments, {'direction': 'up'})
        with self.assertRaises(IntentError):
            validate_intent(item.model_copy(update={'value': 'left'}))

    def test_app_routes_without_confirmation(self):
        from iphone_assistant.direct_cli import run_turn
        with patch('iphone_assistant.screen_scroll.scroll_screen') as scroll, patch('builtins.input', side_effect=AssertionError):
            args = SimpleNamespace(auto=True, listen=False, ai=False, execute=True)
            self.assertIs(run_turn(args, 'scroll down'), scroll.return_value)
        scroll.assert_called_once_with('down', stop_event=None, on_event=None, dry_run=False)
