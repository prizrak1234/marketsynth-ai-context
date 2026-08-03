"""Generate KB-WPL-01.9 integrated program freeze manifest."""
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "packages" / "knowledge" / "kb_wpl_program" / "0.1.0"

FROZEN_HASHES = {
    "wpl_schema_bundle": "db34d8f1dbd82772d86fc921daa57d7007e748c004bf40b250023d1247823f25",
    "workflow_catalog": "5389c3a7fe77a8625e4cceab76da79ee33b816437a671d05a1dac969da1365fa",
    "pilot_bundle": "d2c3f64171bae91fe84708146ab05ff3fde3941f7645abcb006ca9de74a1a284",
    "core_bundle": "b715466982b73f86c11bb05310d72def00a540982baea6ab80882e06b0737fbf",
    "wpl_library_semantic": "1ddd0d033f6028bd5dcf5ee555186c6be0389a96459615b6221348783d9b1883",
    "capability_model_bundle": "e1e2bbeb025a3348944a5dab43e5661d31e2ac559e9e8de4989836c50831e42b",
    "capability_model_semantic": "20fbd1b9f2e4f4f6f044622e37734824a406c727adff8fb97541266a15bbd633",
    "discovery_bundle": "9a4f05af83350893fe32ce2bacc6d7c2e963d6440d4d2b47d002a2b1b85304c8",
}

SKILL_PACKAGE_HASHES = {
    "ms.skill.n8n_workflow_architecture": (
        "5af85271b4f8614ae14b002c3981be54f4128f7381258b3ec1e3729d29b75666"
    ),
    "ms.skill.n8n_workflow_debugging": (
        "e200b06ea6701f0667952b05e523077280e0238a9717787c8a096dc6dcd3d70f"
    ),
    "ms.skill.n8n_deployment_review": (
        "0ec6874bf449bd3e1006d15e9b8b5c004cc64dbad5a14d614dda94f14f6a938c"
    ),
    "ms.skill.knowledge_linking": (
        "95a3ff6d7f83f2e6437b4fb724c9aec13b814be2ae8fdfbc94a5e3872d32602a"
    ),
    "ms.skill.presentation_architecture": (
        "60ce698336fa21006ba203472fc6c3cef5661171ec2e45b641dcca743a42e95c"
    ),
}

COMPONENTS = [
    {
        "component_id": "kb-wpl-01.0",
        "name": "Archive Intake",
        "version": "0.1.0",
        "status": "frozen",
        "path": "docs/research/external-archives/",
    },
    {
        "component_id": "kb-wpl-01.1",
        "name": "Shared Knowledge Contracts",
        "version": "0.1.0",
        "status": "frozen",
        "path": "packages/knowledge/workflow_patterns/0.1.0/",
        "bundle_hash_key": "wpl_schema_bundle",
    },
    {
        "component_id": "kb-wpl-01.2",
        "name": "Workflow Catalog Quarantine",
        "version": "0.1.0",
        "status": "frozen",
        "path": "packages/knowledge/workflow_catalog/0.1.0/",
        "bundle_hash_key": "workflow_catalog",
    },
    {
        "component_id": "kb-wpl-01.2.1",
        "name": "Catalog Quality Repair",
        "version": "0.1.0",
        "status": "frozen",
        "path": "packages/knowledge/workflow_catalog/0.1.0/",
        "bundle_hash_key": "workflow_catalog",
    },
    {
        "component_id": "kb-wpl-01.3",
        "name": "Workflow Pattern Library",
        "version": "0.1.0-frozen",
        "status": "frozen_reviewed_library",
        "path": "packages/knowledge/workflow_patterns/0.1.0/",
        "bundle_hash_key": "wpl_library_semantic",
    },
    {
        "component_id": "kb-wpl-01.4",
        "name": "n8n Engineering Knowledge Skills",
        "version": "0.1.0",
        "status": "frozen_candidate",
        "path": "packages/skills/ms.skill.n8n_*",
    },
    {
        "component_id": "kb-wpl-01.5",
        "name": "Knowledge Linking Skill",
        "version": "0.1.0",
        "status": "frozen_candidate",
        "path": "packages/skills/ms.skill.knowledge_linking/",
        "skill_id": "ms.skill.knowledge_linking",
    },
    {
        "component_id": "kb-wpl-01.6",
        "name": "Presentation Architecture Skill",
        "version": "0.1.0",
        "status": "frozen_candidate",
        "path": "packages/skills/ms.skill.presentation_architecture/",
        "skill_id": "ms.skill.presentation_architecture",
    },
    {
        "component_id": "kb-wpl-01.7",
        "name": "Capability Model",
        "version": "0.1.0",
        "status": "frozen_candidate",
        "path": "packages/knowledge/capability_model/0.1.0/",
        "bundle_hash_key": "capability_model_bundle",
    },
    {
        "component_id": "kb-wpl-01.8",
        "name": "Knowledge Discovery Read Models",
        "version": "0.1.0",
        "status": "frozen_candidate",
        "path": "packages/knowledge/discovery/0.1.0/",
        "bundle_hash_key": "discovery_bundle",
    },
]

INVARIANTS = [
    {"id": "INV-001", "rule": "External Skills never execute directly.", "test_ids": ["test_inv_001"]},
    {"id": "INV-002", "rule": "Imported workflows never execute.", "test_ids": ["test_inv_002"]},
    {"id": "INV-003", "rule": "Imported scripts never execute.", "test_ids": ["test_inv_003"]},
    {"id": "INV-004", "rule": "Workflow JSON parsed only as data.", "test_ids": ["test_inv_004"]},
    {"id": "INV-005", "rule": "Secrets are redacted.", "test_ids": ["test_inv_005"]},
    {"id": "INV-006", "rule": "Credential IDs never become bindings.", "test_ids": ["test_inv_006"]},
    {"id": "INV-007", "rule": "Pattern maturity never exceeds reviewed.", "test_ids": ["test_inv_007"]},
    {"id": "INV-008", "rule": "Pattern does not grant permissions.", "test_ids": ["test_inv_008"]},
    {"id": "INV-009", "rule": "Capability mapping does not grant permissions.", "test_ids": ["test_inv_009"]},
    {"id": "INV-010", "rule": "Discovery does not activate Skills.", "test_ids": ["test_inv_010"]},
    {"id": "INV-011", "rule": "Discovery does not execute Patterns.", "test_ids": ["test_inv_011"]},
    {"id": "INV-012", "rule": "Discovery does not activate Connectors.", "test_ids": ["test_inv_012"]},
    {"id": "INV-013", "rule": "Discovery does not create credentials.", "test_ids": ["test_inv_013"]},
    {"id": "INV-014", "rule": "Discovery ranking is deterministic.", "test_ids": ["test_inv_014"]},
    {"id": "INV-015", "rule": "Discovery is tenant-safe.", "test_ids": ["test_inv_015"]},
    {"id": "INV-016", "rule": "Quarantined artifacts hidden in normal mode.", "test_ids": ["test_inv_016"]},
    {"id": "INV-017", "rule": "Rejected artifacts excluded by default.", "test_ids": ["test_inv_017"]},
    {"id": "INV-018", "rule": "Pattern cannot replace missing Skill.", "test_ids": ["test_inv_018"]},
    {"id": "INV-019", "rule": "Skill package cannot imply runtime availability.", "test_ids": ["test_inv_019"]},
    {"id": "INV-020", "rule": "Connector class cannot imply active Connector.", "test_ids": ["test_inv_020"]},
    {"id": "INV-021", "rule": "Tool class cannot imply allowlist permission.", "test_ids": ["test_inv_021"]},
    {"id": "INV-022", "rule": "Knowledge Linking never mutates files.", "test_ids": ["test_inv_022"]},
    {"id": "INV-023", "rule": "Knowledge Linking never crosses tenants.", "test_ids": ["test_inv_023"]},
    {"id": "INV-024", "rule": "Duplicate candidate never auto-merges.", "test_ids": ["test_inv_024"]},
    {"id": "INV-025", "rule": "Supersession never deletes history.", "test_ids": ["test_inv_025"]},
    {"id": "INV-026", "rule": "Contradiction never auto-selects truth.", "test_ids": ["test_inv_026"]},
    {"id": "INV-027", "rule": "Presentation Architecture never renders.", "test_ids": ["test_inv_027"]},
    {"id": "INV-028", "rule": "Presentation Architecture never publishes.", "test_ids": ["test_inv_028"]},
    {"id": "INV-029", "rule": "Presentation Architecture preserves claim evidence.", "test_ids": ["test_inv_029"]},
    {"id": "INV-030", "rule": "Engineering Skills never call n8n.", "test_ids": ["test_inv_030"]},
    {"id": "INV-031", "rule": "Engineering Skills never deploy.", "test_ids": ["test_inv_031"]},
    {"id": "INV-032", "rule": "Deployment Review never activates.", "test_ids": ["test_inv_032"]},
    {"id": "INV-033", "rule": "Debugging never live-patches.", "test_ids": ["test_inv_033"]},
    {"id": "INV-034", "rule": "Architecture Skill never emits authoritative workflow JSON.", "test_ids": ["test_inv_034"]},
    {"id": "INV-035", "rule": "Capability readiness is multidimensional.", "test_ids": ["test_inv_035"]},
    {"id": "INV-036", "rule": "Missing runtime remains visible.", "test_ids": ["test_inv_036"]},
    {"id": "INV-037", "rule": "Missing Connector remains visible.", "test_ids": ["test_inv_037"]},
    {"id": "INV-038", "rule": "Missing approval blocks publication readiness.", "test_ids": ["test_inv_038"]},
    {"id": "INV-039", "rule": "Spend remains deny-by-default.", "test_ids": ["test_inv_039"]},
    {"id": "INV-040", "rule": "Learning produces candidate only.", "test_ids": ["test_inv_040"]},
    {"id": "INV-041", "rule": "Canonical knowledge is never auto-mutated.", "test_ids": ["test_inv_041"]},
    {"id": "INV-042", "rule": "Tenant filtering occurs before ranking/linking.", "test_ids": ["test_inv_042"]},
    {"id": "INV-043", "rule": "Hidden artifacts do not leak through counts.", "test_ids": ["test_inv_043"]},
    {"id": "INV-044", "rule": "All hashes deterministic.", "test_ids": ["test_inv_044"]},
    {"id": "INV-045", "rule": "generated_at excluded from semantic hashes.", "test_ids": ["test_inv_045"]},
    {"id": "INV-046", "rule": "No absolute local paths in portable artifacts.", "test_ids": ["test_inv_046"]},
    {"id": "INV-047", "rule": "No raw workflow bodies in customer-facing metadata.", "test_ids": ["test_inv_047"]},
    {"id": "INV-048", "rule": "No raw credentials in reports.", "test_ids": ["test_inv_048"]},
    {"id": "INV-049", "rule": "No API/UI/DB introduced.", "test_ids": ["test_inv_049"]},
    {"id": "INV-050", "rule": "No MCP introduced.", "test_ids": ["test_inv_050"]},
    {"id": "INV-051", "rule": "No external network introduced.", "test_ids": ["test_inv_051"]},
    {"id": "INV-052", "rule": "CWF.1 unchanged.", "test_ids": ["test_inv_052"]},
    {"id": "INV-053", "rule": "CWF.1a unchanged.", "test_ids": ["test_inv_053"]},
    {"id": "INV-054", "rule": "Frozen marketing Skill hashes unchanged.", "test_ids": ["test_inv_054"]},
    {"id": "INV-055", "rule": "Audit readiness does not imply activation.", "test_ids": ["test_inv_055"]},
    {"id": "INV-056", "rule": "Frozen candidate does not imply production release.", "test_ids": ["test_inv_056"]},
    {"id": "INV-057", "rule": "Profession does not imply autonomous agent runtime.", "test_ids": ["test_inv_057"]},
    {"id": "INV-058", "rule": "ProfessionalTaskRoute remains advisory.", "test_ids": ["test_inv_058"]},
    {"id": "INV-059", "rule": "Safe actions exclude install/execute/deploy/publish/spend.", "test_ids": ["test_inv_059"]},
    {"id": "INV-060", "rule": "Program freeze does not authorize future runtime.", "test_ids": ["test_inv_060"]},
]

ACCEPTED_LIMITATIONS = [
    "No Knowledge Core persistence",
    "No live Registry API integration",
    "No API/UI for discovery or linking",
    "No vector search or LLM routing",
    "No runtime execution or Connector activation",
    "No external Skill search or Skill Generator",
    "No platform-adapted Pattern maturity beyond reviewed",
    "No n8n deployment gateway",
    "No presentation renderer",
    "No graph DB",
    "Legacy app/knowledge/linking/ remains (no new imports)",
    "Provider advice requires reverification",
    "Quarantine security scanner may contain false positives",
    "Discovery alias catalog is finite and manually governed",
]

DEFERRED_WORK = [
    {"id": "KB-WPL-02", "title": "Knowledge Core Persistence"},
    {"id": "KB-WPL-03", "title": "Internal Workflow Template Generator"},
    {"id": "KB-WPL-04", "title": "Controlled n8n Deployment Gateway"},
    {"id": "KB-WPL-05", "title": "Workflow Pattern Benchmarking"},
    {"id": "KB-WPL-06", "title": "Knowledge-Assisted Skill Draft Generation"},
    {"id": "KB-WPL-07", "title": "Learning and Outcome Feedback"},
    {"id": "discovery-api-ui", "title": "Discovery API/UI advisory panel"},
    {"id": "live-registry", "title": "Live Registry integration"},
    {"id": "vector-retrieval", "title": "Vector/semantic retrieval"},
    {"id": "provider-adapters", "title": "Provider runtime adapters"},
    {"id": "presentation-renderers", "title": "Presentation renderers"},
    {"id": "connector-runtime", "title": "Connector runtime"},
    {"id": "graph-persistence", "title": "Graph persistence"},
    {"id": "external-skill-discovery", "title": "External Skill discovery"},
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def semantic_hash(data: dict[str, Any]) -> str:
    subset = {k: v for k, v in data.items() if k != "generated_at"}
    payload = json.dumps(subset, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def main() -> None:
    component_index: list[dict[str, Any]] = []
    for comp in COMPONENTS:
        entry = dict(comp)
        key = comp.get("bundle_hash_key")
        if key:
            entry["bundle_hash"] = FROZEN_HASHES[key]
        skill_id = comp.get("skill_id")
        if skill_id:
            entry["skill_package_hash"] = SKILL_PACKAGE_HASHES[skill_id]
        component_index.append(entry)

    hash_registry = dict(FROZEN_HASHES)
    hash_registry["skill_packages"] = SKILL_PACKAGE_HASHES

    freeze_findings = {
        "blockers": [],
        "warnings": [
            "Legacy app/knowledge/linking/ directory remains; use app/knowledge/knowledge_linking/",
            "Discovery alias catalog is manually governed and finite",
            "Quarantine security scanner may produce false positives",
        ],
        "verdict": "READY",
        "audit_date": "2026-07-24",
    }

    write_json(BUNDLE / "component_index.json", {"version": "0.1.0", "components": component_index})
    write_json(BUNDLE / "invariant_map.json", {"version": "0.1.0", "invariants": INVARIANTS})
    write_json(
        BUNDLE / "accepted_limitations.json",
        {"version": "0.1.0", "limitations": ACCEPTED_LIMITATIONS},
    )
    write_json(BUNDLE / "deferred_work.json", {"version": "0.1.0", "items": DEFERRED_WORK})
    write_json(BUNDLE / "hash_registry.json", {"version": "0.1.0", "hashes": hash_registry})
    write_json(BUNDLE / "freeze_findings.json", freeze_findings)

    inv_hash = sha256_file(BUNDLE / "invariant_map.json")
    comp_hash = sha256_file(BUNDLE / "component_index.json")
    lim_hash = sha256_file(BUNDLE / "accepted_limitations.json")
    def_hash = sha256_file(BUNDLE / "deferred_work.json")

    integrated = {
        "program_id": "KB-WPL-01",
        "program_version": "0.1.0",
        "status": "frozen_read_only_knowledge_program",
        "owner_decision": "accepted_as_non_executable_foundation",
        "component_ids": [c["component_id"] for c in COMPONENTS],
        "component_versions": {c["component_id"]: c["version"] for c in COMPONENTS},
        "component_hashes": {
            c["component_id"]: c.get("bundle_hash") or c.get("skill_package_hash", "")
            for c in component_index
            if c.get("bundle_hash") or c.get("skill_package_hash")
        },
        "skill_package_hashes": SKILL_PACKAGE_HASHES,
        "knowledge_bundle_hashes": FROZEN_HASHES,
        "pattern_library_hash": FROZEN_HASHES["wpl_library_semantic"],
        "capability_model_hash": FROZEN_HASHES["capability_model_bundle"],
        "discovery_bundle_hash": FROZEN_HASHES["discovery_bundle"],
        "invariant_count": len(INVARIANTS),
        "blocker_count": len(freeze_findings["blockers"]),
        "warning_count": len(freeze_findings["warnings"]),
        "accepted_limitation_count": len(ACCEPTED_LIMITATIONS),
        "deferred_item_count": len(DEFERRED_WORK),
        "runtime_authorized": False,
        "production_eligible": False,
        "external_discovery": False,
        "vector_search": False,
        "llm_ranking": False,
        "persistence": False,
        "API_available": False,
        "UI_available": False,
        "connector_activation_available": False,
        "workflow_execution_available": False,
        "skill_execution_available": False,
        "invariant_map_hash": inv_hash,
        "component_index_hash": comp_hash,
        "accepted_limitations_hash": lim_hash,
        "deferred_work_hash": def_hash,
        "generated_at": "2026-07-24T02:00:00Z",
    }
    integrated["semantic_hash"] = semantic_hash(integrated)
    integrated["bundle_hash"] = sha256_bytes(
        json.dumps(
            {
                "semantic_hash": integrated["semantic_hash"],
                "hash_registry": hash_registry,
                "invariant_map_hash": inv_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )

    write_json(BUNDLE / "integrated_manifest.json", integrated)

    (BUNDLE / "README.md").write_text(
        "# KB-WPL-01 Integrated Program Freeze\n\n"
        "Read-only governed knowledge program spanning archive intake through Discovery.\n\n"
        f"- status: `{integrated['status']}`\n"
        f"- bundle_hash: `{integrated['bundle_hash']}`\n"
        f"- semantic_hash: `{integrated['semantic_hash']}`\n"
        f"- components: {len(COMPONENTS)}\n"
        f"- invariants: {len(INVARIANTS)}\n",
        encoding="utf-8",
    )
    print(f"bundle_hash={integrated['bundle_hash']}")
    print(f"semantic_hash={integrated['semantic_hash']}")


if __name__ == "__main__":
    main()
