from typing import Any, Dict


# Glom is not really intended to return a str, but it is true in my case
def glom(target: Dict[str, Any], spec: str, **kwargs: Any) -> str:
    ...
