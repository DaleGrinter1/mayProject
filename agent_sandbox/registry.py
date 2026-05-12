from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_sandbox.tools import SandboxTools, ToolResult


@dataclass(frozen=True)
class ToolSpec:
    """Describes a sandbox-backed tool for dynamic harnesses.

    Attributes:
        name: Stable registry name used with `call_tool`.
        description: Human-readable tool purpose.
        input_schema: JSON Schema-like object for tool arguments.
    """

    name: str
    description: str
    input_schema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the tool spec for harnesses and logs.

        Returns:
            JSON-friendly tool spec dictionary.
        """

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": dict(self.input_schema),
        }


@dataclass(frozen=True)
class SandboxToolRegistry:
    """Dynamic adapter around `SandboxTools` for agent harnesses.

    Harnesses can list policy-allowed tools and call them by name without
    coupling planners to Python method names.
    """

    tools: SandboxTools

    def list_tools(self) -> tuple[ToolSpec, ...]:
        """List tools allowed by the wrapped `SandboxTools` policy.

        Returns:
            Tool specs for currently allowed tools.
        """

        specs: list[ToolSpec] = []
        if self.tools.policy.allows("shell"):
            specs.append(SHELL_SPEC)
        if self.tools.policy.allows("python"):
            specs.extend((PYTHON_CODE_SPEC, PYTHON_SCRIPT_SPEC))
        if self.tools.policy.allows("browser"):
            specs.append(SCREENSHOT_SPEC)
        return tuple(specs)

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> ToolResult:
        """Call a sandbox-backed tool by registry name.

        Args:
            name: Tool name from `list_tools`.
            arguments: JSON-style tool arguments.

        Returns:
            Structured SDK result from the selected tool.

        Raises:
            ValueError: If the name or arguments are invalid.
            PermissionError: If policy blocks the selected tool.
        """

        match name:
            case "shell":
                _reject_unknown(
                    arguments,
                    allowed=("command", "timeout", "idle_timeout"),
                )
                return self.tools.shell(
                    _string_list(arguments, "command"),
                    timeout=_optional_int(arguments, "timeout"),
                    idle_timeout=_optional_int(arguments, "idle_timeout"),
                )
            case "python_code":
                _reject_unknown(arguments, allowed=("code", "args"))
                return self.tools.python_code(
                    _required_string(arguments, "code"),
                    *_string_list(arguments, "args", default=()),
                )
            case "python_script":
                _reject_unknown(arguments, allowed=("script_path", "args"))
                return self.tools.python_script(
                    Path(_required_string(arguments, "script_path")),
                    *_string_list(arguments, "args", default=()),
                )
            case "screenshot":
                _reject_unknown(arguments, allowed=("url", "output_dir"))
                output_dir = _optional_string(arguments, "output_dir")
                return self.tools.screenshot(
                    _required_string(arguments, "url"),
                    output_dir=Path(output_dir) if output_dir else None,
                )

        raise ValueError(f"Unknown sandbox tool: {name}")


def _reject_unknown(arguments: Mapping[str, Any], allowed: tuple[str, ...]) -> None:
    unknown = sorted(set(arguments) - set(allowed))
    if unknown:
        names = ", ".join(unknown)
        raise ValueError(f"Unknown tool argument(s): {names}.")


def _required_string(arguments: Mapping[str, Any], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Tool argument '{name}' must be a non-empty string.")
    return value


def _optional_string(arguments: Mapping[str, Any], name: str) -> str | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"Tool argument '{name}' must be a non-empty string.")
    return value


def _string_list(
    arguments: Mapping[str, Any],
    name: str,
    default: tuple[str, ...] | None = None,
) -> list[str]:
    value = arguments.get(name, default)
    if value is None:
        raise ValueError(f"Tool argument '{name}' is required.")
    if not isinstance(value, list | tuple) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(f"Tool argument '{name}' must be a list of strings.")
    return list(value)


def _optional_int(arguments: Mapping[str, Any], name: str) -> int | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"Tool argument '{name}' must be an integer.")
    return value


SHELL_SPEC = ToolSpec(
    name="shell",
    description="Run a shell command in a temporary sandbox.",
    input_schema={
        "type": "object",
        "properties": {
            "command": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Command words to execute.",
            },
            "timeout": {"type": "integer"},
            "idle_timeout": {"type": "integer"},
        },
        "required": ["command"],
        "additionalProperties": False,
    },
)

PYTHON_CODE_SPEC = ToolSpec(
    name="python_code",
    description="Run Python source code in a temporary sandbox.",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "args": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["code"],
        "additionalProperties": False,
    },
)

PYTHON_SCRIPT_SPEC = ToolSpec(
    name="python_script",
    description="Run a local Python script in a temporary sandbox.",
    input_schema={
        "type": "object",
        "properties": {
            "script_path": {"type": "string"},
            "args": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["script_path"],
        "additionalProperties": False,
    },
)

SCREENSHOT_SPEC = ToolSpec(
    name="screenshot",
    description="Capture a web page screenshot and text observation.",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "output_dir": {"type": "string"},
        },
        "required": ["url"],
        "additionalProperties": False,
    },
)
