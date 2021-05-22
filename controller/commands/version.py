from distutils.version import LooseVersion

from controller import __version__
from controller.app import Application, Configuration


@Application.app.command(help="Retrieve version details")
def version() -> None:
    Application.get_controller().controller_init()

    # Check if rapydo version is compatible with version required by the project
    if __version__ == Configuration.rapydo_version:
        c = "\033[1;32m"  # Light Green
    else:
        c = "\033[1;31m"  # Light Red
    d = "\033[0m"

    cv = f"{c}{__version__}{d}"
    pv = f"{c}{Configuration.version}{d}"
    rv = f"{c}{Configuration.rapydo_version}{d}"
    print(f"\nrapydo: {cv}\t{Configuration.project}: {pv}\trequired rapydo: {rv}")

    if __version__ != Configuration.rapydo_version:
        cver = LooseVersion(__version__)
        rver = LooseVersion(Configuration.rapydo_version)
        updown = "upgrade" if cver < rver else "downgrade"
        rv = Configuration.rapydo_version
        print(f"\nThis project is not compatible with rapydo version {__version__}")
        print(f"Please {updown} rapydo to version {rv} or modify this project")
        print(f"\n\033[1;31mrapydo install {Configuration.rapydo_version}\033[0m")
