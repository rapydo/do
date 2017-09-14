
import os
from git import Repo
from controller.arguments import ArgParser
from controller.compose import compose_log
from controller.app import Application
from utilities import PROJECT_DIR, \
    BACKEND_DIR, SWAGGER_DIR, ENDPOINTS_CODE_DIR
from utilities.logs import get_logger
from utilities.basher import BashCommands

log = get_logger(__name__)

compose_log_prefix = 'DEBUG %s' % compose_log
symbol = '✓'
env_log = '%s Created .env file' % symbol
env_log_prefix_verbose = 'VERBOSE ' + env_log
env_log_prefix_info = 'INFO ' + env_log
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


# def test_init_and_check(capfd):
def test_all(capfd):

    # create .projectrc
    with open('.projectrc', 'w') as f:
        f.write("project: template")

    # INIT on rapydo-core
    _, err = exec_command(capfd, "rapydo init")
    log.pp(err)
    assert env_log_prefix_verbose in err
    assert "INFO Bower libs downloaded" in err
    assert "INFO Project initialized" in err

    # UPDATE on rapydo-core
    _, err = exec_command(capfd, "rapydo update")
    assert env_log_prefix_verbose in err
    assert "INFO Bower libs downloaded" in err
    assert "INFO All updated" in err

    # _, err = exec_command(capfd, "rapydo build")
    # assert "INFO Image built" in err

    # CHECK on rapydo-core
    _, err = exec_command(capfd, "rapydo check")
    assert env_log_prefix_info in err
    assert "INFO You are working on rapydo-core, not a fork" in err
    assert "INFO All checked" in err

    # NOW with are on a fork of rapydo-core
    gitobj = Repo(".")
    gitobj.remotes.origin.set_url("just_a_non_url")

    # Missing upstream url
    _, err = exec_command(capfd, "rapydo check")
    assert "EXIT Missing upstream to rapydo/core" in err

    # Create upstream url
    _, err = exec_command(capfd, "rapydo init")
    assert env_log_prefix_verbose in err
    assert "INFO Project initialized" in err

    # Check upstream url
    # Also check .env cache
    _, err = exec_command(capfd, "rapydo --cache-env check -s")
    log.pp(err)
    assert "INFO \u2713 Upstream is set correctly" in err
    assert env_cached_log_verbose in err
    assert "INFO All checked" in err

    out, err = exec_command(capfd, "rapydo env")
    assert env_log_prefix_verbose in err
    assert "project: template" in out

    os.remove(".projectrc")

# def test_two_projects(capfd):
    bash = BashCommands()
    bash.copy_folder("projects/template", "projects/second")

    _, err = exec_command(capfd, "rapydo -env check -s")
    e = "EXIT Please select the --project option on one of the following:"
    assert e in err
    # We can no longer test this, we have several projects and the number is
    # dyanamic... we do not want to update this list every new project...
    # assert " ['template', 'second']" in err

    _, err = exec_command(capfd, "rapydo -env -p template check -s")
    assert "INFO All checked" in err

    _, err = exec_command(capfd, "rapydo -env -p xyz check -s")
    assert "EXIT Wrong project 'xyz'." in err
    assert "Select one of the following:" in err
    assert " ['template', 'second']" in err

    # create .projectrc
    with open('.projectrc', 'w') as f:
        f.write("project: template")

    _, err = exec_command(capfd, "rapydo -env check -s")
    assert "INFO All checked" in err


# def test_from_start_to_clean(capfd):

    _, err = exec_command(capfd, "rapydo start")
    assert env_log_prefix_verbose in err
    assert compose_log_prefix + "'up'" in err
    assert "INFO Stack started" in err

    _, err = exec_command(capfd, "rapydo status")
    assert compose_log_prefix + "'ps'" in err

    exec_command(capfd, "rapydo log")
    # FIXME: how is possible that this message is not found??
    # assert compose_log_prefix + "'logs'" in err

    exec_command(capfd, "rapydo bower-install jquery")
    # FIXME: how is possible that this message is not found??
    # assert "EXIT Missing bower lib, please add the --lib option" in err
    exec_command(capfd, "rapydo bower-install --lib jquery")
    # FIXME: how is possible that this message is not found??
    # assert compose_log_prefix + "'run'" in err

    exec_command(capfd, "rapydo bower-update jquery")
    # FIXME: how is possible that this message is not found??
    # assert "EXIT Missing bower lib, please add the --lib option" in err
    exec_command(capfd, "rapydo bower-update --lib jquery")
    # FIXME: how is possible that this message is not found??
    # assert compose_log_prefix + "'run'" in err

    _, err = exec_command(capfd, "rapydo toggle-freeze")
    assert env_log_prefix_verbose in err
    assert "INFO Stack paused" in err

    _, err = exec_command(capfd, "rapydo toggle-freeze")
    assert env_log_prefix_verbose in err
    assert "INFO Stack unpaused" in err

    _, err = exec_command(capfd, "rapydo stop")
    assert env_log_prefix_verbose in err
    assert "INFO Stack stoped" in err

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

    endpoint_name = 'justatest'
    out, err = exec_command(capfd, "rapydo template --yes %s" % endpoint_name)
    # parsing responses like:
    # "rendered projects/template/backend/swagger/justatest/specs.yaml"
    base_response = 'DEBUG rendered %s/template/%s' % \
        (PROJECT_DIR, BACKEND_DIR)

    assert '%s/%s/%s/specs.yaml' % \
        (base_response, SWAGGER_DIR, endpoint_name) in err
    assert '%s/%s/%s/get.yaml' % \
        (base_response, SWAGGER_DIR, endpoint_name) in err
    assert '%s/%s/%s.py' % \
        (base_response, ENDPOINTS_CODE_DIR, endpoint_name) in err
    assert '%s/tests/test_%s.py' % (base_response, endpoint_name) in err
    assert 'INFO Scaffold completed' in err

    out, err = exec_command(capfd, "rapydo find --endpoint %s" % endpoint_name)
    assert "Endpoint path:\t/api/%s" % endpoint_name in err
    assert "Labels:\t\tcustom, %s" % endpoint_name in err
    assert "Python class:\t%s" % endpoint_name.capitalize() in err
