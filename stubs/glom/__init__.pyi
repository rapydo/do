from typing import Any, MutableMapping, TypedDict, TypeVar, Union

T = TypeVar("T")

# Generics TypedDict are not supported
# https://github.com/python/mypy/issues/7719
# => using a mocked Configuration dict as type for glom
class Configuration(TypedDict):
    pass

# With this annotation I'm introducing two STRONG contraints
# 1) default is always required
# 2) the return type is always equivalent to the default type
# These assumptions are only valid for my use cases.
def glom(
    target: Union[Configuration, MutableMapping[str, Any]],
    spec: str,
    default: T,
    **kwargs: Any,
) -> T: ...
