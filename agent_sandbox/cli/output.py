import json

from agent_sandbox.workflows.doctor import DoctorCheck


def print_handle(label: str, handle: object) -> None:
    """Prints one remote computer.

    Args:
        label: A short heading.
        handle: The remote computer details.
    """

    print(label)
    print(f"  id: {handle.object_id}")
    print(f"  app: {handle.app_name}")
    if handle.name:
        print(f"  name: {handle.name}")
    if handle.tags.get("image"):
        print(f"  image: {handle.tags['image']}")
    print(f"  returncode: {handle.returncode}")


def print_handles(handles: list[object]) -> None:
    """Prints remote computers as a table.

    Args:
        handles: Remote computers to show.
    """

    if not handles:
        print("No managed sandboxes found")
        return

    rows = [
        (
            handle.name or handle.tags.get("name", "-"),
            handle.tags.get("image", "-"),
            sandbox_state(handle),
            handle.object_id,
        )
        for handle in handles
    ]
    print_table(("Name", "Image", "State", "Sandbox ID"), rows)


def sandbox_state(handle: object) -> str:
    """Describes whether a remote computer is running.

    Args:
        handle: The remote computer details.

    Returns:
        A short state label for people to read.
    """

    return "running" if handle.returncode is None else f"done:{handle.returncode}"


def handle_payload(handle: object) -> dict[str, object]:
    """Builds a structured view of one remote computer.

    Args:
        handle: The remote computer details.

    Returns:
        A plain dictionary for JSON output.
    """

    name = handle.name or handle.tags.get("name")
    return {
        "name": name,
        "sandbox_id": handle.object_id,
        "app_name": handle.app_name,
        "image": handle.tags.get("image"),
        "state": sandbox_state(handle),
        "returncode": handle.returncode,
        "tags": dict(handle.tags),
    }


def print_json(payload: object) -> None:
    """Prints structured output as formatted JSON.

    Args:
        payload: The JSON-compatible value to print.
    """

    print(json.dumps(payload, indent=2, sort_keys=True))


def print_inspection(handle: object) -> None:
    """Prints detailed information about one remote computer.

    Args:
        handle: The remote computer details.
    """

    name = handle.name or handle.tags.get("name", "-")
    image = handle.tags.get("image", "-")
    print_table(
        ("Field", "Value"),
        [
            ("Name", name),
            ("Sandbox ID", handle.object_id),
            ("App name", handle.app_name),
            ("Image", image),
            ("State", sandbox_state(handle)),
        ],
    )

    tag_rows = sorted(handle.tags.items())
    print("\nTags")
    if tag_rows:
        print_table(("Tag", "Value"), tag_rows)
    else:
        print("(none)")


def print_terminated(handles: list[object]) -> None:
    """Prints the remote computers that were stopped.

    Args:
        handles: Remote computers that were stopped.
    """

    if not handles:
        print("No managed sandboxes found")
        return

    rows = [
        (
            handle.name or handle.tags.get("name", "-"),
            handle.tags.get("image", "-"),
            handle.object_id,
        )
        for handle in handles
    ]
    print_table(("Name", "Image", "Sandbox ID"), rows)
    print(f"Terminated {len(handles)} managed sandbox(es).")


def print_doctor(checks: list[DoctorCheck]) -> None:
    """Prints setup checks as a table.

    Args:
        checks: Setup checks to show.
    """

    rows = [
        (check.name, "ok" if check.ok else "needs help", check.message)
        for check in checks
    ]
    print_table(("Check", "Status", "Message"), rows)


def print_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    """Prints rows with simple borders.

    Args:
        headers: The table column names.
        rows: The table rows.
    """

    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    border = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    header = "| " + " | ".join(
        text.ljust(widths[index]) for index, text in enumerate(headers)
    ) + " |"

    print(border)
    print(header)
    print(border)
    for row in rows:
        print(
            "| "
            + " | ".join(text.ljust(widths[index]) for index, text in enumerate(row))
            + " |"
        )
    print(border)
