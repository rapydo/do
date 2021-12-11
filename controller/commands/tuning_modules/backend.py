def tuning(ram: int, cpu: int) -> None:
    print(f"GUNICORN_MAX_NUM_WORKERS: {1 + 2 * cpu}")
