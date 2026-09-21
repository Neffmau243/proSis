"""Guards of the destructive local reset command.

The command drops the configured database, so the refusal to run outside a
development environment and the password selection are asserted without a
connection.
"""

from __future__ import annotations

import pytest

from app.scripts.reset_demo_database import _read_password, drop_configured_database, main


@pytest.fixture
def _stubbed_rebuild(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace the destructive steps so ``main`` can be driven end to end."""

    events: list[str] = []
    monkeypatch.setattr(
        "app.scripts.reset_demo_database.drop_configured_database",
        lambda: events.append("drop") or "ipress_borrada",
    )
    monkeypatch.setattr(
        "app.scripts.reset_demo_database.create_database_if_missing",
        lambda: events.append("create") or "ipress_reconstruida",
    )
    monkeypatch.setattr(
        "app.scripts.reset_demo_database.upgrade_to_head",
        lambda: events.append("upgrade"),
    )

    def fake_create_admin(username: str, password: str) -> int:
        events.append(f"admin:{username}:{password}")
        return 7

    monkeypatch.setattr(
        "app.scripts.reset_demo_database.create_admin", fake_create_admin
    )
    monkeypatch.setattr(
        "app.scripts.reset_demo_database.seed_demo_data",
        lambda: events.append("seed") or {"adult_patient_id": 1},
    )
    return events


class _StubSettings:
    """Any object exposing the attributes the guard reads."""

    def __init__(self, *, environment: str, url: str) -> None:
        self.environment = environment
        self.sqlalchemy_database_url = url
        self.mysql_database = "sistema_salud_ipress"


@pytest.mark.parametrize("environment", ["production", "PROD", "Production"])
def test_reset_is_blocked_outside_a_development_environment(environment: str) -> None:
    settings = _StubSettings(
        environment=environment,
        url="mysql+pymysql://root@localhost:3306/sistema_salud_ipress",
    )

    with pytest.raises(ValueError, match="bloqueado en producción"):
        drop_configured_database(settings)  # type: ignore[arg-type]


def test_generated_passwords_keep_the_eight_digit_contract() -> None:
    generated = {_read_password(None, generate_password=True) for _ in range(20)}

    assert all(len(password) == 8 and password.isdecimal() for password in generated)
    # A fixed value would be a credential leak once it reaches the console.
    assert len(generated) > 1


def test_explicit_password_is_used_as_given() -> None:
    assert _read_password("12345678", generate_password=False) == "12345678"


def test_prompted_password_must_match_its_confirmation(monkeypatch) -> None:
    answers = iter(["12345678", "87654321"])
    monkeypatch.setattr(
        "app.scripts.reset_demo_database.getpass", lambda *_: next(answers)
    )

    with pytest.raises(ValueError, match="no coinciden"):
        _read_password(None, generate_password=False)


def test_prompted_password_is_accepted_when_it_matches(monkeypatch) -> None:
    answers = iter(["12345678", "12345678"])
    monkeypatch.setattr(
        "app.scripts.reset_demo_database.getpass", lambda *_: next(answers)
    )

    assert _read_password(None, generate_password=False) == "12345678"


def test_main_requires_the_explicit_confirmation_flag(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["reset_demo_database", "--username", "admin"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 2
    # The command must explain how to confirm, never silently rebuild.
    assert "--confirm-delete" in capfd.readouterr().err


def test_main_rejects_ambiguous_password_sources(
    monkeypatch: pytest.MonkeyPatch, _stubbed_rebuild: list[str]
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "reset_demo_database",
            "--confirm-delete",
            "--password",
            "12345678",
            "--generate-password",
        ],
    )

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 2
    assert _stubbed_rebuild == [], "La base no debe tocarse ante argumentos inválidos"


def test_main_rebuilds_the_scene_with_the_demo_credentials(
    monkeypatch: pytest.MonkeyPatch,
    _stubbed_rebuild: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    from app.scripts.seed_demo_data import DEMO_ADMIN_PASSWORD, DEMO_ADMIN_USERNAME

    monkeypatch.setattr(
        "sys.argv",
        ["reset_demo_database", "--confirm-delete", "--demo-credentials"],
    )

    main()

    assert _stubbed_rebuild == [
        "drop",
        "create",
        "upgrade",
        f"admin:{DEMO_ADMIN_USERNAME}:{DEMO_ADMIN_PASSWORD}",
        "seed",
    ]
    output = capsys.readouterr().out
    assert "ipress_borrada" in output
    assert "ADMIN demo" in output
    assert "adult_patient_id=1" in output


def test_main_prints_the_generated_password_only_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    _stubbed_rebuild: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "reset_demo_database",
            "--confirm-delete",
            "--username", "jefe.salud",
            "--generate-password",
        ],
    )

    main()

    generated = [event for event in _stubbed_rebuild if event.startswith("admin:")]
    assert len(generated) == 1
    assert generated[0].startswith("admin:jefe.salud:")
    password = generated[0].split(":")[2]
    assert len(password) == 8 and password.isdecimal()
    output = capsys.readouterr().out
    assert f"Contraseña temporal del ADMIN: {password}" in output
    # An explicit username must never print the demo credentials.
    assert "PROFESIONAL demo" not in output
