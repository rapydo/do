import re

from controller.utilities import system

# from controller import log


def get_parent(IMAGE, images):

    parameters = [
        "inspect",
        "--format='{{.Id}} {{.Parent}}'",
    ]
    for tag in images:
        image = images.get(tag)
        tag = image[2].strip()
        if tag == "":
            continue
        parameters.append(tag)

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

    parameters = ["images", "--all"]
    # log.info("Executing command {} {}", command, parameters)
    img = system.execute_command("docker", parameters).split("\n")
    img = [re.split(r"\s+", i) for i in img[1:]]
    images = {}
    for i in img:
        if len(i) != 7:
            continue
        images[i[2]] = i

    child = IMAGE
    print("Finding all parents and (grand)+ parents of {}".format(child))
    found = 0
    while True:
        parents = get_parent(child, images)
        if len(parents) == 0:
            break
        child = parents[0]
        print("\t".join(images.get(child)))
        found += 1
        parents = get_parent(child, images)
    if found == 0:
        print("No parent found for {}".format(child))
