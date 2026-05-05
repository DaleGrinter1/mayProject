import sys

from mayproject.primitives.shell import ShellPrimitive


def main(argv: list[str] | None = None) -> int:
    """Runs one command on a remote computer.

    Args:
        argv: Optional command-line words.

    Returns:
        The remote command's finish code.
    """

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("Usage: may-shell <command> [args...]")

    result = ShellPrimitive().run(argv)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
