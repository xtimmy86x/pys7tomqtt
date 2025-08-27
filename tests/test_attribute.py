import unittest
from attribute import Attribute
from mqtt_client import MqttClient
from plc_client import PlcClient

class DummyMqtt(MqttClient):
    def __init__(self):
        super().__init__({}, client=None)

class DummyPlc(PlcClient):
    def __init__(self):
        super().__init__({}, client=None)

class AttributeTest(unittest.TestCase):
    def test_format_message(self):
        attr = Attribute(DummyPlc(), DummyMqtt(), 'state', 'X', 'dev')
        self.assertEqual(attr.format_message('true', 'X')[1], True)
        self.assertEqual(attr.format_message('10', 'BYTE')[1], 10)
        self.assertAlmostEqual(attr.format_message('1.5', 'REAL')[1], 1.5)
        self.assertEqual(attr.format_message('foo', 'REAL')[0], -2)

    def test_rec_s7_data_publishes(self):
        mqtt = DummyMqtt()
        plc = DummyPlc()
        attr = Attribute(plc, mqtt, 'state', 'X', 'dev')
        attr.plc_address = 'DB1,X0.0'
        attr.subscribe_plc_updates()
        attr.rec_s7_data(True)
        self.assertEqual(mqtt.published[0][0], 'dev/state')
        self.assertEqual(mqtt.published[0][1], 'True')

if __name__ == '__main__':
    unittest.main()