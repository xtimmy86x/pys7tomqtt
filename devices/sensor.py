from ..device import Device
from ..utils import Utils

class SensorDevice(Device):
    """Simple sensor device exposing a state."""

    def __init__(self, plc, mqtt, config):
        super().__init__(plc, mqtt, config)
        # --- Modalità semplice: un solo stato ---
        if "state" in config:

            state_cfg = config["state"]
            address = state_cfg.get("plc") if isinstance(state_cfg, dict) else state_cfg
            if not address:
                raise ValueError("state requires a plc address")
            # Deduce the data type directly from the PLC address
            dtype = Utils()._parse_address(address)[1]

            self.create_attribute(state_cfg,dtype,"state")
            