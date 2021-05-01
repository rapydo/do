from typing import Any, MutableMapping, TypeVar

T = TypeVar("T")

# With this annotation I'm introducing two STRONG contraints
# 1) default is always required
# 2) the return type is always equivalent to the default type
# These assumptions are only valid for my use cases.
def glom(
    target: MutableMapping[str, Any], spec: str, default: T, **kwargs: Any
) -> T: ...
