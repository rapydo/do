from distutils.version import LooseVersion

from controller import RED, __version__, colors
from controller.app import Application, Configuration


@Application.app.command(help="Retrieve version details")
def version() -> None:

    Application.print_command()

    Application.get_controller().controller_init()

    # Check if rapydo version is compatible with version required by the project
    if __version__ == Configuration.rapydo_version:
        c = colors.GREEN  # Light Green
    else:
        c = colors.RED

    cv = f"{c}{__version__}{colors.RESET}"
    pv = f"{c}{Configuration.version}{colors.RESET}"
    rv = f"{c}{Configuration.rapydo_version}{colors.RESET}"
    print(f"\nrapydo: {cv}\t{Configuration.project}: {pv}\trequired rapydo: {rv}")

    if __version__ != Configuration.rapydo_version:
        cver = LooseVersion(__version__)
        rver = LooseVersion(Configuration.rapydo_version)
        updown = "upgrade" if cver < rver else "downgrade"
        rv = Configuration.rapydo_version
        command = RED(f"rapydo install {Configuration.rapydo_version}")

        print(
            f"""
This project is not compatible with rapydo version {__version__}
Please {updown} rapydo to version {rv} or modify this project

{command}"""
        )
