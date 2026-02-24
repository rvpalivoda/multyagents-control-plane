from pathlib import Path

from multyagents_api.schemas import ArtifactCreate, EventCreate, RoleCreate, TaskCreate, WorkflowRunCreate
from multyagents_api.store import InMemoryStore


def test_store_restores_snapshot_from_state_file(tmp_path: Path) -> None:
    state_file = tmp_path / "api-state.json"
    first = InMemoryStore(state_file=str(state_file))

    role = first.create_role(
        RoleCreate(
            name="persist-role",
            context7_enabled=True,
            system_prompt="persist me",
            allowed_tools=["read", "write"],
            skill_packs=["core"],
            execution_constraints={"max_steps": 5},
        )
    )
    task = first.create_task(
        TaskCreate(
            role_id=role.id,
            title="persist task",
            context7_mode="inherit",
            execution_mode="no-workspace",
        )
    )
    run = first.create_workflow_run(
        WorkflowRunCreate(task_ids=[task.id], initiated_by="persistence-test")
    )
    first.dispatch_task(task.id)
    first.create_event(
        EventCreate(
            event_type="agent.note",
            run_id=run.id,
            task_id=task.id,
            producer_role="planner",
            payload={"message": "persisted event"},
        )
    )
    first.create_artifact(
        ArtifactCreate(
            artifact_type="report",
            location="/tmp/multyagents/persistence/report.md",
            summary="persisted artifact",
            producer_task_id=task.id,
            run_id=run.id,
        )
    )

    second = InMemoryStore(state_file=str(state_file))
    restored_role = second.get_role(role.id)
    restored_task = second.get_task(task.id)
    restored_run = second.get_workflow_run(run.id)
    events = second.list_events(run_id=run.id, limit=100)
    artifacts = second.list_artifacts(run_id=run.id, limit=100)

    assert restored_role.name == "persist-role"
    assert restored_role.allowed_tools == ["read", "write"]
    assert restored_task.title == "persist task"
    assert restored_run.id == run.id
    assert any(event.event_type == "workflow_run.created" for event in events)
    assert any(event.event_type == "task.dispatched" for event in events)
    assert any(event.event_type == "agent.note" for event in events)
    assert any(artifact.artifact_type == "report" for artifact in artifacts)
