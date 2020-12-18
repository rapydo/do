from typing import Any, Dict, TypeVar


T = TypeVar("T")


def glom(target: Dict[str, Any], spec: str, default: T, **kwargs: Any) -> T:
    ...
