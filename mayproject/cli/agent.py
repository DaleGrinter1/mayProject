import argparse
import sys
from pathlib import Path

from mayproject.agents import AgentRegistry, EchoAgent
from mayproject.cli.output import print_json, print_table
from mayproject.workflows import AutomationTask, WorkflowCoordinator, WorkflowRun


def main(argv: list[str] | None = None) -> int:
    """Runs agent registry commands."""

    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    registry = default_registry()
    return run_command(args, registry)


def build_parser() -> argparse.ArgumentParser:
    """Builds the agent command parser."""

    parser = argparse.ArgumentParser(prog="may-agent")
    subparsers = parser.add_subparsers(dest="action", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--json", action="store_true")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("objective", nargs="+")
    run_parser.add_argument("--agent", action="append", default=[])
    run_parser.add_argument("--input", action="append", default=[])
    run_parser.add_argument("--run-root", default=".mayproject/runs")
    run_parser.add_argument("--json", action="store_true")

    return parser


def default_registry() -> AgentRegistry:
    """Returns the built-in agents available without extra packages."""

    return AgentRegistry([EchoAgent()])


def run_command(args: argparse.Namespace, registry: AgentRegistry) -> int:
    """Runs the selected agent command."""

    if args.action == "list":
        specs = registry.specs()
        if args.json:
            print_json([spec.to_dict() for spec in specs])
            return 0
        rows = [
            (
                spec.agent_id,
                spec.role,
                ", ".join(spec.allowed_primitives) or "-",
            )
            for spec in specs
        ]
        print_table(("Agent", "Role", "Primitives"), rows)
        return 0

    if args.action == "run":
        selected = selected_registry(registry, args.agent)
        task = AutomationTask(
            " ".join(args.objective),
            inputs=parse_inputs(args.input),
        )
        workflow = WorkflowCoordinator.from_registry(
            selected,
            run_root=Path(args.run_root),
        ).run(task)
        if args.json:
            print_json(workflow.to_dict())
        else:
            print_workflow_summary(workflow)
        return 0 if workflow.status == "succeeded" else 1

    raise ValueError("Unknown agent action")


def selected_registry(registry: AgentRegistry, agent_ids: list[str]) -> AgentRegistry:
    """Builds a registry for the requested agents."""

    if not agent_ids:
        return registry
    return AgentRegistry([registry.get(agent_id) for agent_id in agent_ids])


def parse_inputs(values: list[str]) -> dict[str, str]:
    """Parses repeated key=value command-line inputs."""

    inputs: dict[str, str] = {}
    for value in values:
        key, separator, item = value.partition("=")
        if not key or not separator:
            raise ValueError("Inputs must look like key=value")
        inputs[key] = item
    return inputs


def print_workflow_summary(workflow: WorkflowRun) -> None:
    """Prints a compact workflow result."""

    print(f"Workflow {workflow.status}")
    print(f"  id: {workflow.workflow_id}")
    print(f"  artifacts: {workflow.artifact_dir.resolve()}")
    rows = [
        (
            run.agent.agent_id,
            run.status,
            run.error or "-",
        )
        for run in workflow.agent_runs
    ]
    print_table(("Agent", "Status", "Error"), rows)


if __name__ == "__main__":
    raise SystemExit(main())
