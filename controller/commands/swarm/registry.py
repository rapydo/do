from controller import print_and_exit
from controller.app import Application


# Deprecated since 2.1
@Application.app.command(help="Replaced by run command")
def registry() -> None:
    # Deprecated since 2.1
    print_and_exit("Registry command is replaced by rapydo run registry")
