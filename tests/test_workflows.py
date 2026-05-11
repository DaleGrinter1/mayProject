import json
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from mayproject.agents import AgentOutcome, AgentRegistry, AgentSpec, EchoAgent
from mayproject.workflows import AutomationTask, WorkflowCoordinator, create_workflow_run


TEST_TMP_ROOT = Path(".mayproject") / "test-tmp"


def workspace_temp_dir():
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = TEST_TMP_ROOT / uuid4().hex
    path.mkdir()
    return path


class WorkflowStateTests(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)

    def test_create_workflow_run_uses_task_objective_in_directory(self):
        temp_dir = workspace_temp_dir()
        try:
            task = AutomationTask("Research and summarize", task_id="task-1")
            run = create_workflow_run(task, run_root=temp_dir, workflow_id="wf-1")

            self.assertEqual(run.task.task_id, "task-1")
            self.assertEqual(run.workflow_id, "wf-1")
            self.assertIn("workflow-research-and-summarize", run.artifact_dir.name)
            self.assertTrue(run.artifact_dir.exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class WorkflowCoordinatorTests(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)

    def test_coordinator_records_agent_outcomes_and_events(self):
        temp_dir = workspace_temp_dir()
        try:
            agent = AgentSpec(
                agent_id="researcher",
                role="Researcher",
                allowed_primitives=("browser",),
            )
            task = AutomationTask("Find the answer", task_id="task-1")

            def handler(context):
                context.emit_event("agent.note", {"message": "looked around"})
                return AgentOutcome("succeeded", output={"answer": "42"})

            workflow = WorkflowCoordinator([agent], run_root=temp_dir).run(
                task,
                {"researcher": handler},
            )

            self.assertEqual(workflow.status, "succeeded")
            self.assertEqual(workflow.agent_runs[0].agent.agent_id, "researcher")
            self.assertEqual(workflow.agent_runs[0].output, {"answer": "42"})
            self.assertTrue((workflow.artifact_dir / "workflow.json").exists())

            events = [
                json.loads(line)
                for line in (workflow.artifact_dir / "events.jsonl").read_text().splitlines()
            ]
            event_types = [event["event_type"] for event in events]
            self.assertEqual(event_types[0], "workflow.started")
            self.assertIn("agent.note", event_types)
            self.assertEqual(event_types[-1], "workflow.completed")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_coordinator_fails_when_handler_is_missing(self):
        temp_dir = workspace_temp_dir()
        try:
            agent = AgentSpec(agent_id="writer", role="Writer")
            task = AutomationTask("Draft output")
            workflow = WorkflowCoordinator([agent], run_root=temp_dir).run(task, {})

            self.assertEqual(workflow.status, "failed")
            self.assertEqual(workflow.agent_runs[0].status, "failed")
            self.assertIn("No handler", workflow.agent_runs[0].error)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_coordinator_runs_registered_agents(self):
        temp_dir = workspace_temp_dir()
        try:
            registry = AgentRegistry([EchoAgent()])
            task = AutomationTask(
                "Package the agent API",
                task_id="task-1",
                inputs={"audience": "agent authors"},
            )

            workflow = WorkflowCoordinator.from_registry(registry, run_root=temp_dir).run(
                task
            )

            self.assertEqual(workflow.status, "succeeded")
            self.assertEqual(workflow.agent_runs[0].agent.agent_id, "echo")
            self.assertEqual(
                workflow.agent_runs[0].output["objective"],
                "Package the agent API",
            )
            artifact = workflow.agent_runs[0].artifacts[0]
            self.assertEqual(artifact.name, "echo")
            self.assertTrue(artifact.path.exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_registry_rejects_duplicate_agent_ids(self):
        registry = AgentRegistry([EchoAgent()])

        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(EchoAgent())


if __name__ == "__main__":
    unittest.main()
