import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from scripts.direct_doctor import inspect_device, wda_candidates


class DoctorTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_or_multiple_devices_never_connect(self):
        create = AsyncMock()
        for devices in ([], [SimpleNamespace(connection_type="USB")] * 2):
            result = await inspect_device(devices, create, Mock())
            self.assertFalse(result["direct_action_verified"])
        create.assert_not_awaited()

    async def test_unpaired_never_installs_or_pairs(self):
        client = AsyncMock()
        client.paired = False
        client.get_value.return_value = "test"
        create = AsyncMock(return_value=client)
        service = Mock()
        result = await inspect_device(
            [SimpleNamespace(connection_type="USB", serial="private")], create, service)
        create.assert_awaited_once_with(serial="private", autopair=False)
        service.assert_not_called()
        self.assertFalse(result["direct_action_verified"])
        self.assertNotIn("private", str(result))

    async def test_open_port_is_not_verified_and_no_retry(self):
        client = AsyncMock()
        client.paired = True
        client.get_value.return_value = True
        service = AsyncMock()
        service.__aenter__.return_value = service
        service.browse.return_value = []
        connection = Mock()
        device = SimpleNamespace(connection_type="USB", serial="private",
                                 connect=AsyncMock(return_value=connection))
        result = await inspect_device([device], AsyncMock(return_value=client),
                                      Mock(return_value=service))
        self.assertEqual(result["device_port_8100"], "open_unverified_service")
        self.assertFalse(result["direct_action_verified"])
        device.connect.assert_awaited_once_with(8100)
        connection.close.assert_called_once()

    def test_only_candidate_ids_returned(self):
        self.assertEqual(wda_candidates([
            {"CFBundleIdentifier": "private.app"},
            {"CFBundleIdentifier": "example.xctrunner", "private": "secret"}
        ]), ["example.xctrunner"])


if __name__ == "__main__":
    unittest.main()
