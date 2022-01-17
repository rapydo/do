def main() -> None:

    # All imports moved here to prevent to slow down the import of main
    import warnings

    from colorama import deinit, init
    from python_on_whales.utils import DockerException

    from controller import TESTING, log, print_and_exit

    if TESTING:
        warnings.simplefilter("always", Warning)
        # Convert warnings to exceptions
        warnings.simplefilter("error", UserWarning)
        warnings.simplefilter("error", DeprecationWarning)
        warnings.simplefilter("error", SyntaxWarning)
        warnings.simplefilter("error", RuntimeWarning)
        warnings.simplefilter("error", FutureWarning)
        warnings.simplefilter("error", PendingDeprecationWarning)
        warnings.simplefilter("error", ImportWarning)
        warnings.simplefilter("error", UnicodeWarning)
        warnings.simplefilter("error", BytesWarning)
        warnings.simplefilter("error", ResourceWarning)
    else:
        warnings.simplefilter("always", UserWarning)
        warnings.simplefilter("always", DeprecationWarning)

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
