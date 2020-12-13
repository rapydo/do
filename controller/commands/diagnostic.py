import requests
import typer

from controller import log
from controller.app import Application

SERVER_IS_ALIVE = '"Server is alive"'


@Application.app.command(help="Execute diagnostic tools against a host")
def diagnostic(
    host: str = typer.Argument(..., help="Host to be verified")
) -> None:  # pragma: no cover
    Application.get_controller().controller_init()

    if "://" in host:
        tokens = host.split("://")
        if tokens[0] != "https":
            Application.exit("{} schema not supported", tokens[0])
        host = tokens[1]

    host = f"https://{host}"

    try:
        resp = requests.get(host)
    except requests.exceptions.ConnectionError as e:
        log.error(e)
        Application.exit("Host {} is unreachable", host)

    log.info("Server: {}", resp.headers.get("Server"))

    resp = requests.get(f"{host}/api/status")
    if resp.status_code != 200:
        Application.exit("Invalid backend response status: {}", resp.status_code)

    if resp.text.strip() == SERVER_IS_ALIVE:
        log.info("Backend is able to respond")
    else:
        log.error("Unexcepted response from backend: {}", resp.text.strip())

    log.info("Project version: {}", resp.headers.get("Version"))
    log.info("RAPyDo version: {}", resp.headers.get("_RV"))

    resp = requests.get(f"{host}/app/login2")

    if resp.text.strip() == SERVER_IS_ALIVE:
        log.error("No frontend found")
    elif resp.status_code != 200:
        Application.exit("Invalid frontend response status: {}", resp.status_code)
    elif '<span class="sr-only">Loading...</span>' not in resp.text:
        Application.exit("Unexcepted response from frontend: {}", resp.text)
    else:
        log.info("Frontend is able to respond")
