"""Minimal browser tool example for a harness."""

from agent_sandbox import SandboxToolPolicy, SandboxTools


def main() -> int:
    """Capture a page and print the produced artifact paths.

    Returns:
        Zero when the screenshot tool succeeds.
    """

    tools = SandboxTools(policy=SandboxToolPolicy(allowed_tools=("browser",)))
    result = tools.screenshot("https://example.com")
    for artifact in result.artifacts:
        print(f"{artifact.name}: {artifact.path}")
    if result.error:
        print(result.error)
    return int(result.status != "succeeded")


if __name__ == "__main__":
    raise SystemExit(main())
