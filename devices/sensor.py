from ..device import Device

class SensorDevice(Device):
    """Simple sensor device exposing a state."""

    def __init__(self, plc, mqtt, config):
        super().__init__(plc, mqtt, config)
        if "state" in config:

            state_cfg = config["state"]
            address = state_cfg.get("plc") if isinstance(state_cfg, dict) else state_cfg
            if not address:
                raise ValueError("state requires a plc address")

            self.create_attribute(state_cfg,"state")
            