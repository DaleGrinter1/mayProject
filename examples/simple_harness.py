"""Minimal example of using agent-sandbox from an external harness."""

from agent_sandbox import SandboxToolPolicy, SandboxTools


def main() -> int:
    """Run one sandbox-backed tool call and print a summary.

    Returns:
        Process-style exit code for the example.
    """

    tools = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("shell",)),
        record_runs=True,
    )
    result = tools.shell(["python", "--version"])
    print(result.to_dict())
    return result.returncode if result.returncode is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
