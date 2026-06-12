# gunicorn_config.py
# Configuración de Gunicorn para producción

import multiprocessing
import os

# Puerto y host
bind = f"0.0.0.0:{os.getenv('PORT', 5000)}"

# Workers (usa 2*cpu_count + 1, máximo 8 para Railway)
cpu_count = multiprocessing.cpu_count()
workers = min(cpu_count * 2 + 1, 8)

# Threads por worker
threads = 2

# Tipo de worker
worker_class = "sync"

# Timeout (aumentado para operaciones largas)
timeout = 120

# Logs a stdout para Railway
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "pos_app"

# Keep-alive
keepalive = 5

# Preload app para ahorrar memoria
preload_app = False

# Max requests per worker (reciclar workers)
max_requests = 1000
max_requests_jitter = 100

# Configuración para producción
if os.getenv('ENVIRONMENT') == 'production':
    # Usar más conexiones
    worker_connections = 1000
    # Backlog más alto
    backlog = 128


# Max requests
max_requests = 1000
max_requests_jitter = 50

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (si lo necesitas)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
# ssl_version = ssl.PROTOCOL_TLSv1_2
# cert_reqs = ssl.CERT_NONE
# ca_certs = None
# ciphers = "TLSv1"

# Application
raw_env = []
reload = False
