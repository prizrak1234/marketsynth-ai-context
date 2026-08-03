"""Built-in product skill manifests (curated from owner packages; no ZIP scripts)."""

from __future__ import annotations

from pathlib import Path

from app.schemas.contracts import (
    ProductSkillExternalAction,
    ProductSkillManifest,
    ProductSkillType,
)

_PACKAGES_ROOT = Path(__file__).resolve().parents[2] / "packages" / "product_skills"


def package_root_for(skill_id: str, version: str) -> Path:
    return _PACKAGES_ROOT / skill_id / version


COPYWRITER = ProductSkillManifest(
    skill_id="marketsynth.copywriter",
    name="Copywriter",
    version="1.0.0",
    description="Генерация и редактура маркетинговых текстов (инфостиль).",
    type=ProductSkillType.INSTRUCTION,
    triggers=["marketing_copy", "telegram_post", "content_edit", "copywriter"],
    accepted_input_types=["content_request"],
    output_types=["content_candidates"],
    instruction_entrypoint="SKILL.md",
    allowed_tools=[],
    allowed_network_hosts=[],
    required_secret_aliases=[],
    external_action=ProductSkillExternalAction.NONE,
    human_approval_required=False,
    provenance="owner_archive:Скилл-копирайтер.zip",
)

VISUAL_GENERATION = ProductSkillManifest(
    skill_id="marketsynth.visual_generation",
    name="Visual Generation",
    version="1.0.0",
    description="Генерация коммерческих изображений для Content Director (social_post_image).",
    type=ProductSkillType.INSTRUCTION,
    triggers=["social_post_image", "visual_generation", "image_variant"],
    accepted_input_types=["visual_request"],
    output_types=["image_candidates"],
    instruction_entrypoint="SKILL.md",
    allowed_tools=[],
    allowed_network_hosts=[],
    required_secret_aliases=[],
    external_action=ProductSkillExternalAction.NONE,
    human_approval_required=False,
    provenance="builtin:PRODUCT-CD-RUNTIME-02",
)

XMLRIVER_WORDSTAT = ProductSkillManifest(
    skill_id="marketsynth.xmlriver.wordstat",
    name="XMLRiver Wordstat",
    version="1.0.0",
    description="Частотность и расширение ключей через XMLRiver Wordstat.",
    type=ProductSkillType.INTEGRATION,
    triggers=["wordstat", "keyword_frequency", "semantic_expand", "xmlriver"],
    accepted_input_types=["keyword_query"],
    output_types=["wordstat_result"],
    instruction_entrypoint="SKILL.md",
    allowed_tools=["wordstat.frequency", "wordstat.expand", "wordstat.related"],
    allowed_network_hosts=["xmlriver.com"],
    required_secret_aliases=["XML_RIVER_USER_ID", "XML_RIVER_KEY"],
    external_action=ProductSkillExternalAction.READ,
    human_approval_required=False,
    provenance="owner_archive:Скилл_для_работы_с_вордстатом_xml_river.zip",
)

AVITO = ProductSkillManifest(
    skill_id="marketsynth.avito",
    name="Avito",
    version="1.0.0",
    description="Аналитика Avito API (read-only после конфигурации credentials).",
    type=ProductSkillType.INTEGRATION,
    triggers=["avito", "avito_analytics", "marketplace_avito"],
    accepted_input_types=["avito_query"],
    output_types=["avito_read_result"],
    instruction_entrypoint="SKILL.md",
    allowed_tools=["avito.analytics.read", "avito.account.read"],
    allowed_network_hosts=["api.avito.ru"],
    required_secret_aliases=["AVITO_CLIENT_ID", "AVITO_CLIENT_SECRET"],
    external_action=ProductSkillExternalAction.READ,
    human_approval_required=False,
    provenance="owner_archive:Скилл для Аvito.zip",
)

BUILTIN_PRODUCT_SKILLS: tuple[ProductSkillManifest, ...] = (
    COPYWRITER,
    VISUAL_GENERATION,
    XMLRIVER_WORDSTAT,
    AVITO,
)


def get_builtin_manifest(skill_id: str, version: str | None = None) -> ProductSkillManifest | None:
    for item in BUILTIN_PRODUCT_SKILLS:
        if item.skill_id != skill_id:
            continue
        if version is None or item.version == version:
            return item
    return None
