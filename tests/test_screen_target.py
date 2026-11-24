import unittest
from unittest.mock import Mock, patch
from threading import Event
from types import SimpleNamespace

from iphone_assistant.screen_target import candidates, open_screen_item, choose_target
from iphone_assistant.commands import Command
from iphone_assistant.intent import IntentResult
from iphone_assistant.screen_navigation import navigation_titles


def xml(label='Categories', title='Home', extra='', y=200):
    return f'''<root><XCUIElementTypeWindow visible="true" x="0" y="0" width="400" height="900">
    <XCUIElementTypeNavigationBar visible="true" name="{title}"/>
    <XCUIElementTypeTable><XCUIElementTypeOther visible="false">
    <XCUIElementTypeButton label="{label}" visible="true" enabled="true" x="20" y="{y}" width="360" height="50">{extra}</XCUIElementTypeButton>
    </XCUIElementTypeOther></XCUIElementTypeTable></XCUIElementTypeWindow></root>'''


class TargetTests(unittest.TestCase):
    def setUp(self):
        self.b = Mock()
        self.b.request.return_value = {'value': False}
        self.b.active_bundle.return_value = 'example.app'
        self.clicks = 0
        self.title = 'Categories'
        self.b.session_request.side_effect = self.request
        self.chooser = Mock(side_effect=lambda target, items: items[0])

    def request(self, method, path, payload=None):
        if path == '/source':
            return {'value': xml(title=self.title if self.clicks else 'Home')}
        if path == '/elements':
            return {'value': [{'ELEMENT': 'item'}]}
        if '/attribute/' in path:
            return {'value': {'label': 'Categories', 'type': 'XCUIElementTypeButton', 'visible': True, 'enabled': True}[path.rsplit('/', 1)[1]]}
        if path.endswith('/click'):
            self.clicks += 1
            return {'value': None}
        raise AssertionError(path)

    def run_item(self, **kw):
        with patch('iphone_assistant.screen_target.time.sleep'):
            return open_screen_item('Categories', backend_factory=lambda: self.b, chooser=self.chooser, **kw)

    def test_select_and_verify_one_click(self):
        self.assertEqual(self.run_item().status, 'verified_match')
        self.assertEqual(self.clicks, 1)
        self.chooser.assert_called_once()

    def test_risky_controls_and_switch_rows_excluded(self):
        for label in ('Delete', 'Send', 'Buy', 'Allow', 'Save', 'Install'):
            self.assertEqual(candidates(xml(label=label)), [])
        self.assertEqual(candidates(xml(extra='<XCUIElementTypeSwitch/>')), [])

    def test_secure_screen_excluded(self):
        self.assertEqual(candidates(xml(extra='<XCUIElementTypeSecureTextField visible="true"/>')), [])

    def test_overlay_blocks_background_items_before_cloud(self):
        for kind in ('XCUIElementTypeAlert', 'XCUIElementTypeSheet', 'XCUIElementTypeKeyboard'):
            source = xml().replace('</root>', f'<{kind} visible="true"/></root>')
            self.b.session_request.side_effect = lambda *args: {'value': source}
            self.assertEqual(self.run_item().status, 'target_not_found')
        self.chooser.assert_not_called()
        self.assertEqual(self.clicks, 0)

    def test_overlay_appearing_during_ai_blocks_click(self):
        def choose(target, items):
            source = xml().replace('</root>', '<XCUIElementTypeAlert visible="true"/></root>')
            self.b.session_request.side_effect = lambda *args: {'value': source}
            return items[0]
        self.chooser.side_effect = choose
        self.assertEqual(self.run_item().status, 'target_not_found')
        self.assertEqual(self.clicks, 0)

    def test_bottom_edge_excluded(self):
        self.assertEqual(candidates(xml(y=800)), [])

    def test_child_label_disambiguates_shared_internal_identifier(self):
        def row(title):
            return xml(label='', extra=f'<XCUIElementTypeStaticText label="{title}" visible="true"/>').replace('label=""', 'name="shared_internal_id"')
        items = candidates('<root>' + row('Account') + row('Privacy') + '</root>')
        self.assertEqual([i['label'] for i in items], ['Account', 'Privacy'])
        self.assertNotEqual(items[0]['selector'], items[1]['selector'])
        self.assertEqual(items[0]['identity'], ('name', 'shared_internal_id'))

    def test_navigation_title_uses_visible_text_not_internal_name(self):
        self.assertEqual(navigation_titles('<root><XCUIElementTypeNavigationBar name="internal_bar" visible="true"><XCUIElementTypeStaticText label="Account" visible="true"/></XCUIElementTypeNavigationBar></root>'), ('Account',))

    def test_internal_id_alone_or_multiple_child_labels_not_sent_to_ai(self):
        source = xml(label='').replace('label=""', 'name="internal_id"')
        self.assertEqual(candidates(source), [])
        source = xml(label='', extra='<XCUIElementTypeStaticText label="A" visible="true"/><XCUIElementTypeStaticText label="B" visible="true"/>').replace('label=""', 'name="internal_id"')
        self.assertEqual(candidates(source), [])

    def test_invisible_layout_ancestor_does_not_hide_visible_item(self):
        self.assertEqual(len(candidates(xml())), 1)

    def test_model_cannot_invent_target(self):
        with patch('iphone_assistant.screen_target.understand_intent', return_value=IntentResult('action', Command('select_target', {'target': '999'}), '')):
            self.assertIsNone(choose_target('Categories', candidates(xml())))
        self.chooser.return_value = None; self.chooser.side_effect = None
        self.assertEqual(self.run_item().status, 'needs_clarification')
        self.assertEqual(self.clicks, 0)

    def test_changed_app_during_model_call_blocks_click(self):
        def choose(target, items):
            self.b.active_bundle.return_value = 'another.app'
            return items[0]
        self.chooser.side_effect = choose
        self.assertEqual(self.run_item().status, 'target_not_found')
        self.assertEqual(self.clicks, 0)

    def test_duplicate_element_match_blocks_click(self):
        original = self.request
        self.b.session_request.side_effect = lambda m, p, v=None: {'value': [{'ELEMENT': 'a'}, {'ELEMENT': 'b'}]} if p == '/elements' else original(m, p, v)
        self.assertEqual(self.run_item().status, 'target_not_found')
        self.assertEqual(self.clicks, 0)

    def test_wrong_destination_is_not_success(self):
        self.title = 'Unrelated'
        self.assertEqual(self.run_item().status, 'verification_uncertain')
        self.assertEqual(self.clicks, 1)

    def test_timeout_never_replays(self):
        original = self.request
        def request(m, p, v=None):
            if p.endswith('/click'):
                self.clicks += 1
                raise TimeoutError()
            return original(m, p, v)
        self.b.session_request.side_effect = request
        self.assertEqual(self.run_item().status, 'verification_uncertain')
        self.assertEqual(self.clicks, 1)

    def test_cancel_and_preview_do_not_call_cloud_or_device(self):
        stop = Event(); stop.set()
        self.assertEqual(self.run_item(stop_event=stop).status, 'canceled')
        self.assertEqual(self.run_item(dry_run=True).status, 'dry_run')
        self.b.request.assert_not_called(); self.chooser.assert_not_called()

    def test_pipeline_routes_item_without_extra_confirmation(self):
        from iphone_assistant.direct_cli import run_turn
        with patch('iphone_assistant.screen_target.open_screen_item') as run, patch('builtins.input', side_effect=AssertionError):
            args = SimpleNamespace(auto=True, listen=False, ai=False, execute=True)
            self.assertIs(run_turn(args, 'open item Categories'), run.return_value)
        run.assert_called_once_with('Categories', stop_event=None, on_event=None, dry_run=False)
