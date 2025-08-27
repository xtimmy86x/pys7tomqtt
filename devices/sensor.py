from ..device import Device

VALID_TYPES = {"X", "B", "R", "DR", "I", "DI", "W", "DW", "D"}

class SensorDevice(Device):
    """Simple sensor device exposing a state."""

    def __init__(self, plc, mqtt, config):
        super().__init__(plc, mqtt, config)
        # --- Modalità semplice: un solo stato ---
        
        if "state" in config:
            dtype = str(config.get("state_type")).upper()
            if dtype not in VALID_TYPES:
                raise ValueError(f"state_type non valido: {dtype}. Attesi: {VALID_TYPES}")
            elif dtype is None:
                raise ValueError("state_type mancante")
            # nome pubblicato = "state"
            self.create_attribute(config["state"],dtype,"state")