"""
This module will test the install command
"""
from controller import __version__, gitter
from tests import TemporaryRemovePath, create_project, exec_command, random_project_name


def test_install(capfd, fake):

    project = random_project_name(fake)
    create_project(
        capfd=capfd,
        name=project,
        auth="postgres",
        frontend="angular",
        init=True,
        pull=False,
        start=False,
    )

    with TemporaryRemovePath("submodules/do"):
        exec_command(
            capfd,
            "install",
            "missing as submodules/do. You should init your project",
        )

    exec_command(capfd, "install 100.0", "Invalid version")

    exec_command(capfd, "install auto")

    r = gitter.get_repo("submodules/do")
    gitter.switch_branch(r, "0.7.6")

    exec_command(
        capfd,
        "install",
        f"Controller repository switched to {__version__}",
    )

    exec_command(capfd, "install")

    exec_command(capfd, "install --no-editable")

    # This is the very last command... installing an old version!
    exec_command(capfd, "install --no-editable 0.7.2")

    # This test will change the required version
    pconf = f"projects/{project}/project_configuration.yaml"

    # Read and change the content
    fin = open(pconf)
    data = fin.read()
    data = data.replace(f'rapydo: "{__version__}"', 'rapydo: "0.7.6"')
    fin.close()
    # Write the new content
    fin = open(pconf, "wt")
    fin.write(data)
    fin.close()

    exec_command(
        capfd,
        "version",
        f"This project is not compatible with rapydo version {__version__}",
        "Please downgrade rapydo to version 0.7.6 or modify this project",
    )

    # Read and change the content
    fin = open(pconf)
    data = fin.read()
    data = data.replace('rapydo: "0.7.6"', 'rapydo: "99.99.99"')
    fin.close()
    # Write the new content
    fin = open(pconf, "wt")
    fin.write(data)
    fin.close()

    exec_command(
        capfd,
        "version",
        f"This project is not compatible with rapydo version {__version__}",
        "Please upgrade rapydo to version 99.99.99 or modify this project",
    )
