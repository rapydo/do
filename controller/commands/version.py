from distutils.version import LooseVersion

from controller import __version__

# from controller import log


def __call__(project, version, rapydo_version, **kwargs):

    # Check if rapydo version is compatible with version required by the project
    if __version__ == rapydo_version:
        c = "\033[1;32m"  # Light Green
    else:
        c = "\033[1;31m"  # Light Red
    d = "\033[0m"

    cv = "{}{}{}".format(c, __version__, d)
    pv = "{}{}{}".format(c, version, d)
    rv = "{}{}{}".format(c, rapydo_version, d)
    print("\nrapydo: {}\t{}: {}\trequired rapydo: {}".format(cv, project, pv, rv))

    if __version__ != rapydo_version:
        c = LooseVersion(__version__)
        v = LooseVersion(rapydo_version)
        updown = "upgrade" if c < v else "downgrade"
        print(
            "\nThis project is not compatible with rapydo version {}".format(
                __version__
            )
        )
        print(
            "Please {} rapydo to version {} or modify this project".format(
                updown, rapydo_version
            )
        )

        print("\n\033[1;31mrapydo install {}\033[0m".format(rapydo_version))
