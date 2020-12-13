from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Generate SSL DH DSA parameters, 4096 bit long prime")
def dhparam() -> None:
    Application.get_controller().controller_init()

    command = "openssl dhparam -out /etc/nginx/ssl/dhparam.pem 4096"
    dc = Compose(files=Application.data.files)
    dc.exec_command("proxy", user="root", command=command)
