import inspect
import typing
from typing import Any, Dict, List, get_type_hints, Union


def get_json_type(py_type: Any) -> str:
    """Map Python types to JSON schema types."""
    origin = typing.get_origin(py_type)
    args = typing.get_args(py_type)

    if py_type is str:
        return "string"
    elif py_type is int:
        return "integer"
    elif py_type is float:
        return "number"
    elif py_type is bool:
        return "boolean"
    elif py_type is list or origin is list or origin is List:
        return "array"
    elif py_type is dict or origin is dict or origin is Dict:
        return "object"
    elif origin is Union:
        # Handle Optional[X] which is Union[X, None]
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return get_json_type(non_none[0])
        # Union of multiple types - just default to string or create complex schema?
        # For simplicity, string.
        return "string"

    return "string"


def generate_input_schema(func: Any) -> Dict[str, Any]:
    """
    Generate JSON Schema for function arguments.

    Args:
        func: The function to inspect

    Returns:
        JSON Schema dictionary
    """
    try:
        sig = inspect.signature(func)
        try:
            type_hints = get_type_hints(func)
        except Exception:
            # Occasionally fails if types aren't resolvable
            type_hints = {}

        properties = {}
        required = []

        for name, param in sig.parameters.items():
            if name in ("self", "cls", "kwargs", "args"):
                continue

            # Get type
            param_type = type_hints.get(name, Any)
            json_type = get_json_type(param_type)

            prop_def = {"type": json_type}

            # Add description if we parsed docstrings (omitted for brevity, can add later)

            properties[name] = prop_def

            # Check if required (no default value)
            if param.default == inspect.Parameter.empty:
                required.append(name)

        return {"type": "object", "properties": properties, "required": required}
    except Exception:
        # Fallback for when inspection failed
        return {"type": "object", "properties": {}, "required": []}
