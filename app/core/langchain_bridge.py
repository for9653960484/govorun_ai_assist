from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from app.tools.base import BaseTool


def _json_type_to_python(prop: dict[str, Any]) -> type[Any]:
    json_type = prop.get("type", "string")
    if json_type == "integer":
        return int
    if json_type == "number":
        return float
    if json_type == "boolean":
        return bool
    return str


def _parameters_to_args_schema(name: str, parameters: dict[str, Any]) -> type[BaseModel]:
    properties = parameters.get("properties", {})
    required = set(parameters.get("required", []))
    fields: dict[str, Any] = {}

    for prop_name, prop_def in properties.items():
        py_type = _json_type_to_python(prop_def)
        field_kwargs: dict[str, Any] = {}
        if description := prop_def.get("description"):
            field_kwargs["description"] = description
        if enum := prop_def.get("enum"):
            field_kwargs["json_schema_extra"] = {"enum": enum}
        if prop_name in required:
            fields[prop_name] = (py_type, Field(**field_kwargs))
        else:
            fields[prop_name] = (py_type | None, Field(default=None, **field_kwargs))

    model_name = "".join(part.capitalize() for part in name.split("_")) + "Input"
    return create_model(model_name, **fields)  # type: ignore[call-overload]


def base_tool_to_langchain(tool: BaseTool) -> StructuredTool:
    """Преобразует инструмент проекта в LangChain StructuredTool."""

    schema = tool.schema()
    parameters = schema.get("parameters", {"type": "object", "properties": {}})
    args_schema = _parameters_to_args_schema(tool.name, parameters)

    async def _arun(**kwargs: Any) -> str:
        result = await tool.run(**kwargs)
        if result.ok:
            return result.message
        return f"Ошибка: {result.message}"

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        coroutine=_arun,
        args_schema=args_schema,
    )


def registry_to_langchain_tools(tools: list[BaseTool]) -> list[StructuredTool]:
    return [base_tool_to_langchain(tool) for tool in tools]
