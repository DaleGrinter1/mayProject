"""Testing pattern for harnesses that use agent-sandbox."""

from __future__ import annotations

import json

from agent_sandbox import create_fake_sandbox_tools


def main() -> int:
    """Run fake tool calls and print their structured result dictionaries."""

    tools = create_fake_sandbox_tools()
    results = [
        tools.shell(["python", "--version"]),
        tools.python_code("print('hello')"),
        tools.screenshot("https://example.com"),
    ]
    print(json.dumps([result.to_dict() for result in results], indent=2))
    return int(any(result.status != "succeeded" for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
