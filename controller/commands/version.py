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

    cv = f"{c}{__version__}{d}"
    pv = f"{c}{version}{d}"
    rv = f"{c}{rapydo_version}{d}"
    print(f"\nrapydo: {cv}\t{project}: {pv}\trequired rapydo: {rv}")

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

        print(f"\n\033[1;31mrapydo install {rapydo_version}\033[0m")
