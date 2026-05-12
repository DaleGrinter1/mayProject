from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import json
from pathlib import Path
from time import time
from typing import Any
from uuid import uuid4

from agent_sandbox.registry import SandboxToolRegistry, ToolSpec
from agent_sandbox.sandbox.results import utc_now
from agent_sandbox.tools import ToolResult


DEFAULT_AUDIT_DIR = Path(".agent-sandbox") / "audit"


@dataclass(frozen=True)
class ToolCall:
    """Structured tool call envelope used by custom harnesses.

    Attributes:
        tool: Registry tool name to call.
        arguments: JSON-style tool arguments.
        call_id: Optional harness-provided call identifier.
        agent_id: Optional harness agent identifier.
        task_id: Optional harness task identifier.
        metadata: Extra harness metadata to carry into result/audit records.
    """

    tool: str
    arguments: dict[str, Any]
    call_id: str | None = None
    agent_id: str | None = None
    task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the call envelope for audit logs.

        Returns:
            JSON-friendly call dictionary.
        """

        return {
            "tool": self.tool,
            "arguments": dict(self.arguments),
            "call_id": self.call_id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SandboxToolExecutor:
    """Harness-facing invocation layer around `SandboxToolRegistry`.

    The executor keeps dynamic discovery/calls from the registry while adding
    call context propagation and optional audit logging.
    """

    registry: SandboxToolRegistry
    audit_dir: Path | str | None = None

    def list_tools(self) -> tuple[ToolSpec, ...]:
        """List policy-allowed tools.

        Returns:
            Tool specs from the wrapped registry.
        """

        return self.registry.list_tools()

    def call(self, call: ToolCall) -> ToolResult:
        """Execute one harness tool call envelope.

        Args:
            call: Structured tool call.

        Returns:
            Tool result with harness call context copied into metadata.
        """

        started_at = utc_now()
        try:
            result = self.registry.call_tool(call.tool, call.arguments)
        except Exception as exc:
            completed_at = utc_now()
            result = ToolResult(
                status="failed",
                error=str(exc),
                error_code=_exception_error_code(exc),
                metadata={"tool": call.tool},
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=max(
                    0,
                    int((completed_at - started_at).total_seconds() * 1000),
                ),
            )
        final = self._with_call_context(result, call)
        self._write_audit(call, final)
        return final

    def call_dict(self, payload: Mapping[str, Any]) -> ToolResult:
        """Execute one harness call from a plain mapping.

        Args:
            payload: JSON-style call envelope.

        Returns:
            Tool result with harness call context copied into metadata.
        """

        try:
            call = tool_call_from_mapping(payload)
        except Exception as exc:
            result = _failed_result(
                error=str(exc),
                error_code=_exception_error_code(exc),
                tool=_payload_tool(payload),
            )
            self._write_raw_audit(payload, result)
            return result
        return self.call(call)

    def _with_call_context(self, result: ToolResult, call: ToolCall) -> ToolResult:
        metadata = {
            **result.metadata,
            "call_id": call.call_id,
            "agent_id": call.agent_id,
            "task_id": call.task_id,
            "call_metadata": dict(call.metadata),
        }
        return ToolResult(
            status=result.status,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            artifacts=result.artifacts,
            metadata=metadata,
            error=result.error,
            error_code=result.error_code,
            run_id=result.run_id,
            started_at=result.started_at,
            completed_at=result.completed_at,
            duration_ms=result.duration_ms,
            run_dir=result.run_dir,
        )

    def _write_audit(self, call: ToolCall, result: ToolResult) -> None:
        if self.audit_dir is None:
            return
        audit_dir = Path(self.audit_dir)
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_id = call.call_id or uuid4().hex[:8]
        path = audit_dir / f"{int(time() * 1000)}-{_safe_slug(audit_id)}.json"
        payload = {
            "call": call.to_dict(),
            "result": result.to_dict(),
            "status": result.status,
            "error_code": result.error_code,
            "artifacts": [artifact.to_dict() for artifact in result.artifacts],
            "recorded_at": utc_now().isoformat(),
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _write_raw_audit(
        self,
        payload: Mapping[str, Any],
        result: ToolResult,
    ) -> None:
        if self.audit_dir is None:
            return
        audit_dir = Path(self.audit_dir)
        audit_dir.mkdir(parents=True, exist_ok=True)
        path = audit_dir / f"{int(time() * 1000)}-invalid-tool-call.json"
        audit_payload = {
            "call": dict(payload),
            "result": result.to_dict(),
            "status": result.status,
            "error_code": result.error_code,
            "artifacts": [],
            "recorded_at": utc_now().isoformat(),
        }
        path.write_text(
            json.dumps(audit_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def tool_call_from_mapping(payload: Mapping[str, Any]) -> ToolCall:
    """Build a `ToolCall` from a JSON-style mapping.

    Args:
        payload: Mapping with tool, arguments, and optional context fields.

    Returns:
        Validated tool call envelope.
    """

    tool = payload.get("tool")
    if not isinstance(tool, str) or not tool:
        raise ValueError("Tool call field 'tool' must be a non-empty string.")

    arguments = payload.get("arguments")
    if not isinstance(arguments, dict):
        raise ValueError("Tool call field 'arguments' must be an object.")

    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("Tool call field 'metadata' must be an object.")

    return ToolCall(
        tool=tool,
        arguments=dict(arguments),
        call_id=_optional_string(payload, "call_id"),
        agent_id=_optional_string(payload, "agent_id"),
        task_id=_optional_string(payload, "task_id"),
        metadata=dict(metadata),
    )


def _optional_string(payload: Mapping[str, Any], name: str) -> str | None:
    value = payload.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"Tool call field '{name}' must be a non-empty string.")
    return value


def _exception_error_code(exc: Exception) -> str:
    if isinstance(exc, PermissionError):
        return "policy_denied"
    if isinstance(exc, ValueError):
        return "invalid_arguments"
    return "tool_exception"


def _failed_result(error: str, error_code: str, tool: str) -> ToolResult:
    completed_at = utc_now()
    return ToolResult(
        status="failed",
        error=error,
        error_code=error_code,
        metadata={"tool": tool},
        started_at=completed_at,
        completed_at=completed_at,
        duration_ms=0,
    )


def _payload_tool(payload: Mapping[str, Any]) -> str:
    tool = payload.get("tool")
    return tool if isinstance(tool, str) and tool else "<invalid>"


def _safe_slug(text: str) -> str:
    slug = "".join(c if c.isalnum() or c in ".-" else "-" for c in text.lower())
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "tool-call"
