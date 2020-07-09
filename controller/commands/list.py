import os

from controller import COMPOSE_ENVIRONMENT_FILE, gitter, log


def read_env():
    envfile = os.path.join(os.curdir, COMPOSE_ENVIRONMENT_FILE)
    env = {}
    with open(envfile) as f:
        lines = f.readlines()
        for line in lines:
            line = line.split("=")
            k = line[0].strip()
            v = line[1].strip()
            env[k] = v
    return env


def __call__(args, active_services, compose_config, gits, **kwargs):

    printed_something = False
    if args.get("args"):
        printed_something = True
        log.info("List of configured rapydo arguments:\n")
        for var in sorted(args):
            val = args.get(var)
            print(f"{var:<20}\t{val}")

    if args.get("env"):
        printed_something = True
        log.info("List env variables:\n")
        env = read_env()
        for var in sorted(env):
            val = env.get(var)
            print(f"{var:<36}\t{val}")

    if args.get("active_services"):
        printed_something = True
        log.info("List of active services:\n")
        print("{:<12} {:<24} {}".format("Name", "Image", "Path"))

        for service in compose_config:
            name = service.get("name")
            if name in active_services:
                image = service.get("image")
                build = service.get("build")
                if build is None:
                    print(f"{name:<12} {image:<24}")
                else:
                    path = build.get("context")
                    path = path.replace(os.getcwd(), "")
                    if path.startswith("/"):
                        path = path[1:]
                    print(f"{name:<12} {image:<24} {path}")

    if args.get("submodules"):
        printed_something = True
        log.info("List of submodules:\n")
        print("{:<18} {:<18} {}".format("Repo", "Branch", "Path"))
        for name in gits:
            repo = gits.get(name)
            if repo is None:
                continue
            branch = gitter.get_active_branch(repo)
            path = repo.working_dir
            path = path.replace(os.getcwd(), "")
            if path.startswith("/"):
                path = path[1:]
            print(f"{name:<18} {branch:<18} {path}")

    if not printed_something:
        log.error("Nothing to list, please use rapydo list -h for available options")
