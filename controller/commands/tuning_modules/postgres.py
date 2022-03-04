from controller.utilities import system


def tuning(ram: int, cpu: int) -> None:
    # Something like 25% of available RAM
    print(f"POSTGRES_SHARED_BUFFERS: {system.bytes_to_str(ram * 0.25)}")
    # Something like 75% of available RAM
    print(f"POSTGRES_EFFECTIVE_CACHE_SIZE: {system.bytes_to_str(ram * 0.75)}")
    # Something like 1/16 of RAM
    print(f"POSTGRES_MAINTENANCE_WORK_MEM: {system.bytes_to_str(ram * 0.0625)}")
    # Set as the number of core (and not more).
    print(f"POSTGRES_MAX_WORKER_PROCESSES: {cpu}")
