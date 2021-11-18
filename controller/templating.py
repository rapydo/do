import os
import random
import string
from filecmp import cmp
from pathlib import Path
from typing import Dict, List, Union

from jinja2 import DebugUndefined, Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound, UndefinedError
from zxcvbn import zxcvbn

from controller import TEMPLATE_DIR, log, print_and_exit

TemplateDataType = Dict[str, Union[bool, float, str, List[str], Dict[str, str], None]]


def username(param_not_used: str, length: int = 8) -> str:
    rand = random.SystemRandom()
    charset = string.ascii_lowercase
    random_string = rand.choice(charset)
    charset += string.digits
    for _ in range(length - 1):
        random_string += rand.choice(charset)
    return random_string


def password(param_not_used: str, length: int = 12, symbols: str = "") -> str:
    rand = random.SystemRandom()
    charset = string.ascii_lowercase + string.ascii_uppercase + string.digits

    random_string = rand.choice(charset)
    charset += symbols
    for _ in range(length - 1):
        random_string += rand.choice(charset)

    return random_string


def get_strong_password() -> str:
    p = password(length=16, param_not_used="", symbols="%*,-.=^_~")
    result = zxcvbn(p)
    score = result["score"]
    # Should never happens since 16 characters with symbols is very unlikely to be weak
    if score < 4:  # pragma: no cover
        log.warning("Generated password is not strong enough, sampling again")
        return get_strong_password()
    return p


class Templating:
    def __init__(self) -> None:

        self.template_dir = Path(__file__).resolve().parent.joinpath(TEMPLATE_DIR)

        if not self.template_dir.is_dir():
            print_and_exit("Template folder not found: {}", self.template_dir)

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

    @staticmethod
    def get_template_name(filename: str) -> str:

        if filename.startswith("."):
            filename = filename[1:]

        return f"{filename}.j2"

    def get_template(self, filename: str, data: TemplateDataType) -> str:
        try:
            template_name = self.get_template_name(filename)
            template = self.env.get_template(template_name)
            content = str(template.render(**data))

            return content
        except TemplateNotFound as e:
            print_and_exit("Template {} not found in: {}", str(e), self.template_dir)
        except UndefinedError as e:  # pragma: no cover
            print_and_exit(str(e))

    def save_template(self, filename: Path, content: str, force: bool = False) -> None:

        if filename.exists():
            if force:
                self.make_backup(filename)
            # It is always verified before calling save_template from app, create & add
            else:  # pragma: no cover
                print_and_exit("File {} already exists", filename)

        with open(filename, "w+") as fh:
            fh.write(content)

    @staticmethod
    def make_backup(filename: Path) -> None:
        backup_filename = f"{filename}.bak"
        os.rename(filename, backup_filename)
        log.info("A backup of {} is saved as {}", filename, backup_filename)

    def file_changed(self, filename: str) -> bool:

        template = self.get_template_name(filename)
        return not cmp(
            filename, os.path.join(self.template_dir, template), shallow=True
        )
