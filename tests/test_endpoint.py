import unittest
from iphone_assistant.endpoint import SilenceEndpoint


class EndpointTests(unittest.TestCase):
    def test_speech_then_silence_completes(self):
        endpoint = SilenceEndpoint()
        self.assertIsNone(endpoint.feed(900, .5))
        self.assertIsNone(endpoint.feed(0, .5))
        self.assertEqual(endpoint.feed(0, .8), 'complete')

    def test_pause_then_more_speech_resets_silence(self):
        endpoint = SilenceEndpoint()
        for level, duration in [(900, .5), (0, .8), (900, .5), (0, .8)]:
            self.assertIsNone(endpoint.feed(level, duration))
        self.assertEqual(endpoint.feed(0, .5), 'complete')

    def test_silence_or_short_click_is_not_speech(self):
        for level in [0, 1000]:
            endpoint = SilenceEndpoint()
            self.assertIsNone(endpoint.feed(level, .05))
            self.assertEqual(endpoint.feed(0, 8), 'no_speech')

    def test_continuous_noise_or_speech_cannot_exceed_limit(self):
        self.assertEqual(SilenceEndpoint().feed(1000, 20), 'too_long')
        endpoint = SilenceEndpoint()
        endpoint.feed(1000, 19)
        self.assertEqual(endpoint.feed(0, 2), 'too_long')


if __name__ == '__main__':
    unittest.main()
