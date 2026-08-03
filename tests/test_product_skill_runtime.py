"""PROGRAM-CONTENT-01-SKILL-RUNTIME-01 oracles."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.product_skills.importer import ProductSkillImporter
from app.product_skills.router import ProductSkillRouter
from app.schemas.contracts import ProductSkillInstallStatus


@pytest.fixture(autouse=True)
def _cd_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTENT_DIRECTOR_DETERMINISTIC", "true")
    monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "mock")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_importer_valid_builtin_package() -> None:
    reports = ProductSkillImporter().seed_builtins()
    assert len(reports) == 4
    assert all(r.ok for r in reports)
    assert {r.skill_id for r in reports} == {
        "marketsynth.copywriter",
        "marketsynth.visual_generation",
        "marketsynth.xmlriver.wordstat",
        "marketsynth.avito",
    }


def test_importer_path_traversal_denied(tmp_path: Path) -> None:
    bad = tmp_path / "pkg"
    bad.mkdir()
    (bad / "manifest.json").write_text(
        json.dumps(
            {
                "skill_id": "marketsynth.copywriter",
                "name": "x",
                "version": "1.0.0",
                "description": "d",
                "type": "instruction",
            }
        ),
        encoding="utf-8",
    )
    # Create a file that claims traversal in relative listing via symlink if supported
    target = tmp_path / "outside.txt"
    target.write_text("secret", encoding="utf-8")
    link = bad / "escape"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks not available")
    report = ProductSkillImporter().import_directory(bad)
    assert any(f.code == "symlink_forbidden" for f in report.findings)
    assert not report.ok


def test_importer_secret_detection(tmp_path: Path) -> None:
    root = tmp_path / "pkg"
    root.mkdir()
    (root / "notes.py").write_text('api_key = "sk-live-ABCDEFGH123456"\n', encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "skill_id": "marketsynth.copywriter",
                "name": "x",
                "version": "1.0.0",
                "description": "d",
                "type": "instruction",
            }
        ),
        encoding="utf-8",
    )
    report = ProductSkillImporter().import_directory(root)
    assert any(f.code == "secret_detected" for f in report.findings)
    assert not report.ok


def test_importer_dangerous_executable_blocked(tmp_path: Path) -> None:
    root = tmp_path / "pkg"
    root.mkdir()
    (root / "run.sh").write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "skill_id": "marketsynth.copywriter",
                "name": "x",
                "version": "1.0.0",
                "description": "d",
                "type": "instruction",
            }
        ),
        encoding="utf-8",
    )
    report = ProductSkillImporter().import_directory(root)
    assert not report.ok
    assert any(f.code in {"forbidden_file", "dangerous_executable"} for f in report.findings)


def test_router_disabled_skill_excluded() -> None:
    router = ProductSkillRouter(
        install_status={
            "marketsynth.copywriter": ProductSkillInstallStatus.DISABLED,
        }
    )
    decision = router.route(trigger="telegram_post", explicit=False)
    assert decision.manifest is None or decision.manifest.skill_id != "marketsynth.copywriter"
    explicit = router.route(
        skill_id="marketsynth.copywriter",
        explicit=True,
    )
    assert explicit.manifest is None
    assert explicit.reason == "skill_disabled"


def test_router_excludes_unconfigured_avito() -> None:
    router = ProductSkillRouter(
        install_status={
            "marketsynth.avito": ProductSkillInstallStatus.INSTALLED_UNCONFIGURED,
        }
    )
    index = router.compact_index()
    avito = next(i for i in index if i["skill_id"] == "marketsynth.avito")
    assert avito["availability"] == "unconfigured"
    decision = router.route(trigger="avito", explicit=False)
    assert decision.manifest is None or decision.manifest.skill_id != "marketsynth.avito"


def test_router_automatic_copywriter() -> None:
    decision = ProductSkillRouter().route(
        trigger="telegram_post",
        input_type="content_request",
        explicit=False,
    )
    assert decision.manifest is not None
    assert decision.manifest.skill_id == "marketsynth.copywriter"
    assert decision.mode == "automatic"


def test_skills_list_and_avito_unconfigured(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/skills", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    by_id = {row["skill_id"]: row for row in body}
    assert "marketsynth.copywriter" in by_id
    assert by_id["marketsynth.copywriter"]["configured"] is True
    assert by_id["marketsynth.avito"]["configured"] is False
    assert by_id["marketsynth.avito"]["install_status"] == "installed_unconfigured"


def test_skill_run_copywriter_persisted(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Skill Runtime"},
        headers=auth_headers,
    ).json()["id"]
    first = client.post(
        f"/projects/{project_id}/skills/runs",
        headers=auth_headers,
        json={
            "skill_id": "marketsynth.copywriter",
            "trigger": "telegram_post",
            "input_type": "content_request",
            "input_ref": {"content_request_id": "demo"},
            "idempotency_key": "skill-1",
            "explicit": True,
        },
    )
    assert first.status_code == 200, first.text
    run = first.json()
    assert run["status"] == "succeeded"
    assert run["skill_id"] == "marketsynth.copywriter"
    assert run["result_ref"].get("ready_for_content_director") is True
    assert run["result_ref"].get("instruction_loaded") is True
    assert run["result_ref"].get("system_prompt_loaded") is True
    assert run["evidence"].get("system_prompt_chars", 0) > 0

    dup = client.post(
        f"/projects/{project_id}/skills/runs",
        headers=auth_headers,
        json={
            "skill_id": "marketsynth.copywriter",
            "input_type": "content_request",
            "input_ref": {"content_request_id": "demo"},
            "idempotency_key": "skill-1",
            "explicit": True,
        },
    )
    assert dup.status_code == 200
    assert dup.json()["id"] == run["id"]

    got = client.get(
        f"/projects/{project_id}/skills/runs/{run['id']}",
        headers=auth_headers,
    )
    assert got.status_code == 200
    assert got.json()["id"] == run["id"]


def test_skill_run_cross_tenant_denied(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Owner project"},
        headers=auth_headers,
    ).json()["id"]
    created = client.post(
        f"/projects/{project_id}/skills/runs",
        headers=auth_headers,
        json={
            "skill_id": "marketsynth.copywriter",
            "input_type": "content_request",
            "input_ref": {},
            "explicit": True,
        },
    ).json()
    denied = client.get(
        f"/projects/{project_id}/skills/runs/{created['id']}",
        headers=other_auth_headers,
    )
    assert denied.status_code in (403, 404)


def test_avito_run_unconfigured_fails(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Avito"},
        headers=auth_headers,
    ).json()["id"]
    response = client.post(
        f"/projects/{project_id}/skills/runs",
        headers=auth_headers,
        json={
            "skill_id": "marketsynth.avito",
            "input_type": "avito_query",
            "input_ref": {"tool": "avito.analytics.read"},
            "explicit": True,
        },
    )
    assert response.status_code == 409


def test_content_director_stamps_copywriter_skill(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "CD Skill"},
        headers=auth_headers,
    ).json()["id"]
    request_id = client.post(
        f"/projects/{project_id}/content-director/requests",
        headers=auth_headers,
        json={
            "title": "Post",
            "objective": "Announce",
            "audience_description": "SMB",
            "key_message": "Ship",
            "requested_variants": 1,
            "channel": "telegram",
            "content_type": "telegram_post",
            "context_source": "manual",
        },
    ).json()["id"]
    gen = client.post(
        f"/projects/{project_id}/content-director/requests/{request_id}/generate",
        headers=auth_headers,
        json={},
    )
    assert gen.status_code == 200, gen.text
    workspace = client.get(
        f"/projects/{project_id}/content-director/workspace",
        headers=auth_headers,
        params={"request_id": request_id},
    ).json()
    assert workspace["applied_skill_id"] == "marketsynth.copywriter"
    assert workspace["applied_skill_version"] == "1.0.0"
    content_run_id = workspace["active_run"]["id"]
    # Persisted SkillRun lineage (idempotent replay)
    lineage = client.post(
        f"/projects/{project_id}/skills/runs",
        headers=auth_headers,
        json={
            "skill_id": "marketsynth.copywriter",
            "trigger": "telegram_post",
            "input_type": "content_request",
            "input_ref": {"content_request_id": request_id},
            "idempotency_key": f"cd-copywriter-{content_run_id}",
            "explicit": True,
        },
    )
    assert lineage.status_code == 200, lineage.text
    skill_run = lineage.json()
    assert skill_run["status"] == "succeeded"
    assert skill_run["skill_id"] == "marketsynth.copywriter"
    assert skill_run["skill_version"] == "1.0.0"
    assert skill_run["idempotency_key"] == f"cd-copywriter-{content_run_id}"
    asset_id = workspace["candidates"][0]["asset_id"]
    asset = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    meta = asset.get("metadata") or {}
    generation = meta.get("generation") or {}
    assert generation.get("skill_id") == "marketsynth.copywriter"
    assert generation.get("copywriter_package_verified") is True


def test_xmlriver_secret_binding_and_redaction(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.product_skills.catalog import XMLRIVER_WORDSTAT
    from app.product_skills.secret_binding import resolve_secret_alias
    from app.product_skills.tools_wordstat import wordstat_frequency

    monkeypatch.setenv("XMLRIVER_USER_ID", "19836")
    monkeypatch.setenv("XMLRIVER_API_KEY", "test-xmlriver-key-xyz")
    get_settings.cache_clear()
    bound = resolve_secret_alias("XML_RIVER_KEY")
    assert bound.configured is True
    assert bound.value == "test-xmlriver-key-xyz"

    def _fake_get_json(url: str, *, timeout: float = 65.0) -> dict:
        assert "test-xmlriver-key-xyz" in url  # provider auth style
        return {"totalValue": 42, "code": 0}

    monkeypatch.setattr(
        "app.product_skills.tools_wordstat._get_json",
        _fake_get_json,
    )
    result = wordstat_frequency(XMLRIVER_WORDSTAT, "кофейня")
    assert result["frequency"] == 42
    assert result["source"] == "XMLRiver"
    meta = result.get("request_metadata") or {}
    endpoint = str(meta.get("endpoint") or "")
    assert "test-xmlriver-key-xyz" not in endpoint
    assert "19836" not in endpoint
    get_settings.cache_clear()


def test_xmlriver_auth_and_rate_limit_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.core.exceptions import InvalidStateError
    from app.product_skills.catalog import XMLRIVER_WORDSTAT
    from app.product_skills.tools_wordstat import wordstat_frequency

    monkeypatch.setenv("XMLRIVER_USER_ID", "19836")
    monkeypatch.setenv("XMLRIVER_API_KEY", "k")
    get_settings.cache_clear()

    class _Resp:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload

        def read(self) -> bytes:
            return self._payload

        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def _with_code(code: int):
        def _open(req: object, timeout: float = 65.0) -> _Resp:
            return _Resp(json.dumps({"code": code}).encode("utf-8"))

        return _open

    monkeypatch.setattr("app.product_skills.tools_wordstat.urlopen", _with_code(401))
    with pytest.raises(InvalidStateError, match="xmlriver_auth_error"):
        wordstat_frequency(XMLRIVER_WORDSTAT, "q")

    monkeypatch.setattr("app.product_skills.tools_wordstat.urlopen", _with_code(429))
    with pytest.raises(InvalidStateError, match="xmlriver_rate_limited"):
        wordstat_frequency(XMLRIVER_WORDSTAT, "q")

    monkeypatch.setattr("app.product_skills.tools_wordstat.urlopen", _with_code(402))
    with pytest.raises(InvalidStateError, match="xmlriver_balance_error"):
        wordstat_frequency(XMLRIVER_WORDSTAT, "q")
    get_settings.cache_clear()


def test_importer_zip_absolute_windows_path_denied(tmp_path: Path) -> None:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Absolute-style member that shares a string prefix with extract root
        zf.writestr("C:/tmp/extract_evil/pwn.txt", "owned")
        zf.writestr(
            "manifest.json",
            json.dumps(
                {
                    "skill_id": "marketsynth.copywriter",
                    "name": "x",
                    "version": "1.0.0",
                    "description": "d",
                    "type": "instruction",
                }
            ),
        )
    zip_path = tmp_path / "evil.zip"
    zip_path.write_bytes(buf.getvalue())
    extract_to = tmp_path / "extract"
    report = ProductSkillImporter().import_zip(zip_path, extract_to)
    assert not report.ok
    assert any(f.code == "path_traversal" for f in report.findings)
    assert not (tmp_path / "extract_evil").exists()


def test_avito_credentials_alone_not_available(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Env Avito keys must not mark Available while live API is disabled."""
    monkeypatch.setenv("AVITO_CLIENT_ID", "cid")
    monkeypatch.setenv("AVITO_CLIENT_SECRET", "csecret")
    from app.core.config import get_settings
    from app.product_skills.tools_avito import (
        avito_configured,
        avito_credentials_present,
        avito_live_ready,
        avito_write_blocked,
    )
    from app.core.exceptions import InvalidStateError
    from app.product_skills.catalog import AVITO

    get_settings.cache_clear()
    assert avito_credentials_present() is True
    assert avito_live_ready() is False
    assert avito_configured() is False
    with pytest.raises(InvalidStateError, match="avito_write_disabled"):
        avito_write_blocked(AVITO, "avito.listing.write")

    skills = client.get("/skills", headers=auth_headers).json()
    avito = next(s for s in skills if s["skill_id"] == "marketsynth.avito")
    assert avito["configured"] is False
    assert avito["install_status"] == "installed_unconfigured"
    assert "live" in (avito.get("safe_error") or "").lower()
    assert "AVITO_CLIENT_SECRET" not in json.dumps(avito)

    project_id = client.post(
        "/projects",
        json={"name": "Avito creds"},
        headers=auth_headers,
    ).json()["id"]
    response = client.post(
        f"/projects/{project_id}/skills/runs",
        headers=auth_headers,
        json={
            "skill_id": "marketsynth.avito",
            "input_type": "avito_query",
            "input_ref": {"tool": "avito.listing.write"},
            "explicit": True,
        },
    )
    assert response.status_code == 409
    payload = json.dumps(response.json()).lower()
    assert "unconfigured" in payload
    get_settings.cache_clear()


def test_importer_zip_symlink_member_denied(tmp_path: Path) -> None:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("link_payload")
        info.external_attr = (0o120777 << 16)  # S_IFLNK
        zf.writestr(info, b"/tmp/evil")
        zf.writestr(
            "manifest.json",
            json.dumps(
                {
                    "skill_id": "marketsynth.copywriter",
                    "name": "x",
                    "version": "1.0.0",
                    "description": "d",
                    "type": "instruction",
                }
            ),
        )
    zip_path = tmp_path / "symlink.zip"
    zip_path.write_bytes(buf.getvalue())
    report = ProductSkillImporter().import_zip(zip_path, tmp_path / "out")
    assert not report.ok
    assert any(f.code == "symlink_forbidden" for f in report.findings)
