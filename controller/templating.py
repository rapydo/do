# -*- coding: utf-8 -*-
import os
import random
import string
from jinja2 import FileSystemLoader, Environment, DebugUndefined
# from jinja2.meta import find_undeclared_variables
from jinja2.exceptions import TemplateNotFound, UndefinedError
from controller import log

TEMPLATE_DIR = 'templates'


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
            os.path.abspath(os.path.dirname(__file__)),
            TEMPLATE_DIR
        )
        if not os.path.isdir(self.template_dir):
            log.exit("Template folder not found: {}", self.template_dir)

        log.debug("Template folder: {}", self.template_dir)
        loader = FileSystemLoader([TEMPLATE_DIR, self.template_dir])

        self.env = Environment(
            loader=loader,
            undefined=DebugUndefined,
            autoescape=True
        )
        self.env.filters['password'] = password
        self.env.filters['username'] = username

    def get_template(self, filename, data):
        try:
            template = self.env.get_template(filename)
            content = template.render(**data)
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
        except UndefinedError as e:
            log.exit(e)

    def save_template(self, filename, content, force=False):

        if os.path.exists(filename):
            if force:
                self.make_backup(filename)
            else:
                log.exit("File {} already exists", filename)

        with open(filename, "w+") as fh:
            fh.write(content)

    @staticmethod
    def make_backup(filename):
        backup_filename = "{}.bak".format(filename)
        os.rename(filename, backup_filename)
        log.info("A backup of {} is saved as {}", filename, backup_filename)
