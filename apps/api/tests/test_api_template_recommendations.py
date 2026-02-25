from fastapi.testclient import TestClient

from multyagents_api.main import app
from multyagents_api.schemas import (
    RoleCreate,
    RunnerLifecycleStatus,
    WorkflowRunCreate,
    WorkflowTemplateCreate,
    WorkflowTemplateRecommendationRequest,
)
from multyagents_api.store import InMemoryStore


client = TestClient(app)


def _create_store_template(store: InMemoryStore, *, role_id: int, name: str, title: str) -> int:
    created = store.create_workflow_template(
        WorkflowTemplateCreate(
            name=name,
            steps=[{"step_id": "single", "role_id": role_id, "title": title, "depends_on": []}],
        )
    )
    return created.id


def _create_api_template(*, role_id: int, project_id: int, name: str, title: str) -> int:
    response = client.post(
        "/workflow-templates",
        json={
            "name": name,
            "project_id": project_id,
            "steps": [{"step_id": "single", "role_id": role_id, "title": title, "depends_on": []}],
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def _record_run_outcome(template_id: int, status: RunnerLifecycleStatus) -> None:
    created = client.post(
        "/workflow-runs",
        json={"workflow_template_id": template_id, "task_ids": [], "initiated_by": "recommendation-test"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_ids"][0]
    status_update = client.post(f"/runner/tasks/{task_id}/status", json={"status": status.value})
    assert status_update.status_code == 200


def test_store_recommendations_rank_by_intent_match_without_history() -> None:
    store = InMemoryStore()
    role = store.create_role(RoleCreate(name="recommendation-role", context7_enabled=True))
    bugfix_template_id = _create_store_template(
        store,
        role_id=role.id,
        name="bugfix-fast-lane",
        title="Reproduce and fix the bug quickly",
    )
    _create_store_template(
        store,
        role_id=role.id,
        name="feature-delivery",
        title="Implement and test a new feature",
    )

    response = store.recommend_workflow_templates(
        WorkflowTemplateRecommendationRequest(
            query="Need a bugfix for checkout regression",
            use_history=False,
            limit=3,
        )
    )

    assert "bugfix" in response.detected_intents
    assert response.recommendations[0].workflow_template_id == bugfix_template_id
    assert "Intent match: bugfix." in response.recommendations[0].reason


def test_store_recommendations_use_history_heuristics() -> None:
    store = InMemoryStore()
    role = store.create_role(RoleCreate(name="recommendation-history-role", context7_enabled=True))
    incident_hotfix_id = _create_store_template(
        store,
        role_id=role.id,
        name="incident-hotfix-lane",
        title="Contain outage and apply hotfix",
    )
    incident_review_id = _create_store_template(
        store,
        role_id=role.id,
        name="incident-review-lane",
        title="Summarize incident findings for follow-up",
    )

    for _ in range(3):
        run = store.create_workflow_run(WorkflowRunCreate(workflow_template_id=incident_hotfix_id, task_ids=[]))
        store.update_task_runner_status(run.task_ids[0], status=RunnerLifecycleStatus.SUCCESS)
    for _ in range(3):
        run = store.create_workflow_run(WorkflowRunCreate(workflow_template_id=incident_review_id, task_ids=[]))
        store.update_task_runner_status(run.task_ids[0], status=RunnerLifecycleStatus.FAILED)

    response = store.recommend_workflow_templates(
        WorkflowTemplateRecommendationRequest(
            query="incident hotfix for production outage",
            use_history=True,
            limit=2,
        )
    )

    assert response.recommendations[0].workflow_template_id == incident_hotfix_id
    assert response.recommendations[0].historical_success_rate == 100.0
    assert response.recommendations[1].workflow_template_id == incident_review_id
    assert response.recommendations[1].historical_success_rate == 0.0


def test_api_workflow_template_recommend_endpoint_returns_ranked_items() -> None:
    project = client.post(
        "/projects",
        json={
            "name": "recommendation-project",
            "root_path": "/tmp/multyagents/recommendation-project",
            "allowed_paths": ["/tmp/multyagents/recommendation-project/src"],
        },
    )
    assert project.status_code == 200
    project_id = project.json()["id"]

    role = client.post("/roles", json={"name": "recommendation-api-role", "context7_enabled": True})
    assert role.status_code == 200
    role_id = role.json()["id"]

    incident_hotfix_id = _create_api_template(
        role_id=role_id,
        project_id=project_id,
        name="incident-hotfix-lane",
        title="Contain outage and apply hotfix",
    )
    incident_review_id = _create_api_template(
        role_id=role_id,
        project_id=project_id,
        name="incident-review-lane",
        title="Summarize incident findings for follow-up",
    )

    for _ in range(2):
        _record_run_outcome(incident_hotfix_id, RunnerLifecycleStatus.SUCCESS)
    for _ in range(2):
        _record_run_outcome(incident_review_id, RunnerLifecycleStatus.FAILED)

    response = client.post(
        "/workflow-templates/recommend",
        json={
            "query": "Need an incident hotfix workflow for a production outage",
            "project_id": project_id,
            "use_history": True,
            "limit": 1,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "incident" in body["detected_intents"]
    assert len(body["recommendations"]) == 1
    top = body["recommendations"][0]
    assert top["workflow_template_id"] == incident_hotfix_id
    assert top["historical_runs"] == 2
    assert top["historical_success_rate"] == 100.0
    assert "Intent match: incident." in top["reason"]
    assert "Historical success" in top["reason"]


def test_api_workflow_template_recommend_endpoint_rejects_unknown_project() -> None:
    response = client.post(
        "/workflow-templates/recommend",
        json={
            "query": "feature request",
            "project_id": 999999,
            "use_history": True,
        },
    )
    assert response.status_code == 404
    assert "project 999999 not found" in response.json()["detail"]
