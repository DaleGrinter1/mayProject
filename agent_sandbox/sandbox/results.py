from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


DEFAULT_RUN_ROOT = Path(".agent-sandbox") / "runs"


def utc_now() -> datetime:
    return datetime.now(UTC)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def safe_slug(text: str) -> str:
    slug = "".join(c if c.isalnum() or c in ".-" else "-" for c in text.lower())
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "task"


@dataclass(frozen=True)
class Artifact:
    name: str
    kind: str
    path: Path
    mime_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind,
            "path": str(self.path),
        }
        if self.mime_type is not None:
            data["mime_type"] = self.mime_type
        return data


@dataclass(frozen=True)
class SandboxRun:
    run_id: str
    task_kind: str
    started_at: datetime
    artifact_dir: Path
    status: str = "created"
    tags: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    completed_at: datetime | None = None

    def complete(self, status: str, completed_at: datetime | None = None) -> "SandboxRun":
        return replace(
            self,
            status=status,
            completed_at=completed_at or utc_now(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_kind": self.task_kind,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "tags": dict(self.tags),
            "artifact_dir": str(self.artifact_dir),
            "metadata": dict(self.metadata),
        }

    def write_json(self, path: Path) -> None:
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )


@dataclass(frozen=True)
class SandboxResult:
    run: SandboxRun
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    artifacts: tuple[Artifact, ...] = ()
    stdout: str = ""
    stderr: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run": self.run.to_dict(),
            "status": self.status,
            "output": dict(self.output),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
        }

    def write_json(self, path: Path) -> None:
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )


def create_sandbox_run(
    task_kind: str,
    run_root: Path = DEFAULT_RUN_ROOT,
    tags: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
    started_at: datetime | None = None,
    run_id: str | None = None,
) -> SandboxRun:
    started_at = started_at or utc_now()
    run_id = run_id or uuid4().hex[:8]
    run_dir_name = f"{format_timestamp(started_at)}-{safe_slug(task_kind)}-{safe_slug(run_id)[:8]}"
    artifact_dir = run_root / run_dir_name
    artifact_dir.mkdir(parents=True, exist_ok=False)
    return SandboxRun(
        run_id=run_id,
        task_kind=task_kind,
        started_at=started_at,
        artifact_dir=artifact_dir,
        tags=dict(tags or {}),
        metadata=dict(metadata or {}),
    )
