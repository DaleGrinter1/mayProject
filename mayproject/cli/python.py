import sys
from pathlib import Path

from mayproject.primitives.python import PythonPrimitive


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("Usage: may-python <script.py> [args...]")

    script_path = Path(argv[0])
    result = PythonPrimitive().run_script(script_path, *argv[1:])
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

