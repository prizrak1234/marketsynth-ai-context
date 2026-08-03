"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { WorkspaceSectionShell } from "@/components/workspace/section-shell";
import {
  approveKnowledgeItem,
  getKnowledgePolicy,
  ingestContentPack,
  listKnowledgeInventory,
  listStoredKnowledge,
  rejectKnowledgeItem,
  type KnowledgeItemDto,
} from "@/lib/api/endpoints/knowledge-foundation";
import {
  archiveKgVersion,
  deprecateKgVersion,
  getKgFreshness,
  getKgObject,
  listKgBenchmarks,
  listKgCandidates,
  listKgObjects,
  publishKgVersion,
  validateKgVersion,
  type KgObjectDetail,
  type KgObjectSummary,
} from "@/lib/api/endpoints/knowledge-governance";
import { useLocale } from "@/lib/i18n";

const TYPE_FILTERS = ["", "constitutional_policy", "domain_methodology", "output_template", "example", "obsolete", "forbidden"];
const STATUS_FILTERS = ["", "candidate", "under_review", "approved", "rejected", "superseded", "archived"];

type GovTab =
  | "candidates"
  | "review"
  | "published"
  | "freshness"
  | "expired"
  | "archive"
  | "benchmark";

export function KnowledgeManagementView() {
  const { t } = useLocale();
  const [items, setItems] = useState<KnowledgeItemDto[]>([]);
  const [stored, setStored] = useState<
    Array<{ id: string; code: string; version: string; status: string; locale: string }>
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [knowledgeType, setKnowledgeType] = useState("");
  const [policyLine, setPolicyLine] = useState("");

  const [govTab, setGovTab] = useState<GovTab>("candidates");
  const [govRows, setGovRows] = useState<KgObjectSummary[]>([]);
  const [freshness, setFreshness] = useState<
    Array<{ version_id: string; freshness: string; expired: boolean; owner_review_task: boolean; safe_message: string }>
  >([]);
  const [benchmarks, setBenchmarks] = useState<
    Array<{ id: string; name: string; version: string; domain: string; case_count: number }>
  >([]);
  const [selected, setSelected] = useState<KgObjectDetail | null>(null);
  const [govError, setGovError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [inventory, policy, durable] = await Promise.all([
        listKnowledgeInventory({
          status: status || undefined,
          knowledge_type: knowledgeType || undefined,
        }),
        getKnowledgePolicy(),
        listStoredKnowledge(),
      ]);
      setItems(inventory);
      setStored(
        durable.map((row) => ({
          id: row.id,
          code: row.code,
          version: row.version,
          status: row.status,
          locale: row.locale,
        })),
      );
      setPolicyLine(
        [
          `storage=${policy.storage_option}`,
          `embeddings=${policy.embeddings_enabled}`,
          `bulk=${policy.bulk_repo_ingestion_enabled}`,
          `exec=${policy.execution_enabled}`,
          `durable=${durable.length}`,
        ].join(" · "),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "load_failed");
    } finally {
      setLoading(false);
    }
  }, [status, knowledgeType]);

  const loadGov = useCallback(async () => {
    setGovError(null);
    try {
      if (govTab === "candidates") {
        const res = await listKgCandidates();
        setGovRows(res.candidates);
      } else if (govTab === "review") {
        const res = await listKgObjects("validated");
        setGovRows(res.objects);
      } else if (govTab === "published") {
        const res = await listKgObjects("published");
        setGovRows(res.objects);
      } else if (govTab === "archive") {
        const res = await listKgObjects("archived");
        setGovRows(res.objects);
      } else if (govTab === "expired" || govTab === "freshness") {
        const res = await getKgFreshness();
        setFreshness(res.checks);
        setGovRows([]);
      } else if (govTab === "benchmark") {
        const res = await listKgBenchmarks();
        setBenchmarks(res.datasets);
        setGovRows([]);
      }
    } catch (err) {
      setGovError(err instanceof Error ? err.message : "gov_load_failed");
    }
  }, [govTab]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadGov();
  }, [loadGov]);

  const whereUsed = useMemo(() => {
    return items.map((item) => ({
      id: item.id,
      roles: item.specialist_roles.join(", ") || "—",
      scopes: `${item.tenant_scope} · ${item.domain}`,
    }));
  }, [items]);

  async function onApprove(id: string) {
    await approveKnowledgeItem(id, "owner review");
    await load();
  }

  async function onReject(id: string) {
    await rejectKnowledgeItem(id, "owner review");
    await load();
  }

  async function openObject(id: string) {
    const detail = await getKgObject(id);
    setSelected(detail);
  }

  async function actOnCurrent(action: "validate" | "publish" | "deprecate" | "archive") {
    if (!selected?.current_version_id) return;
    const vid = selected.current_version_id;
    if (action === "validate") await validateKgVersion(vid);
    if (action === "publish") await publishKgVersion(vid);
    if (action === "deprecate") await deprecateKgVersion(vid);
    if (action === "archive") await archiveKgVersion(vid);
    await openObject(selected.id);
    await loadGov();
  }

  const govTabs: Array<{ id: GovTab; label: string }> = [
    { id: "candidates", label: "Кандидаты" },
    { id: "review", label: "На проверке" },
    { id: "published", label: "Опубликованные" },
    { id: "freshness", label: "Требуют актуализации" },
    { id: "expired", label: "Устаревшие" },
    { id: "archive", label: "Архив" },
    { id: "benchmark", label: "Benchmark" },
  ];

  return (
    <WorkspaceSectionShell
      title={t("knowledgeMgmt.title")}
      description={t("knowledgeMgmt.description")}
      testId="workspace-knowledge-mgmt"
    >
      <div className="space-y-6 text-sm">
        <section data-testid="knowledge-governance-panel" className="space-y-3">
          <h2 className="text-base font-medium">Knowledge Governance (KG.2)</h2>
          <div className="flex flex-wrap gap-2">
            {govTabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                className="rounded border px-2 py-1 text-xs"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: govTab === tab.id ? "var(--ms-bg-elevated, transparent)" : "transparent",
                }}
                data-testid={`kg-tab-${tab.id}`}
                onClick={() => setGovTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          {govError ? (
            <p style={{ color: "var(--ms-danger, #b42318)" }}>{govError}</p>
          ) : null}

          {govTab === "benchmark" ? (
            <ul className="space-y-1" data-testid="kg-benchmark-list">
              {benchmarks.map((b) => (
                <li key={b.id}>
                  {b.name} v{b.version} · {b.domain} · cases={b.case_count}
                </li>
              ))}
            </ul>
          ) : null}

          {(govTab === "freshness" || govTab === "expired") && (
            <ul className="space-y-1" data-testid="kg-freshness-list">
              {freshness
                .filter((c) => (govTab === "expired" ? c.expired : c.owner_review_task || c.freshness === "due_for_review"))
                .map((c) => (
                  <li key={c.version_id}>
                    {c.version_id.slice(0, 8)}… · {c.freshness}
                    {c.owner_review_task ? " · задача владельцу" : ""} — {c.safe_message}
                  </li>
                ))}
            </ul>
          )}

          {["candidates", "review", "published", "archive"].includes(govTab) ? (
            <div className="overflow-x-auto" data-testid="kg-objects-table">
              <table className="w-full min-w-[640px] border-collapse text-left">
                <thead>
                  <tr style={{ color: "var(--ms-text-muted)" }}>
                    <th className="border-b px-2 py-2 font-medium">Код</th>
                    <th className="border-b px-2 py-2 font-medium">Название</th>
                    <th className="border-b px-2 py-2 font-medium">Домен</th>
                    <th className="border-b px-2 py-2 font-medium">Статус</th>
                    <th className="border-b px-2 py-2 font-medium">Действие</th>
                  </tr>
                </thead>
                <tbody>
                  {govRows.map((row) => (
                    <tr key={row.id}>
                      <td className="border-b px-2 py-2">{row.code}</td>
                      <td className="border-b px-2 py-2">{row.title}</td>
                      <td className="border-b px-2 py-2">{row.domain}</td>
                      <td className="border-b px-2 py-2">{row.status}</td>
                      <td className="border-b px-2 py-2">
                        <button
                          type="button"
                          className="rounded border px-2 py-1 text-xs"
                          style={{ borderColor: "var(--ms-border-default)" }}
                          onClick={() => void openObject(row.id)}
                        >
                          Открыть
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {selected ? (
            <div
              className="space-y-2 rounded border p-3"
              style={{ borderColor: "var(--ms-border-default)" }}
              data-testid="kg-object-card"
            >
              <div className="font-medium">
                {selected.title} · {selected.code} · {selected.status}
              </div>
              <div style={{ color: "var(--ms-text-muted)" }}>
                domain={selected.domain} · version=
                {selected.versions.find((v) => v.id === selected.current_version_id)?.version || "—"}
              </div>
              {(selected.versions[0] && (
                <div style={{ color: "var(--ms-text-muted)" }}>
                  source={selected.versions[0].source_uri} · freshness=
                  {selected.versions[0].freshness} · next_review=
                  {selected.versions[0].next_review_at || "—"}
                </div>
              )) || null}
              <div>
                <div className="mb-1 font-medium">Semantic chunks</div>
                <ul className="space-y-1">
                  {selected.semantic_chunks.map((c) => (
                    <li key={c.id}>
                      {c.title}: {c.rule.slice(0, 160)}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="rounded border px-2 py-1 text-xs" style={{ borderColor: "var(--ms-border-default)" }} onClick={() => void actOnCurrent("validate")}>
                  Подтвердить
                </button>
                <button type="button" className="rounded border px-2 py-1 text-xs" style={{ borderColor: "var(--ms-border-default)" }} onClick={() => void actOnCurrent("publish")}>
                  Опубликовать
                </button>
                <button type="button" className="rounded border px-2 py-1 text-xs" style={{ borderColor: "var(--ms-border-default)" }} onClick={() => void actOnCurrent("deprecate")}>
                  Пометить устаревшим
                </button>
                <button type="button" className="rounded border px-2 py-1 text-xs" style={{ borderColor: "var(--ms-border-default)" }} onClick={() => void actOnCurrent("archive")}>
                  Архивировать
                </button>
              </div>
            </div>
          ) : null}
        </section>

        <p style={{ color: "var(--ms-text-muted)" }} data-testid="knowledge-policy-line">
          {policyLine || t("common.loading")}
        </p>
        <button
          type="button"
          className="rounded border px-3 py-1.5 text-sm"
          style={{ borderColor: "var(--ms-border-default)" }}
          data-testid="knowledge-ingest-pack"
          onClick={() => {
            void (async () => {
              await ingestContentPack();
              await load();
            })();
          }}
        >
          {t("knowledgeMgmt.ingestPack")}
        </button>
        <div className="flex flex-wrap gap-3">
          <label>
            {t("common.status")}
            <select
              className="ml-2 rounded border px-2 py-1"
              style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-surface)" }}
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              data-testid="knowledge-filter-status"
            >
              {STATUS_FILTERS.map((s) => (
                <option key={s || "all"} value={s}>
                  {s || t("common.all")}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("common.type")}
            <select
              className="ml-2 rounded border px-2 py-1"
              style={{ borderColor: "var(--ms-border-default)", background: "var(--ms-bg-surface)" }}
              value={knowledgeType}
              onChange={(e) => setKnowledgeType(e.target.value)}
              data-testid="knowledge-filter-type"
            >
              {TYPE_FILTERS.map((s) => (
                <option key={s || "all"} value={s}>
                  {s || t("common.all")}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error ? (
          <p style={{ color: "var(--ms-danger, #b42318)" }}>{error}</p>
        ) : null}
        {loading ? <p style={{ color: "var(--ms-text-muted)" }}>{t("common.loading")}</p> : null}

        <div className="overflow-x-auto" data-testid="knowledge-inventory-table">
          <table className="w-full min-w-[720px] border-collapse text-left">
            <thead>
              <tr style={{ color: "var(--ms-text-muted)" }}>
                <th className="border-b px-2 py-2 font-medium">{t("knowledgeMgmt.colTitle")}</th>
                <th className="border-b px-2 py-2 font-medium">{t("common.type")}</th>
                <th className="border-b px-2 py-2 font-medium">{t("common.status")}</th>
                <th className="border-b px-2 py-2 font-medium">{t("common.version")}</th>
                <th className="border-b px-2 py-2 font-medium">{t("knowledgeMgmt.colSource")}</th>
                <th className="border-b px-2 py-2 font-medium">{t("knowledgeMgmt.colActions")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} data-testid={`knowledge-row-${item.id}`}>
                  <td className="border-b px-2 py-2">
                    <div>{item.title}</div>
                    <div className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      {item.id} · {item.locale} · {item.authority}
                    </div>
                  </td>
                  <td className="border-b px-2 py-2">{item.knowledge_type}</td>
                  <td className="border-b px-2 py-2">{item.status}</td>
                  <td className="border-b px-2 py-2">{item.version}</td>
                  <td className="border-b px-2 py-2">
                    <div className="max-w-[220px] truncate" title={item.source_uri}>
                      {item.source_uri}
                    </div>
                    <div className="text-xs" style={{ color: "var(--ms-text-muted)" }}>
                      {item.source_hash || "—"}
                    </div>
                  </td>
                  <td className="border-b px-2 py-2">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="rounded border px-2 py-1 text-xs"
                        style={{ borderColor: "var(--ms-border-default)" }}
                        onClick={() => void onApprove(item.id)}
                        data-testid={`knowledge-approve-${item.id}`}
                      >
                        {t("knowledgeMgmt.approve")}
                      </button>
                      <button
                        type="button"
                        className="rounded border px-2 py-1 text-xs"
                        style={{ borderColor: "var(--ms-border-default)" }}
                        onClick={() => void onReject(item.id)}
                        data-testid={`knowledge-reject-${item.id}`}
                      >
                        {t("knowledgeMgmt.reject")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <section data-testid="knowledge-durable-pack">
          <h2 className="mb-2 text-base font-medium">{t("knowledgeMgmt.durable")}</h2>
          <ul className="space-y-1" style={{ color: "var(--ms-text-secondary)" }}>
            {stored.map((row) => (
              <li key={`${row.code}:${row.version}`}>
                {row.code} v{row.version} · {row.status} · {row.locale}
              </li>
            ))}
          </ul>
        </section>

        <section data-testid="knowledge-where-used">
          <h2 className="mb-2 text-base font-medium">{t("knowledgeMgmt.whereUsed")}</h2>
          <ul className="space-y-1" style={{ color: "var(--ms-text-secondary)" }}>
            {whereUsed.slice(0, 12).map((row) => (
              <li key={row.id}>
                {row.id}: {row.roles} · {row.scopes}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </WorkspaceSectionShell>
  );
}
