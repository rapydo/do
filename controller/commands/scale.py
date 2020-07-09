from glom import glom

from controller import log
from controller.compose import Compose


def __call__(args, conf_vars, files, **kwargs):

    scaling = args.get("value", "")
    options = scaling.split("=")
    if len(options) != 2:
        scale_var = "DEFAULT_SCALE_{}".format(scaling.upper())
        nreplicas = glom(conf_vars, "env.{}".format(scale_var), default=None)
        if nreplicas is None:
            hints = "You can also set a {} variable in your .projectrc file".format(
                scale_var
            )
            log.exit("Please specify how to scale: SERVICE=NUM_REPLICA\n\n{}", hints)
        service = scaling
        scaling = "{}={}".format(service, nreplicas)
    else:
        service, nreplicas = options

    if isinstance(nreplicas, str) and not nreplicas.isnumeric():
        log.exit("Invalid number of replicas: {}", nreplicas)

    dc = Compose(files=files)
    dc.start_containers([service], scale=[scaling], skip_dependencies=True)
