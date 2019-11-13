import os
from git import Repo
from controller.arguments import ArgParser
from controller.compose import compose_log
from controller.app import Application
from utilities.logs import get_logger
from utilities.basher import BashCommands

log = get_logger(__name__)

compose_log_prefix = 'DEBUG %s' % compose_log
symbol = '✓'
env_log = 'Created .env file'
env_log_prefix_verbose = 'VERBOSE ' + env_log
env_log_prefix_info = 'INFO %s %s' % (symbol, env_log)
env_cached_log = 'Using cached .env'
env_cached_log_verbose = 'VERY_VERBOSE ' + env_cached_log


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
    log.pp(err)
    assert env_log_prefix_verbose in err
    assert "INFO Project initialized" in err

    _, err = exec_command(capfd, "rapydo pull")
    log.pp(err)
    assert env_log_prefix_verbose in err
    assert "INFO Base images pulled from docker hub" in err

    _, err = exec_command(capfd, "rapydo init")
    log.pp(err)
    assert env_log_prefix_verbose in err
    assert "INFO Project initialized" in err

    # UPDATE on rapydo-core
    _, err = exec_command(capfd, "rapydo update")
    assert env_log_prefix_verbose in err
    assert "INFO All updated" in err

    _, err = exec_command(capfd, "rapydo build --rebuild-templates")
    assert "INFO Images built" in err

    # CHECK on rapydo-core
    _, err = exec_command(capfd, "rapydo check")
    assert env_log_prefix_info in err
    assert "INFO All checked" in err

    # CHECK on rapydo-core by enabling permissions checks
    _, err = exec_command(capfd, "rapydo --check-permissions check")
    assert env_log_prefix_info in err
    assert "INFO All checked" in err

    # NOW we are on a fork of rapydo-core
    gitobj = Repo(".")
    gitobj.remotes.origin.set_url("just_a_non_url")

    _, err = exec_command(capfd, "rapydo init")
    assert env_log_prefix_verbose in err
    assert "INFO Project initialized" in err

    _, err = exec_command(capfd, "rapydo list --env")
    assert "INFO List env variables:" in err

    _, err = exec_command(capfd, "rapydo list --args")
    assert "INFO List of configured rapydo arguments:" in err

    _, err = exec_command(capfd, "rapydo list --services")
    assert "INFO List of active services:" in err

    _, err = exec_command(capfd, "rapydo list --submodules")
    assert "INFO List of submodules:" in err

    _, err = exec_command(capfd, "rapydo dump")
    assert "WARNING Config dump: docker-compose.yml" in err

    os.remove(".projectrc")

    bash = BashCommands()
    bash.copy_folder("projects/sql", "projects/second")

    _, err = exec_command(capfd, "rapydo check -s")
    assert "EXIT Please select the --project option on one of the following:" in err

    _, err = exec_command(capfd, "rapydo -p sql check -s")
    assert "INFO All checked" in err

    _, err = exec_command(capfd, "rapydo -p invalid_character check -s")
    assert "EXIT Wrong project name, _ is not a valid character." in err

    _, err = exec_command(capfd, "rapydo -p celery check -s")
    assert "EXIT You selected a reserved name, invalid project name: celery" in err

    _, err = exec_command(capfd, "rapydo -p xyz check -s")
    assert "EXIT Wrong project 'xyz'." in err
    assert "Select one of the following:" in err

    # create .projectrc
    with open('.projectrc', 'w') as f:
        f.write("project: sql")

    _, err = exec_command(capfd, "rapydo check -s")
    assert "INFO All checked" in err

    _, err = exec_command(capfd, "rapydo start")
    assert env_log_prefix_verbose in err
    assert compose_log_prefix + "'up'" in err
    assert "INFO Stack started" in err

    _, err = exec_command(capfd, "rapydo status")
    assert compose_log_prefix + "'ps'" in err

    # Template project is based on neo4j
    exec_command(capfd, "rapydo verify neo4j")
    # This output is not capture, since it is produced by the backend
    # assert 'EXIT Service "neo4j" was NOT detected' in err

    exec_command(capfd, "rapydo verify postgres")
    # This output is not capture, since it is produced by the backend
    # assert "INFO Service postgres is reachable" in err

    exec_command(capfd, "rapydo scale backend=1")

    exec_command(capfd, "rapydo logs")
    # FIXME: how is possible that this message is not found??
    # assert compose_log_prefix + "'logs'" in err

    _, err = exec_command(capfd, "rapydo toggle-freeze")
    assert env_log_prefix_verbose in err
    assert "INFO Stack paused" in err

    _, err = exec_command(capfd, "rapydo toggle-freeze")
    assert env_log_prefix_verbose in err
    assert "INFO Stack unpaused" in err

    _, err = exec_command(capfd, "rapydo stop")
    assert env_log_prefix_verbose in err
    assert "INFO Stack stopped" in err

    _, err = exec_command(capfd, "rapydo restart")
    assert env_log_prefix_verbose in err
    assert "INFO Stack restarted" in err

    _, err = exec_command(capfd, "rapydo remove")
    assert env_log_prefix_verbose in err
    assert compose_log_prefix + "'stop'" in err
    assert "INFO Stack removed" in err

    _, err = exec_command(capfd, "rapydo clean")
    assert env_log_prefix_verbose in err
    assert "INFO Stack cleaned" in err

    """
    endpoint_name = 'justatest'
    _, err = exec_command(capfd, "rapydo template --yes %s" % endpoint_name)
    # parsing responses like:
    # "rendered projects/sql/backend/swagger/justatest/specs.yaml"
    base_response = 'INFO rendered %s/sql/%s' % (PROJECT_DIR, BACKEND_DIR)

    assert '%s/%s/%s/specs.yaml' % (base_response, SWAGGER_DIR, endpoint_name) in err
    assert '%s/%s/%s/get.yaml' % (base_response, SWAGGER_DIR, endpoint_name) in err
    assert '%s/%s/%s.py' % (base_response, ENDPOINTS_CODE_DIR, endpoint_name) in err
    assert '%s/tests/test_%s.py' % (base_response, endpoint_name) in err
    assert 'INFO Scaffold completed' in err

    _, err = exec_command(capfd, "rapydo find --endpoint %s" % endpoint_name)
    assert "Endpoint path:\t/api/%s" % endpoint_name in err
    assert "Labels:\t\tcustom, %s" % endpoint_name in err
    assert "Python class:\t%s" % endpoint_name.capitalize() in err
    """

    # exec_command(capfd, "rapydo install --git auto")

    exec_command(capfd, "rapydo interfaces sqlalchemy --port 123 --detach")

    # Output is too long? Removed last tests...
    # exec_command(capfd, "rapydo create test")
    # assert 'EXIT You are on a git repo, unable to continue' in err

    # os.chdir("/tmp")
    # exec_command(capfd, "rapydo create test")
    # assert "INFO Project test successfully created" in err
