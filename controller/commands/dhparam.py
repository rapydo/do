from controller.compose import Compose

# from controller import log


def __call__(files, **kwargs):

    command = "openssl dhparam -out /etc/nginx/ssl/dhparam.pem 4096"
    dc = Compose(files=files)
    return dc.exec_command("proxy", user="root", command=command)
