import unittest
import pys7tomqtt.plc_client as pc
pc.snap7 = None

from pys7tomqtt.devices.sensor import SensorDevice
from pys7tomqtt.mqtt_client import MqttClient
from pys7tomqtt.plc_client import PlcClient


class DummyMqtt(MqttClient):
    def __init__(self):
        super().__init__({}, client=None)


class DummyPlc(PlcClient):
    def __init__(self):
        super().__init__({}, client=None)


class SensorDeviceTest(unittest.TestCase):
    def test_detects_type_from_address(self):
        plc = DummyPlc()
        mqtt = DummyMqtt()
        config = {"type": "sensor", "name": "s", "state": "DB1.DBX0.0"}
        dev = SensorDevice(plc, mqtt, config)
        attr = dev.attributes.get("state")
        self.assertIsNotNone(attr)
        self.assertEqual(attr.type, "X")


if __name__ == "__main__":
    unittest.main()