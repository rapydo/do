from typing import Any, MutableMapping, TypeVar


T = TypeVar("T")


def glom(target: MutableMapping[str, Any], spec: str, default: T, **kwargs: Any) -> T:
    ...
