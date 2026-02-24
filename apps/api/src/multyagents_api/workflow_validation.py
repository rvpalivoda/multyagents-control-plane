from __future__ import annotations

from collections import deque
from typing import Protocol


class StepLike(Protocol):
    step_id: str
    depends_on: list[str]


def validate_workflow_dag(steps: list[StepLike]) -> None:
    step_ids = [step.step_id for step in steps]
    unique_step_ids = set(step_ids)

    if len(unique_step_ids) != len(step_ids):
        raise ValueError("workflow step_id values must be unique")

    graph: dict[str, list[str]] = {step_id: [] for step_id in step_ids}
    indegree: dict[str, int] = {step_id: 0 for step_id in step_ids}

    for step in steps:
        for dependency in step.depends_on:
            if dependency not in unique_step_ids:
                raise ValueError(f"workflow dependency '{dependency}' is not a known step_id")
            if dependency == step.step_id:
                raise ValueError("workflow step cannot depend on itself")
            graph[dependency].append(step.step_id)
            indegree[step.step_id] += 1

    queue = deque([step_id for step_id, degree in indegree.items() if degree == 0])
    visited = 0

    while queue:
        current = queue.popleft()
        visited += 1
        for next_step in graph[current]:
            indegree[next_step] -= 1
            if indegree[next_step] == 0:
                queue.append(next_step)

    if visited != len(step_ids):
        raise ValueError("workflow graph contains a cycle")
