from __future__ import annotations

from multyagents_api.schemas import Context7Mode


def resolve_context7_enabled(*, role_context7_enabled: bool, task_mode: Context7Mode) -> bool:
    if task_mode == Context7Mode.FORCE_ON:
        return True
    if task_mode == Context7Mode.FORCE_OFF:
        return False
    return role_context7_enabled
