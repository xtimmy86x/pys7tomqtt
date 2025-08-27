from .device import Device


class LightDevice(Device):
    """Simple light device exposing a binary state and optional brightness."""

    def __init__(self, plc, mqtt, config):
        super().__init__(plc, mqtt, config)
        if "state" in config:
            self.create_attribute(config["state"], "X", "state")
        if "brightness" in config:
            self.create_attribute(config["brightness"], "BYTE", "brightness")