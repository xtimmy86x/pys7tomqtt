# pys7tomqtt

Bridge between Siemens S7 PLCs and MQTT brokers.

## Installation

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

The application now uses a YAML configuration file.  The default file is
`config.yaml`; an example configuration is available in
`config.example.yaml`.

To migrate from older versions using `config.json`, rename the file to
`config.yaml` and adapt the contents to YAML syntax.

## Running

Execute the connector, optionally providing a custom configuration path:

```bash
python -m pys7tomqtt.main [path/to/config.yaml]
```
