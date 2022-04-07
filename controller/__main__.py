def main() -> None:

    # All imports moved here to prevent to slow down the import of main
    import warnings

    from controller import TESTING, log, print_and_exit

    if TESTING:
        warnings.filterwarnings("error")
    else:  # pragma: no cover
        warnings.filterwarnings("default")

    from colorama import deinit, init  # type: ignore
    from python_on_whales.utils import DockerException

    from controller.app import Application

    try:
        init()
        Application.load_projectrc()
        controller = Application()
        controller.app()
    except DockerException as e:  # pragma: no cover
        log.critical("Uncatched exception: {}", type(e))
        print_and_exit(str(e))
    deinit()


if __name__ == "__main__":
    main()
