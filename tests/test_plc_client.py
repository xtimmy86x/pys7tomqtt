import struct
import unittest

from plc_client import PlcClient


class FakeSnap7Client:
    def __init__(self, data_map, raise_on=None):
        self.data_map = data_map
        self.raise_on = raise_on

    def read_area(self, area, dbnumber, start, size):
        key = (dbnumber, start, size)
        if self.raise_on == key:
            raise RuntimeError("read error")
        return self.data_map[key]


class PlcClientReadAllTest(unittest.TestCase):
    def test_read_all_parses_and_converts(self):
        data_map = {
            (1, 0, 1): bytes([0b00000001]),
            (1, 2, 2): (123).to_bytes(2, "big", signed=True),
            (1, 4, 4): struct.pack(">f", 3.14),
        }
        client = FakeSnap7Client(data_map)
        plc = PlcClient({}, client=client)
        plc.add_item("bool/topic", "DB1.DBX0.0")
        plc.add_item("int/topic", "DB1.DBW2")
        plc.add_item("float/topic", "DB1.DBD4")
        result = plc.read_all()
        self.assertTrue(result["bool/topic"])
        self.assertEqual(result["int/topic"], 123)
        self.assertAlmostEqual(result["float/topic"], 3.14, places=5)

    def test_connection_error_logged_and_skipped(self):
        client = FakeSnap7Client({}, raise_on=(1, 0, 1))
        plc = PlcClient({}, client=client)
        plc.add_item("bad/topic", "DB1.DBX0.0")
        with self.assertLogs(level="ERROR") as cm:
            result = plc.read_all()
        self.assertNotIn("bad/topic", result)
        self.assertTrue(any("Failed to read address" in msg for msg in cm.output))


if __name__ == "__main__":
    unittest.main()

