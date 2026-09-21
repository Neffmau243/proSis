"""The operator-facing surface of ``create_admin``.

``create_admin`` itself is exercised against MySQL elsewhere; what is asserted
here is the command line: the hidden prompt, the confirmation of the typed
password, and the fact that a mismatch never reaches the database.
"""

from __future__ import annotations

import pytest

from app.scripts.create_admin import main


def test_password_is_requested_hidden_and_confirmed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prompts: list[str] = []
    calls: list[tuple[str, str]] = []

    def fake_getpass(prompt: str) -> str:
        prompts.append(prompt)
        return "12345678"

    monkeypatch.setattr("app.scripts.create_admin.getpass", fake_getpass)
    monkeypatch.setattr("sys.argv", ["create_admin", "--username", "jefe.salud"])
    monkeypatch.setattr(
        "app.scripts.create_admin.create_admin",
        lambda username, password: calls.append((username, password)) or 3,
    )

    main()

    assert len(prompts) == 2, "La contraseña debe pedirse dos veces"
    assert calls == [("jefe.salud", "12345678")]
    assert "Usuario ADMIN creado con id 3." in capsys.readouterr().out


def test_a_mismatched_confirmation_never_creates_the_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter(["12345678", "87654321"])
    monkeypatch.setattr("app.scripts.create_admin.getpass", lambda *_: next(answers))
    monkeypatch.setattr("sys.argv", ["create_admin", "--username", "jefe.salud"])
    created: list[str] = []
    monkeypatch.setattr(
        "app.scripts.create_admin.create_admin",
        lambda username, password: created.append(username) or 1,
    )

    with pytest.raises(ValueError, match="no coinciden"):
        main()

    assert created == []


def test_a_password_on_the_command_line_skips_the_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(*_: object) -> str:
        raise AssertionError("No debe solicitarse la contraseña de forma interactiva")

    monkeypatch.setattr("app.scripts.create_admin.getpass", explode)
    monkeypatch.setattr(
        "sys.argv",
        ["create_admin", "--username", "jefe.salud", "--password", "12345678"],
    )
    received: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "app.scripts.create_admin.create_admin",
        lambda username, password: received.append((username, password)) or 5,
    )

    main()

    assert received == [("jefe.salud", "12345678")]


def test_the_command_requires_a_username(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["create_admin"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 2
