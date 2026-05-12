from pathlib import Path
import tomllib

from pydantic import BaseModel, ConfigDict


class AgentSandboxConfig(BaseModel):
    """Stores local defaults for agent-sandbox commands.

    Attributes:
        app_name: The Modal app name to use by default.
        artifacts_dir: The local folder for generated and copied files.
    """

    model_config = ConfigDict(frozen=True)

    app_name: str = "my-app"
    artifacts_dir: Path = Path("artifacts")


def load_config(path: Path = Path("pyproject.toml")) -> AgentSandboxConfig:
    """Reads agent-sandbox settings from pyproject.toml.

    Args:
        path: The pyproject file to read.

    Returns:
        The project settings, with defaults for missing values.
    """

    if not path.exists():
        return AgentSandboxConfig()

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    settings = data.get("tool", {}).get("agent-sandbox", {})
    return AgentSandboxConfig(**settings)
