import re

from controller.utilities import system

# from controller import log


def get_children(IMAGE, images):

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


def __call__(args, **kwargs):

    IMAGE = args.get("imagetag")

    img = system.execute_command("docker", ["images", "--all"]).split("\n")
    img = [re.split(r"\s+", i) for i in img[1:]]
    images = {}
    for i in img:
        if len(i) != 7:
            continue
        images[i[2]] = i

    child = IMAGE
    print("Finding all children and (grand)+ children of {}".format(child))
    found = 0
    while True:
        children = get_children(child, images)
        if len(children) == 0:
            break
        child = children[0]
        print("\t".join(images.get(child)))
        found += 1
        children = get_children(child, images)
    if found == 0:
        print("No child found for {}".format(child))
