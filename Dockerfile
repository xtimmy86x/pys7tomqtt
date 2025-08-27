# Usa Python slim
FROM python:3.11-slim

# Dipendenze di sistema: libsnap7 serve a python-snap7
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsnap7-1 \
  && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Installa le dipendenze Python prima per cache più efficiente
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice
COPY . .

# Cartella per il file di configurazione montato dall’host
VOLUME ["/config"]

# Log non bufferizzati
ENV PYTHONUNBUFFERED=1

# Avvio: punta al tuo config YAML montato in /config
ENTRYPOINT ["python", "-m", "pys7tomqtt.main", "/config/config.yaml"]