from ..device import Device

VALID_TYPES = {"X", "B", "R", "DR", "I", "DI", "W", "DW", "D"}

class SensorDevice(Device):
    """Simple sensor device exposing a state."""

    def __init__(self, plc, mqtt, config):
        super().__init__(plc, mqtt, config)

        # --- Modalità semplice: un solo stato ---
        if "state" in config:
            dtype = str(config.get("state_type", "X")).upper()
            if dtype not in VALID_TYPES:
                raise ValueError(f"state_type non valido: {dtype}. Attesi: {VALID_TYPES}")
            # nome pubblicato = "state"
            self._create_attr_safe(
                addr=config["state"],
                dtype=dtype,
                name="state",
                #opts=config  # passiamo l'intera config per eventuali meta futuri
            )