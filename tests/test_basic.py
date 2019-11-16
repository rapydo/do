import os
from git import Repo
from controller import log
from controller.arguments import ArgParser
from controller.compose import compose_log
from controller.app import Application


def exec_command(capfd, command):
    command = command.split(" ")

    arguments = ArgParser(args=command)

    try:
        Application(arguments)
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        log.info('completed')

    out, err = capfd.readouterr()
    out = out.split("\n")
    err = err.split("\n")

    for e in err:
        print(e)

    return out, err


def test_all(capfd):

    # create .projectrc
    with open('.projectrc', 'w') as f:
        f.write("project: sql")

    # INIT on rapydo-core
    _, err = exec_command(capfd, "rapydo init")
    print(err)
    assert "x" == err[-1]
    assert "Project initialized" in err

    _, err = exec_command(capfd, "rapydo pull")
    assert "Base images pulled from docker hub" in err

    _, err = exec_command(capfd, "rapydo init")
    assert "Project initialized" in err

    # UPDATE on rapydo-core
    _, err = exec_command(capfd, "rapydo update")
    assert "All updated" in err

    _, err = exec_command(capfd, "rapydo build --rebuild-templates")
    assert "Images built" in err

    # CHECK on rapydo-core
    _, err = exec_command(capfd, "rapydo check")
    assert 'Created .env file' in err
    assert "All checked" in err

    # CHECK on rapydo-core by enabling permissions checks
    _, err = exec_command(capfd, "rapydo --check-permissions check")
    assert 'Created .env file' in err
    assert "All checked" in err

    # NOW we are on a fork of rapydo-core
    gitobj = Repo(".")
    gitobj.remotes.origin.set_url("just_a_non_url")

    _, err = exec_command(capfd, "rapydo init")
    assert "Project initialized" in err

    _, err = exec_command(capfd, "rapydo list --env")
    assert "List env variables:" in err

    _, err = exec_command(capfd, "rapydo list --args")
    assert "List of configured rapydo arguments:" in err

    _, err = exec_command(capfd, "rapydo list --services")
    assert "List of active services:" in err

    _, err = exec_command(capfd, "rapydo list --submodules")
    assert "List of submodules:" in err

    _, err = exec_command(capfd, "rapydo dump")
    assert "Config dump: docker-compose.yml" in err

    os.remove(".projectrc")

    from plumbum import local
    command = local["cp"]
    command(["-r", "projects/sql", "projects/second"])

    _, err = exec_command(capfd, "rapydo check -s")
    assert "Please select the --project option on one of the following:" in err

    _, err = exec_command(capfd, "rapydo -p sql check -s")
    assert "All checked" in err

    _, err = exec_command(capfd, "rapydo -p invalid_character check -s")
    assert "Wrong project name, _ is not a valid character." in err

    _, err = exec_command(capfd, "rapydo -p celery check -s")
    assert "You selected a reserved name, invalid project name: celery" in err

    _, err = exec_command(capfd, "rapydo -p xyz check -s")
    assert "Wrong project 'xyz'." in err
    assert "Select one of the following:" in err

    # create .projectrc
    with open('.projectrc', 'w') as f:
        f.write("project: sql")

    _, err = exec_command(capfd, "rapydo check -s")
    assert "All checked" in err

    _, err = exec_command(capfd, "rapydo start")
    assert compose_log + "'up'" in err
    assert "Stack started" in err

    _, err = exec_command(capfd, "rapydo status")
    assert compose_log + "'ps'" in err

    # Template project is based on neo4j
    exec_command(capfd, "rapydo verify neo4j")
    # This output is not capture, since it is produced by the backend
    # assert 'Service "neo4j" was NOT detected' in err

    exec_command(capfd, "rapydo verify postgres")
    # This output is not capture, since it is produced by the backend
    # assert "Service postgres is reachable" in err

    exec_command(capfd, "rapydo scale backend=1")

    exec_command(capfd, "rapydo logs")
    # FIXME: how is possible that this message is not found??
    # assert compose_log + "'logs'" in err

    _, err = exec_command(capfd, "rapydo toggle-freeze")
    assert "Stack paused" in err

    _, err = exec_command(capfd, "rapydo toggle-freeze")
    assert "Stack unpaused" in err

    _, err = exec_command(capfd, "rapydo stop")
    assert "Stack stopped" in err

    _, err = exec_command(capfd, "rapydo restart")
    assert "Stack restarted" in err

    _, err = exec_command(capfd, "rapydo remove")
    assert compose_log + "'stop'" in err
    assert "Stack removed" in err

    _, err = exec_command(capfd, "rapydo clean")
    assert "Stack cleaned" in err

    """
    endpoint_name = 'justatest'
    _, err = exec_command(capfd, "rapydo template --yes %s" % endpoint_name)
    # parsing responses like:
    # "rendered projects/sql/backend/swagger/justatest/specs.yaml"
    base_response = 'rendered %s/sql/%s' % (PROJECT_DIR, BACKEND_DIR)

    SWAGGER_DIR = 'swagger'
    assert '%s/%s/%s/specs.yaml' % (base_response, SWAGGER_DIR, endpoint_name) in err
    assert '%s/%s/%s/get.yaml' % (base_response, SWAGGER_DIR, endpoint_name) in err
    assert '%s/apis/%s.py' % (base_response, endpoint_name) in err
    assert '%s/tests/test_%s.py' % (base_response, endpoint_name) in err
    assert 'Scaffold completed' in err

    _, err = exec_command(capfd, "rapydo find --endpoint %s" % endpoint_name)
    assert "Endpoint path:\t/api/%s" % endpoint_name in err
    assert "Labels:\t\tcustom, %s" % endpoint_name in err
    assert "Python class:\t%s" % endpoint_name.capitalize() in err
    """

    # exec_command(capfd, "rapydo install --git auto")

    exec_command(capfd, "rapydo interfaces sqlalchemy --port 123 --detach")

    # Output is too long? Removed last tests...
    # exec_command(capfd, "rapydo create test")
    # assert 'You are on a git repo, unable to continue' in err

    # os.chdir("/tmp")
    # exec_command(capfd, "rapydo create test")
    # assert "Project test successfully created" in err
