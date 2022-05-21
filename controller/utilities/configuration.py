import re
from copy import deepcopy
from enum import Enum, IntEnum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    TypedDict,
    Union,
    cast,
)

import yaml
from glom import glom
from pydantic import (
    BaseModel,
    ConstrainedInt,
    ConstrainedStr,
    Extra,
    PositiveInt,
    PydanticValueError,
    ValidationError,
)

from controller import (
    COMPOSE_FILE_VERSION,
    CONFS_DIR,
    PLACEHOLDER,
    EnvType,
    log,
    print_and_exit,
)

PROJECTS_DEFAULTS_FILE = Path("projects_defaults.yaml")
PROJECTS_PROD_DEFAULTS_FILE = Path("projects_prod_defaults.yaml")
PROJECT_CONF_FILENAME = Path("project_configuration.yaml")


class Project(TypedDict):
    title: str
    description: str
    keywords: str
    rapydo: str
    version: str
    extends: Optional[str]
    extends_from: Optional[str]


class Submodule(TypedDict):
    online_url: str
    branch: Optional[str]
    _if: str


class Variables(TypedDict):
    submodules: Dict[str, Submodule]
    roles: Dict[str, str]
    env: Dict[str, EnvType]


# total is False because of .projectrc and project_configuration
# But should be total=True in case of projects_defaults
class Configuration(TypedDict, total=False):
    project: Project
    tags: Dict[str, str]
    variables: Variables


class BACKEND_BUILD_MODE_VALUES(Enum):
    backend = "backend"
    backend_legacy38 = "backend-legacy38"
    backend_legacy39 = "backend-legacy39"


class FRONTEND_FRAMEWORK_VALUES(Enum):
    nofrontend = "nofrontend"
    angular = "angular"


class FRONTEND_BUILD_MODE_VALUES(Enum):
    angular = "angular"
    angular_test = "angular-test"


class LOG_LEVEL_VALUES(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class APP_MODE_VALUES(Enum):
    development = "development"
    production = "production"
    test = "test"


class FLASK_ENV_VALUES(Enum):
    development = "development"
    production = "production"


class PYTHONMALLOC_VALUES(Enum):
    empty = ""
    debug = "debug"
    malloc = "malloc"
    pymalloc = "pymalloc"


class AUTH_SERVICE_VALUES(Enum):
    no = "NO_AUTHENTICATION"
    postgres = "sqlalchemy"
    neo4j = "neo4j"


class ALCHEMY_DBTYPE_VALUES(Enum):
    postgresql = "postgresql"
    mysql = "mysql+pymysql"


class CELERY_BROKER_VALUES(Enum):
    RABBIT = "RABBIT"
    REDIS = "REDIS"


class CELERY_BACKEND_VALUES(Enum):
    RABBIT = "RABBIT"
    REDIS = "REDIS"


class CELERY_POOL_MODE_VALUES(Enum):
    prefork = "prefork"
    eventlet = "eventlet"
    gevent = "gevent"
    thread = "thread"
    solo = "solo"


class FLOWER_PROTOCOL_VALUES(Enum):
    http = "http"
    https = "https"


class NEO4J_BOLT_TLS_LEVEL_VALUES(Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    DISABLED = "DISABLED"


class true_or_false(Enum):
    true = "true"
    false = "false"


class PLACEHOLDER_VALUE(Enum):
    PLACEHOLDER_VALUE = PLACEHOLDER


# Conflicts between pydantic and mypy
# https://stackoverflow.com/questions/66924001/conflict-between-pydantic-constr-and-mypy-checking
class Port(ConstrainedInt):
    gt = 0
    le = 65535


class NullablePort(ConstrainedInt):
    ge = 0
    le = 65535


class PasswordScore(ConstrainedInt):
    ge = 0
    le = 4


class GzipCompressionLevel(ConstrainedInt):
    ge = 1
    le = 9


class NonNegativeInt(ConstrainedInt):
    ge = 0


class AssignedCPU(ConstrainedStr):
    regex = re.compile(r"^[0-9]+\.[0-9]+$")


class AssignedMemory(ConstrainedStr):
    regex = re.compile(r"^[0-9]+(M|G)$")


class PostgresMem(ConstrainedStr):
    regex = re.compile(r"^[0-9]+(KB|MB|GB)$")


class Neo4jMem(ConstrainedStr):
    regex = re.compile(r"^[0-9]+(K|M|G|k|m|g)$")


class HealthcheckInterval(ConstrainedStr):
    regex = re.compile(r"^[0-9]+(s|m|h)$")


class Version(ConstrainedStr):
    regex = re.compile(r"^[0-9]+(\.[0-9]+)+$")


# most of bool variables were deprecated since 1.0
# Backend and Frontend use different booleans due to Py vs Js
# 0/1 is a much more portable value to prevent true|True|"true"
# This fixes troubles in setting boolean values only used by Angular
# (expected true|false) or used by Pyton (expected True|False)
class zero_or_one(IntEnum):
    ZERO = 0
    ONE = 1


class InvalidNeo4jFlag(PydanticValueError):
    msg_template = "Invalid Neo4j flag, expected values are: true or false"


class Neo4jFlag:
    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        field_schema.update(type="boolean")

    @classmethod
    def __get_validators__(cls) -> Iterator[Callable[["Neo4jFlag", Any], bool]]:
        yield cls.validate

    def validate(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value

        if value == "true":
            return True

        if value == "false":
            return False

        raise InvalidNeo4jFlag()


class ProjectModel(BaseModel):
    title: str
    description: str
    keywords: str
    rapydo: Version
    version: str


class SubmoduleModel(BaseModel):
    online_url: str
    branch: Optional[str]
    _if: str


class BaseEnvModel(BaseModel):
    BACKEND_BUILD_MODE: BACKEND_BUILD_MODE_VALUES
    FRONTEND_FRAMEWORK: FRONTEND_FRAMEWORK_VALUES
    FRONTEND_BUILD_MODE: FRONTEND_BUILD_MODE_VALUES
    NETWORK_MTU: PositiveInt
    HEALTHCHECK_INTERVAL: HealthcheckInterval
    HEALTHCHECK_BACKEND_CMD: str
    LOG_LEVEL: LOG_LEVEL_VALUES
    FILE_LOGLEVEL: LOG_LEVEL_VALUES
    LOG_RETENTION: PositiveInt
    MIN_PASSWORD_SCORE: PasswordScore
    ACTIVATE_BACKEND: zero_or_one
    ACTIVATE_PROXY: zero_or_one
    ACTIVATE_ALCHEMY: zero_or_one
    ACTIVATE_POSTGRES: zero_or_one
    ACTIVATE_MYSQL: zero_or_one
    ACTIVATE_NEO4J: zero_or_one
    ACTIVATE_RABBIT: zero_or_one
    ACTIVATE_REDIS: zero_or_one
    ACTIVATE_CELERY: zero_or_one
    ACTIVATE_CELERYBEAT: zero_or_one
    ACTIVATE_FLOWER: zero_or_one
    ACTIVATE_FTP: zero_or_one
    ACTIVATE_SMTP: zero_or_one
    ACTIVATE_SMTP_SERVER: zero_or_one
    ACTIVATE_TELEGRAM: zero_or_one
    ACTIVATE_SWAGGERUI: zero_or_one
    ACTIVATE_ADMINER: zero_or_one
    RUN_SCHEMATHESIS: zero_or_one
    MAX_LOGS_LENGTH: PositiveInt
    APP_MODE: APP_MODE_VALUES
    FLASK_HOST: str
    FLASK_DEFAULT_PORT: Port
    FLASK_ENV: FLASK_ENV_VALUES
    API_AUTOSTART: zero_or_one
    BACKEND_PORT: Port
    BACKEND_API_PORT: Port
    BACKEND_URL: str
    PYTHON_MAIN_FILE: str
    PYTHON_PATH: Path
    PYTHONASYNCIODEBUG: zero_or_one
    PYTHONFAULTHANDLER: zero_or_one
    PYTHONMALLOC: PYTHONMALLOC_VALUES
    BACKEND_PREFIX: str
    APP_SECRETS: Path
    DATA_PATH: Path
    DATA_IMPORT_FOLDER: Path
    GUNICORN_WORKERS: PositiveInt
    GUNICORN_WORKERS_PER_CORE: PositiveInt
    GUNICORN_MAX_NUM_WORKERS: PositiveInt
    CRONTAB_ENABLE: zero_or_one
    GZIP_COMPRESSION_ENABLE: zero_or_one
    GZIP_COMPRESSION_THRESHOLD: PositiveInt
    GZIP_COMPRESSION_LEVEL: GzipCompressionLevel
    ALEMBIC_AUTO_MIGRATE: zero_or_one
    PROXY_HOST: str
    PROXY_DEV_PORT: Port
    PROXY_PROD_PORT: Port
    PROXIED_CONNECTION: zero_or_one
    DOMAIN_ALIASES: Optional[str]
    SET_UNSAFE_EVAL: Optional[str]
    SET_UNSAFE_INLINE: Optional[str]
    SET_STYLE_UNSAFE_INLINE: Optional[str]
    SET_CSP_SCRIPT_SRC: Optional[str]
    SET_CSP_IMG_SRC: Optional[str]
    SET_CSP_FONT_SRC: Optional[str]
    SET_CSP_CONNECT_SRC: Optional[str]
    SET_CSP_FRAME_SRC: Optional[str]
    SET_MAX_REQUESTS_PER_SECOND_AUTH: PositiveInt
    SET_MAX_REQUESTS_BURST_AUTH: PositiveInt
    SET_MAX_REQUESTS_PER_SECOND_API: PositiveInt
    SET_MAX_REQUESTS_BURST_API: PositiveInt
    CORS_ALLOWED_ORIGIN: Optional[str]
    SSL_VERIFY_CLIENT: zero_or_one
    SSL_FORCE_SELF_SIGNED: zero_or_one

    ALCHEMY_ENABLE_CONNECTOR: zero_or_one
    ALCHEMY_EXPIRATION_TIME: PositiveInt
    ALCHEMY_VERIFICATION_TIME: PositiveInt
    ALCHEMY_HOST: str
    ALCHEMY_PORT: Port
    ALCHEMY_DBTYPE: ALCHEMY_DBTYPE_VALUES
    ALCHEMY_USER: str
    ALCHEMY_PASSWORD: str
    ALCHEMY_DB: str
    ALCHEMY_DBS: str
    ALCHEMY_POOLSIZE: PositiveInt
    MYSQL_ROOT_PASSWORD: str
    POSTGRES_MAX_CONNECTIONS: PositiveInt
    POSTGRES_SHARED_BUFFERS: PostgresMem
    POSTGRES_WAL_BUFFERS: PostgresMem
    POSTGRES_EFFECTIVE_CACHE_SIZE: PostgresMem
    POSTGRES_WORK_MEM: PostgresMem
    POSTGRES_MAINTENANCE_WORK_MEM: PostgresMem
    POSTGRES_EFFECTIVE_IO_CONCURRENCY: PositiveInt
    POSTGRES_MAX_WORKER_PROCESSES: PositiveInt
    NEO4J_ENABLE_CONNECTOR: zero_or_one
    NEO4J_EXPIRATION_TIME: PositiveInt
    NEO4J_VERIFICATION_TIME: PositiveInt
    NEO4J_HOST: str
    NEO4J_BOLT_PORT: Port
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    NEO4J_EXPOSED_WEB_INTERFACE_PORT: Port
    NEO4J_WEB_INTERFACE_PORT: Port
    NEO4J_SSL_ENABLED: Neo4jFlag
    NEO4J_BOLT_TLS_LEVEL: NEO4J_BOLT_TLS_LEVEL_VALUES
    # They are equal to placeholder in production mode when neo4j is not enabled
    NEO4J_HEAP_SIZE: Union[Neo4jMem, PLACEHOLDER_VALUE]
    NEO4J_PAGECACHE_SIZE: Union[Neo4jMem, PLACEHOLDER_VALUE]
    NEO4J_ALLOW_UPGRADE: Neo4jFlag
    NEO4J_RECOVERY_MODE: Neo4jFlag
    ELASTIC_HOST: str
    ELASTIC_PORT: Port
    RABBITMQ_ENABLE_CONNECTOR: zero_or_one
    RABBITMQ_EXPIRATION_TIME: PositiveInt
    RABBITMQ_VERIFICATION_TIME: PositiveInt
    RABBITMQ_HOST: str
    RABBITMQ_PORT: Port
    RABBITMQ_VHOST: str
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str
    RABBITMQ_MANAGEMENT_PORT: Port
    RABBITMQ_ENABLE_SHOVEL_PLUGIN: zero_or_one
    RABBITMQ_SSL_CERTFILE: Optional[Path]
    RABBITMQ_SSL_KEYFILE: Optional[Path]
    RABBITMQ_SSL_FAIL_IF_NO_PEER_CERT: Optional[true_or_false]
    RABBITMQ_SSL_ENABLED: zero_or_one
    REDIS_ENABLE_CONNECTOR: zero_or_one
    REDIS_EXPIRATION_TIME: PositiveInt
    REDIS_VERIFICATION_TIME: PositiveInt
    REDIS_HOST: str
    REDIS_PORT: Port
    REDIS_PASSWORD: str
    FTP_ENABLE_CONNECTOR: zero_or_one
    FTP_EXPIRATION_TIME: PositiveInt
    FTP_VERIFICATION_TIME: PositiveInt
    FTP_HOST: str
    FTP_PORT: Port
    FTP_USER: str
    FTP_PASSWORD: str
    FTP_SSL_ENABLED: zero_or_one
    NFS_HOST: Optional[str]
    NFS_EXPORTS_SECRETS: Path
    NFS_EXPORTS_RABBITDATA: Path
    NFS_EXPORTS_SQLDATA: Path
    NFS_EXPORTS_MARIADB: Path
    NFS_EXPORTS_GRAPHDATA: Path
    NFS_EXPORTS_DATA_IMPORTS: Path
    NFS_EXPORTS_PUREFTPD: Path
    NFS_EXPORTS_SSL_CERTS: Path
    NFS_EXPORTS_FLOWER_DB: Path
    NFS_EXPORTS_REDISDATA: Path
    CELERY_ENABLE_CONNECTOR: zero_or_one
    CELERY_EXPIRATION_TIME: PositiveInt
    CELERY_VERIFICATION_TIME: PositiveInt
    CELERY_BROKER: CELERY_BROKER_VALUES
    CELERY_BACKEND: CELERY_BACKEND_VALUES
    CELERY_POOL_MODE: CELERY_POOL_MODE_VALUES
    FLOWER_USER: str
    FLOWER_PASSWORD: str
    FLOWER_DBDIR: Path
    FLOWER_PORT: Port
    FLOWER_SSL_OPTIONS: Optional[str]
    FLOWER_PROTOCOL: FLOWER_PROTOCOL_VALUES
    DEFAULT_SCALE_BACKEND: PositiveInt
    DEFAULT_SCALE_CELERY: PositiveInt
    DEFAULT_SCALE_CELERYBEAT: PositiveInt
    DEFAULT_SCALE_SWAGGERUI: PositiveInt
    ASSIGNED_CPU_BACKEND: AssignedCPU
    ASSIGNED_MEMORY_BACKEND: AssignedMemory
    ASSIGNED_CPU_PROXY: AssignedCPU
    ASSIGNED_MEMORY_PROXY: AssignedMemory
    ASSIGNED_CPU_POSTGRES: AssignedCPU
    ASSIGNED_MEMORY_POSTGRES: AssignedMemory
    ASSIGNED_CPU_MARIADB: AssignedCPU
    ASSIGNED_MEMORY_MARIADB: AssignedMemory
    ASSIGNED_CPU_NEO4J: AssignedCPU
    ASSIGNED_MEMORY_NEO4J: AssignedMemory
    ASSIGNED_CPU_CELERY: AssignedCPU
    ASSIGNED_MEMORY_CELERY: AssignedMemory
    ASSIGNED_CPU_CELERYBEAT: AssignedCPU
    ASSIGNED_MEMORY_CELERYBEAT: AssignedMemory
    ASSIGNED_CPU_RABBIT: AssignedCPU
    ASSIGNED_MEMORY_RABBIT: AssignedMemory
    ASSIGNED_CPU_REDIS: AssignedCPU
    ASSIGNED_MEMORY_REDIS: AssignedMemory
    ASSIGNED_CPU_BOT: AssignedCPU
    ASSIGNED_MEMORY_BOT: AssignedMemory
    ASSIGNED_CPU_FLOWER: AssignedCPU
    ASSIGNED_MEMORY_FLOWER: AssignedMemory
    ASSIGNED_CPU_SWAGGERUI: AssignedCPU
    ASSIGNED_MEMORY_SWAGGERUI: AssignedMemory
    ASSIGNED_CPU_ADMINER: AssignedCPU
    ASSIGNED_MEMORY_ADMINER: AssignedMemory
    ASSIGNED_CPU_FTP: AssignedCPU
    ASSIGNED_MEMORY_FTP: AssignedMemory
    ASSIGNED_CPU_SMTP: AssignedCPU
    ASSIGNED_MEMORY_SMTP: AssignedMemory
    ASSIGNED_CPU_REGISTRY: AssignedCPU
    ASSIGNED_MEMORY_REGISTRY: AssignedMemory
    REGISTRY_HOST: Optional[str]
    REGISTRY_PORT: Port
    REGISTRY_USERNAME: str
    REGISTRY_PASSWORD: str
    REGISTRY_HTTP_SECRET: Optional[str]
    ACTIVATE_FAIL2BAN: zero_or_one
    SWARM_MANAGER_ADDRESS: Optional[str]
    # SYSLOG_ADDRESS: Optional[str]
    SMTP_ENABLE_CONNECTOR: zero_or_one
    SMTP_EXPIRATION_TIME: PositiveInt
    SMTP_VERIFICATION_TIME: PositiveInt
    SMTP_ADMIN: Optional[str]
    SMTP_NOREPLY: Optional[str]
    SMTP_HOST: Optional[str]
    SMTP_PORT: NullablePort
    SMTP_USERNAME: Optional[str]
    SMTP_PASSWORD: Optional[str]
    SMTP_SERVER_HOST: str
    SMTP_SERVER_PORT: Port
    TELEGRAM_API_KEY: str
    TELEGRAM_ADMINS: str
    TELEGRAM_USERS: Optional[str]
    TELEGRAM_WORKERS: PositiveInt
    TELEGRAM_APP_HASH: Optional[str]
    TELEGRAM_APP_ID: Optional[str]
    TELEGRAM_BOTNAME: Optional[str]
    TELETHON_SESSION: Optional[str]
    FRONTEND_URL: str
    FRONTEND_PREFIX: str
    ALLOW_PASSWORD_RESET: zero_or_one
    ALLOW_REGISTRATION: zero_or_one
    ALLOW_TERMS_OF_USE: zero_or_one
    REGISTRATION_NOTIFICATIONS: zero_or_one
    SENTRY_URL: Optional[str]
    GA_TRACKING_CODE: Optional[str]
    SHOW_LOGIN: zero_or_one
    ENABLE_FOOTER: zero_or_one
    ENABLE_ANGULAR_SSR: zero_or_one
    ENABLE_YARN_PNP: zero_or_one
    FORCE_SSR_SERVER_MODE: zero_or_one
    ACTIVATE_AUTH: zero_or_one
    AUTH_SERVICE: AUTH_SERVICE_VALUES
    AUTH_DEFAULT_USERNAME: str
    AUTH_DEFAULT_PASSWORD: str
    AUTH_MIN_PASSWORD_LENGTH: NonNegativeInt
    AUTH_FORCE_FIRST_PASSWORD_CHANGE: zero_or_one
    AUTH_MAX_PASSWORD_VALIDITY: NonNegativeInt
    AUTH_DISABLE_UNUSED_CREDENTIALS_AFTER: NonNegativeInt
    AUTH_MAX_LOGIN_ATTEMPTS: NonNegativeInt
    AUTH_LOGIN_BAN_TIME: PositiveInt
    AUTH_SECOND_FACTOR_AUTHENTICATION: zero_or_one
    AUTH_TOTP_VALIDITY_WINDOW: NonNegativeInt
    AUTH_JWT_TOKEN_TTL: PositiveInt
    AUTH_TOKEN_SAVE_FREQUENCY: NonNegativeInt
    AUTH_TOKEN_IP_GRACE_PERIOD: NonNegativeInt
    ALLOW_ACCESS_TOKEN_PARAMETER: zero_or_one
    DEFAULT_DHLEN: PositiveInt

    FORCE_PRODUCTION_TESTS: zero_or_one


class CoreEnvModel(BaseEnvModel, extra=Extra.forbid):
    pass


class CustomEnvModel(BaseEnvModel, extra=Extra.ignore):
    pass


class CoreVariablesModel(BaseModel):
    submodules: Dict[str, SubmoduleModel]
    roles: Dict[str, str]
    env: CoreEnvModel


class CustomVariablesModel(BaseModel):
    submodules: Dict[str, SubmoduleModel]
    roles: Dict[str, str]
    env: CustomEnvModel


class CoreConfigurationModel(BaseModel):
    project: ProjectModel
    tags: Dict[str, str]
    variables: CoreVariablesModel


class CustomConfigurationModel(BaseModel):
    project: ProjectModel
    tags: Dict[str, str]
    variables: CustomVariablesModel


def read_configuration(
    default_file_path: Path,
    base_project_path: Path,
    projects_path: Path,
    submodules_path: Path,
    read_extended: bool = True,
    production: bool = False,
) -> Tuple[Configuration, Optional[str], Optional[Path], Configuration]:
    """
    Read default configuration
    """

    custom_configuration = load_yaml_file(
        file=base_project_path.joinpath(PROJECT_CONF_FILENAME)
    )

    # Verify custom project configuration
    project = custom_configuration.get("project")
    # Can't be tested because it is included in default configuration
    if project is None:  # pragma: no cover
        raise AttributeError("Missing project configuration")

    variables = ["title", "description", "version", "rapydo"]

    for key in variables:
        # Can't be tested because it is included in default configuration
        if project.get(key) is None:  # pragma: no cover

            print_and_exit(
                "Project not configured, missing key '{}' in file {}/{}",
                key,
                base_project_path,
                PROJECT_CONF_FILENAME,
            )

    base_configuration = load_yaml_file(
        file=default_file_path.joinpath(PROJECTS_DEFAULTS_FILE)
    )
    # Prevent any change due to the mix_configuration
    base_configuration_copy = deepcopy(base_configuration)

    if production:
        base_prod_conf = load_yaml_file(
            file=default_file_path.joinpath(PROJECTS_PROD_DEFAULTS_FILE)
        )
        base_configuration = mix_configuration(base_configuration, base_prod_conf)

    if read_extended:
        extended_project = project.get("extends")
    else:
        extended_project = None
    if extended_project is None:
        # Mix default and custom configuration
        return (
            mix_configuration(base_configuration, custom_configuration),
            None,
            None,
            base_configuration_copy,
        )

    extends_from = project.get("extends_from") or "projects"

    if extends_from == "projects":
        extend_path = projects_path.joinpath(extended_project)
    elif extends_from.startswith("submodules/"):  # pragma: no cover
        repository_name = (extends_from.split("/")[1]).strip()
        if repository_name == "":
            print_and_exit("Invalid repository name in extends_from, name is empty")

        extend_path = submodules_path.joinpath(
            repository_name, projects_path, extended_project
        )
    else:  # pragma: no cover
        suggest = "Expected values: 'projects' or 'submodules/${REPOSITORY_NAME}'"
        print_and_exit("Invalid extends_from parameter: {}.\n{}", extends_from, suggest)

    if not extend_path.exists():  # pragma: no cover
        print_and_exit("From project not found: {}", extend_path)

    extended_configuration = load_yaml_file(
        file=extend_path.joinpath(PROJECT_CONF_FILENAME)
    )

    m1 = mix_configuration(base_configuration, extended_configuration)
    return (
        mix_configuration(m1, custom_configuration),
        extended_project,
        Path(extend_path),
        base_configuration_copy,
    )


# This function is not mypy-friend after the introduction of TypedDict
# TypedDict key must be a string literal;
# This use case is not supported by mypy
# https://github.com/python/mypy/issues/7178
def mix_configuration(
    base: Optional[Configuration], custom: Optional[Configuration]
) -> Configuration:
    # WARNING: This function has the side effect of changing the input base dict!

    if base is None:
        base = {}

    if custom is None:
        return base

    for key, elements in custom.items():

        if key not in base:
            # TypedDict key must be a string literal;
            base[key] = custom[key]  # type: ignore
            continue

        if elements is None:  # pragma: no cover
            # TypedDict key must be a string literal;
            if isinstance(base[key], dict):  # type: ignore
                log.warning("Cannot replace {} with empty list", key)
                continue

        if isinstance(elements, dict):
            # TypedDict key must be a string literal;
            base[key] = mix_configuration(base[key], custom[key])  # type: ignore

        elif isinstance(elements, list):
            for e in elements:  # pragma: no cover
                # TypedDict key must be a string literal;
                base[key].append(e)  # type: ignore
        else:
            # TypedDict key must be a string literal;
            base[key] = elements  # type: ignore

    return base


def load_yaml_file(
    file: Path, keep_order: bool = False, is_optional: bool = False
) -> Configuration:
    """
    Import any data from a YAML file.
    """

    if not file.exists():
        if not is_optional:
            print_and_exit("Failed to read {}: File does not exist", file)
        return {}

    with open(file) as fh:
        try:
            docs = list(yaml.safe_load_all(fh))

            if not docs:
                print_and_exit("YAML file is empty: {}", file)

            # Return value of yaml.safe_load_all is un-annotated and considered as Any
            # But we known that it is a Dict Configuration-compliant
            return cast(Configuration, docs[0])

        except Exception as e:
            # # IF dealing with a strange exception string (escaped)
            # import codecs
            # error, _ = codecs.getdecoder("unicode_escape")(str(error))

            print_and_exit("Failed to read [{}]: {}", file, str(e))


def read_composer_yamls(config_files: List[Path]) -> Tuple[List[Path], List[Path]]:

    base_files: List[Path] = []
    all_files: List[Path] = []

    # YAML CHECK UP
    for path in config_files:

        try:

            # This is to verify that mandatory files exist and yml syntax is valid
            conf = load_yaml_file(file=path, is_optional=False)

            if conf.get("version") != COMPOSE_FILE_VERSION:  # pragma: no cover
                log.warning(
                    "Compose file version in {} is {}, expected {}",
                    path,
                    conf.get("version"),
                    COMPOSE_FILE_VERSION,
                )

            if path.exists():
                all_files.append(path)

                # Base files are those loaded from CONFS_DIR
                if CONFS_DIR in path.parents:
                    base_files.append(path)

        except KeyError as e:  # pragma: no cover

            print_and_exit("Error reading {}: {}", path, str(e))

    return all_files, base_files


def validate_configuration(conf: Configuration, core: bool) -> None:
    if conf:

        try:
            if core:
                CoreConfigurationModel(**conf)
            else:
                CustomConfigurationModel(**conf)
        except ValidationError as e:
            for field in str(e).split("\n")[1::2]:
                # field is like:
                # "variables -> env -> XYZ"
                # this way it is converted in key = variables.env.XYZ
                key = ".".join(field.split(" -> "))
                log.error(
                    "Invalid value for {}: {}", field, glom(conf, key, default=None)
                )
            print_and_exit(str(e))


def validate_env(env: Dict[str, EnvType]) -> None:
    try:
        BaseEnvModel(**env)
    except ValidationError as e:
        for field in str(e).split("\n")[1::2]:
            log.error("Invalid value for {}: {}", field, env.get(field, "N/A"))
        print_and_exit(str(e))
