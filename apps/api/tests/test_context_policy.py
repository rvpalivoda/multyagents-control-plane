from multyagents_api.context_policy import resolve_context7_enabled
from multyagents_api.schemas import Context7Mode


def test_context7_resolver_inherit_uses_role_default() -> None:
    assert resolve_context7_enabled(role_context7_enabled=True, task_mode=Context7Mode.INHERIT) is True
    assert resolve_context7_enabled(role_context7_enabled=False, task_mode=Context7Mode.INHERIT) is False


def test_context7_resolver_force_on_has_precedence() -> None:
    assert resolve_context7_enabled(role_context7_enabled=False, task_mode=Context7Mode.FORCE_ON) is True


def test_context7_resolver_force_off_has_precedence() -> None:
    assert resolve_context7_enabled(role_context7_enabled=True, task_mode=Context7Mode.FORCE_OFF) is False
