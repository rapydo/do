import os
import random
import string

from jinja2 import DebugUndefined, Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound, UndefinedError

from controller import TEMPLATE_DIR, log


def username(param_not_used, length=8):
    rand = random.SystemRandom()
    charset = string.ascii_lowercase
    random_string = rand.choice(charset)
    charset += string.digits
    for _ in range(length - 1):
        random_string += rand.choice(charset)
    return random_string


def password(param_not_used, length=12):
    rand = random.SystemRandom()
    charset = string.ascii_lowercase + string.ascii_uppercase + string.digits

    random_string = rand.choice(charset)
    charset += string.digits
    for _ in range(length - 1):
        random_string += rand.choice(charset)

    return random_string


class Templating:
    def __init__(self):

        self.template_dir = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), TEMPLATE_DIR
        )
        if not os.path.isdir(self.template_dir):
            log.exit("Template folder not found: {}", self.template_dir)

        log.debug("Template folder: {}", self.template_dir)
        loader = FileSystemLoader([TEMPLATE_DIR, self.template_dir])

        self.env = Environment(
            loader=loader,
            undefined=DebugUndefined,
            autoescape=True,
            keep_trailing_newline=True,
        )
        self.env.filters["password"] = password
        self.env.filters["username"] = username

    def get_template(self, filename, data):
        try:
            if filename.startswith("."):
                filename = filename[1:]

            template = self.env.get_template("{}.j2".format(filename))
            content = template.render(**data)
            # from jinja2.meta import find_undeclared_variables
            # ast = self.env.parse(content)
            # undefined = find_undeclared_variables(ast)
            # if undefined:
            #     log.exit(
            #         'Missing variables in template: {}',
            #         undefined
            #     )

            return content
        except TemplateNotFound as e:
            log.exit("Template {} not found in: {}", str(e), self.template_dir)
        except UndefinedError as e:  # pragma: no cover
            log.exit(e)

    def save_template(self, filename, content, force=False):

        if os.path.exists(filename):
            if force:
                self.make_backup(filename)
            # It is always verified before calling save_template from app, create & add
            else:  # pragma: no cover
                log.exit("File {} already exists", filename)

        with open(filename, "w+") as fh:
            fh.write(content)

    @staticmethod
    def make_backup(filename):
        backup_filename = "{}.bak".format(filename)
        os.rename(filename, backup_filename)
        log.info("A backup of {} is saved as {}", filename, backup_filename)
