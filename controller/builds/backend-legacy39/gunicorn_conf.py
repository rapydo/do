import multiprocessing
import os

bind_env = os.getenv("BIND", None)
if bind_env:
    use_bind = bind_env
else:
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "8080")
    use_bind = f"{host}:{port}"

gunicorn_workers = int(os.getenv("GUNICORN_WORKERS", "1"))
workers_per_core = float(os.getenv("GUNICORN_WORKERS_PER_CORE", "1"))
cores = multiprocessing.cpu_count()

# GUNICORN_WORKERS + cores * GUNICORN_WORKERS_PER_CORE
gunicorn_workers += int(workers_per_core * cores)

max_workers = int(os.getenv("GUNICORN_MAX_NUM_WORKERS", "24"))
if gunicorn_workers > max_workers:
    gunicorn_workers = max_workers

if gunicorn_workers < 1:
    gunicorn_workers = 1

# Gunicorn config variables
loglevel = os.getenv("LOG_LEVEL", "info")
workers = gunicorn_workers
bind = use_bind
keepalive = 120
timeout = 120
errorlog = "-"
