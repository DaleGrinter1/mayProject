import sys

from agent_sandbox import SandboxToolPolicy, SandboxTools


def main(argv: list[str] | None = None) -> int:
    """Runs one command on a remote computer.

    Args:
        argv: Optional command-line words.

    Returns:
        The remote command's finish code.
    """

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("Usage: agent-sandbox-shell <command> [args...]")

    result = SandboxTools(
        policy=SandboxToolPolicy(allowed_tools=("shell",)),
    ).shell(argv)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.error:
        print(result.error, file=sys.stderr)
    return result.returncode if result.returncode is not None else int(result.status != "succeeded")


if __name__ == "__main__":
    raise SystemExit(main())
