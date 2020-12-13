import re
from typing import Dict, List

import typer

from controller.app import Application
from controller.utilities import system

# from controller import log


@Application.app.command(help="Find all children of a docker image")
def ancestors(
    imagetag: str = typer.Argument(..., help="Image tag ID to be inspected"),
) -> None:
    Application.get_controller().controller_init()

    all_images = system.execute_command("docker", ["images", "--all"]).split("\n")
    img = [re.split(r"\s+", i) for i in all_images[1:]]
    images = {}
    for i in img:
        if len(i) != 7:
            continue
        images[i[2]] = i

    child = imagetag
    print(f"Finding all children and (grand)+ children of {child}")
    found = 0
    while True:
        children = get_children(child, images)
        if len(children) == 0:
            break
        child = children[0]
        print("\t".join(images.get(child, "N/A")))
        found += 1
        children = get_children(child, images)
    if found == 0:
        print(f"No child found for {child}")


def get_children(IMAGE: str, images: Dict[str, List[str]]) -> List[str]:

    parameters = [
        "inspect",
        "--format='{{.Id}} {{.Parent}}'",
    ]

    parameters.extend(set(images.keys()))

    out = system.execute_command("docker", parameters).split("\n")
    final_output = []
    for result in out:
        if IMAGE not in result:
            continue
        tokens = re.findall(r"'sha256:(.*) sha256:(.*)'", result)
        if len(tokens) == 0:
            continue
        for t in tokens:
            tag = t[0][0:12]
            if tag != IMAGE:
                final_output.append(tag)
    return final_output
