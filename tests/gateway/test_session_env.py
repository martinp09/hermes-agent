import os

from gateway.config import Platform
from gateway.run import GatewayRunner
from gateway.session import SessionContext, SessionSource


def test_set_session_env_includes_thread_id(monkeypatch):
    runner = object.__new__(GatewayRunner)
    source = SessionSource(
        platform=Platform.TELEGRAM,
        chat_id="-1001",
        chat_name="Group",
        chat_type="group",
        thread_id="17585",
    )
    context = SessionContext(source=source, connected_platforms=[], home_channels={})

    monkeypatch.delenv("HERMES_SESSION_PLATFORM", raising=False)
    monkeypatch.delenv("HERMES_SESSION_CHAT_ID", raising=False)
    monkeypatch.delenv("HERMES_SESSION_CHAT_NAME", raising=False)
    monkeypatch.delenv("HERMES_SESSION_THREAD_ID", raising=False)

    backup = runner._set_session_env(context)

    assert os.getenv("HERMES_SESSION_PLATFORM") == "telegram"
    assert os.getenv("HERMES_SESSION_CHAT_ID") == "-1001"
    assert os.getenv("HERMES_SESSION_CHAT_NAME") == "Group"
    assert os.getenv("HERMES_SESSION_THREAD_ID") == "17585"

    runner._clear_session_env(backup)


def test_clear_session_env_removes_thread_id(monkeypatch):
    runner = object.__new__(GatewayRunner)

    monkeypatch.setenv("HERMES_SESSION_PLATFORM", "telegram")
    monkeypatch.setenv("HERMES_SESSION_CHAT_ID", "-1001")
    monkeypatch.setenv("HERMES_SESSION_CHAT_NAME", "Group")
    monkeypatch.setenv("HERMES_SESSION_THREAD_ID", "17585")

    runner._clear_session_env()

    assert os.getenv("HERMES_SESSION_PLATFORM") is None
    assert os.getenv("HERMES_SESSION_CHAT_ID") is None
    assert os.getenv("HERMES_SESSION_CHAT_NAME") is None
    assert os.getenv("HERMES_SESSION_THREAD_ID") is None


def test_set_session_env_clears_optional_fields_when_absent(monkeypatch):
    runner = object.__new__(GatewayRunner)
    source = SessionSource(
        platform=Platform.TELEGRAM,
        chat_id="-2002",
        chat_name=None,
        chat_type="dm",
        thread_id=None,
    )
    context = SessionContext(source=source, connected_platforms=[], home_channels={})

    # Seed stale values that should be cleared by _set_session_env().
    monkeypatch.setenv("HERMES_SESSION_CHAT_NAME", "stale-group")
    monkeypatch.setenv("HERMES_SESSION_THREAD_ID", "999")

    backup = runner._set_session_env(context)

    assert os.getenv("HERMES_SESSION_PLATFORM") == "telegram"
    assert os.getenv("HERMES_SESSION_CHAT_ID") == "-2002"
    assert os.getenv("HERMES_SESSION_CHAT_NAME") is None
    assert os.getenv("HERMES_SESSION_THREAD_ID") is None

    runner._clear_session_env(backup)


def test_clear_session_env_restores_previous_values(monkeypatch):
    runner = object.__new__(GatewayRunner)
    source = SessionSource(
        platform=Platform.TELEGRAM,
        chat_id="-3003",
        chat_name="Current",
        chat_type="group",
        thread_id="333",
    )
    context = SessionContext(source=source, connected_platforms=[], home_channels={})

    monkeypatch.setenv("HERMES_SESSION_PLATFORM", "discord")
    monkeypatch.setenv("HERMES_SESSION_CHAT_ID", "old-chat")
    monkeypatch.setenv("HERMES_SESSION_CHAT_NAME", "old-name")
    monkeypatch.setenv("HERMES_SESSION_THREAD_ID", "old-thread")

    backup = runner._set_session_env(context)
    runner._clear_session_env(backup)

    assert os.getenv("HERMES_SESSION_PLATFORM") == "discord"
    assert os.getenv("HERMES_SESSION_CHAT_ID") == "old-chat"
    assert os.getenv("HERMES_SESSION_CHAT_NAME") == "old-name"
    assert os.getenv("HERMES_SESSION_THREAD_ID") == "old-thread"


def test_clear_session_env_supports_nested_restore_order(monkeypatch):
    runner = object.__new__(GatewayRunner)

    monkeypatch.delenv("HERMES_SESSION_PLATFORM", raising=False)
    monkeypatch.delenv("HERMES_SESSION_CHAT_ID", raising=False)
    monkeypatch.delenv("HERMES_SESSION_CHAT_NAME", raising=False)
    monkeypatch.delenv("HERMES_SESSION_THREAD_ID", raising=False)

    outer_source = SessionSource(
        platform=Platform.TELEGRAM,
        chat_id="outer",
        chat_name="Outer",
        chat_type="group",
        thread_id="101",
    )
    inner_source = SessionSource(
        platform=Platform.TELEGRAM,
        chat_id="inner",
        chat_name="Inner",
        chat_type="group",
        thread_id="202",
    )

    outer_ctx = SessionContext(source=outer_source, connected_platforms=[], home_channels={})
    inner_ctx = SessionContext(source=inner_source, connected_platforms=[], home_channels={})

    backup_outer = runner._set_session_env(outer_ctx)
    backup_inner = runner._set_session_env(inner_ctx)

    assert os.getenv("HERMES_SESSION_CHAT_ID") == "inner"

    runner._clear_session_env(backup_inner)
    assert os.getenv("HERMES_SESSION_CHAT_ID") == "outer"
    assert os.getenv("HERMES_SESSION_CHAT_NAME") == "Outer"
    assert os.getenv("HERMES_SESSION_THREAD_ID") == "101"

    runner._clear_session_env(backup_outer)
    assert os.getenv("HERMES_SESSION_PLATFORM") is None
    assert os.getenv("HERMES_SESSION_CHAT_ID") is None
    assert os.getenv("HERMES_SESSION_CHAT_NAME") is None
    assert os.getenv("HERMES_SESSION_THREAD_ID") is None
