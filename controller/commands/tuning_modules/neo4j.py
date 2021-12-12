from controller import log
from controller.app import Application
from controller.deploy.builds import verify_available_images
from controller.deploy.docker import Docker

SERVICE_NAME = __name__


def tuning(ram: int, cpu: int) -> None:

    verify_available_images(
        [SERVICE_NAME],
        Application.data.compose_config,
        Application.data.base_services,
    )

    docker = Docker()

    container = docker.get_container(SERVICE_NAME)

    command = f"neo4j-admin memrec --memory {ram}"

    if container:
        docker.exec_command(container, user="neo4j", command=command)
    else:
        docker.compose.create_volatile_container(SERVICE_NAME, command=command)

    # output = temporary_stream.getvalue().split("\\")
    # print(output)
    # Don't allocate more than 31g of heap,
    # since this will disable pointer compression, also known as "compressed oops",
    # in the JVM and make less effective use of the heap.
    # heap = min(ram * 0.4, 31 * GB)
    # print(f"NEO4J_HEAP_SIZE: {bytes_to_str(heap)}")
    # print(f"NEO4J_PAGECACHE_SIZE: {bytes_to_str(ram * 0.3)}")
    log.info("Use 'dbms.memory.heap.max_size' as NEO4J_HEAP_SIZE")
    log.info("Use 'dbms.memory.pagecache.size' as NEO4J_PAGECACHE_SIZE")
    log.info(
        "Keep enough free memory for lucene indexes "
        "(check size reported in the output, if any)"
    )
