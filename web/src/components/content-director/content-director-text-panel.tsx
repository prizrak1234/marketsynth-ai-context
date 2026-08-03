"use client";

import { useCallback, useEffect, useState } from "react";
import { CommercialAlert } from "@/components/commercial/commercial-alert";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialLoadingState } from "@/components/commercial/commercial-loading-state";
import {
  approveContentDirectorCandidate,
  createContentDirectorRequest,
  editContentDirectorCandidate,
  fetchContentDirectorWorkspace,
  generateContentDirectorVariants,
  patchContentDirectorRequest,
  rejectContentDirectorCandidate,
  type ContentDirectorCandidate,
  type ContentDirectorWorkspace,
} from "@/lib/api/endpoints/content-director";
import { useLocale } from "@/lib/i18n";

type Props = {
  projectId: string;
};

type FormState = {
  title: string;
  objective: string;
  audience_description: string;
  key_message: string;
  offer_value_proposition: string;
  tone: string;
  language: string;
  length: string;
  cta: string;
  must_include: string;
  must_avoid: string;
  requested_variants: number;
};

const emptyForm: FormState = {
  title: "",
  objective: "",
  audience_description: "",
  key_message: "",
  offer_value_proposition: "",
  tone: "professional",
  language: "ru",
  length: "medium",
  cta: "",
  must_include: "",
  must_avoid: "",
  requested_variants: 2,
};

export function ContentDirectorTextPanel({ projectId }: Props) {
  const { t } = useLocale();
  const [workspace, setWorkspace] = useState<ContentDirectorWorkspace | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [selected, setSelected] = useState<ContentDirectorCandidate | null>(null);
  const [editBody, setEditBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const reload = useCallback(async () => {
    const state = await fetchContentDirectorWorkspace(projectId);
    setWorkspace(state);
    if (state.request) {
      setForm({
        title: state.request.title,
        objective: state.request.objective,
        audience_description: state.request.audience_description,
        key_message: state.request.key_message,
        offer_value_proposition: state.request.offer_value_proposition,
        tone: state.request.tone,
        language: state.request.language,
        length: state.request.length,
        cta: state.request.cta,
        must_include: state.request.must_include,
        must_avoid: state.request.must_avoid,
        requested_variants: state.request.requested_variants,
      });
      const approved = state.candidates.find((c) => c.asset_id === state.approved_asset_id);
      const first = approved ?? state.candidates.find((c) => !c.rejected) ?? null;
      setSelected(first);
      setEditBody(first?.body ?? "");
    }
  }, [projectId]);

  useEffect(() => {
    void reload().catch(() => setError(t("contentDirector.loadError")));
  }, [reload, t]);

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (!form.title.trim()) next.title = t("contentDirector.validation.required");
    if (!form.objective.trim()) next.objective = t("contentDirector.validation.required");
    if (!form.audience_description.trim())
      next.audience_description = t("contentDirector.validation.required");
    if (!form.key_message.trim()) next.key_message = t("contentDirector.validation.required");
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  }

  async function saveRequest(): Promise<string | null> {
    if (!validate()) return null;
    setBusy(true);
    setError(null);
    try {
      const saved = workspace?.request
        ? await patchContentDirectorRequest(projectId, workspace.request.id, form)
        : await createContentDirectorRequest(projectId, form);
      await reload();
      return saved.id;
    } catch {
      setError(t("contentDirector.saveError"));
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function onGenerate() {
    if (!validate()) return;
    setBusy(true);
    setError(null);
    try {
      let requestId = workspace?.request?.id ?? null;
      if (!requestId) {
        const created = await createContentDirectorRequest(projectId, form);
        requestId = created.id;
      } else {
        await patchContentDirectorRequest(projectId, requestId, form);
      }
      await generateContentDirectorVariants(
        projectId,
        requestId,
        `cd-gen-${requestId}-${Date.now()}`,
      );
      await reload();
    } catch {
      setError(t("contentDirector.generateError"));
    } finally {
      setBusy(false);
    }
  }

  async function onApprove() {
    if (!workspace?.request || !selected) return;
    setBusy(true);
    setError(null);
    try {
      await approveContentDirectorCandidate(
        projectId,
        workspace.request.id,
        selected.asset_id,
      );
      await reload();
    } catch {
      setError(t("contentDirector.approveError"));
    } finally {
      setBusy(false);
    }
  }

  async function onSaveEdit() {
    if (!workspace?.request || !selected) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await editContentDirectorCandidate(
        projectId,
        workspace.request.id,
        selected.asset_id,
        { title: selected.title, body: editBody },
      );
      setSelected(updated);
      setEditBody(updated.body);
      await reload();
    } catch {
      setError(t("contentDirector.editError"));
    } finally {
      setBusy(false);
    }
  }

  async function onReject() {
    if (!workspace?.request || !selected) return;
    setBusy(true);
    try {
      await rejectContentDirectorCandidate(
        projectId,
        workspace.request.id,
        selected.asset_id,
      );
      await reload();
    } catch {
      setError(t("contentDirector.rejectError"));
    } finally {
      setBusy(false);
    }
  }

  const approved = Boolean(workspace?.approved_asset_id);
  const runFailed = workspace?.active_run?.status === "failed";

  return (
    <div className="space-y-6" data-testid="content-director-text-panel">
      {error ? (
        <CommercialAlert tone="danger" title={error} testId="content-director-error" />
      ) : null}
      {runFailed ? (
        <CommercialAlert
          tone="danger"
          title={workspace?.active_run?.error_message || t("contentDirector.generateError")}
        />
      ) : null}
      {busy ? <CommercialLoadingState label={t("contentDirector.working")} /> : null}

      <CommercialCard>
        <h2 className="mb-4 text-lg font-semibold">{t("contentDirector.requestHeading")}</h2>
        <p className="mb-4 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          {t("contentDirector.manualContextNote")}
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          {(
            [
              ["title", t("contentDirector.fields.title")],
              ["objective", t("contentDirector.fields.objective")],
              ["audience_description", t("contentDirector.fields.audience")],
              ["key_message", t("contentDirector.fields.keyMessage")],
              ["offer_value_proposition", t("contentDirector.fields.offer")],
              ["tone", t("contentDirector.fields.tone")],
              ["language", t("contentDirector.fields.language")],
              ["length", t("contentDirector.fields.length")],
              ["cta", t("contentDirector.fields.cta")],
              ["must_include", t("contentDirector.fields.mustInclude")],
              ["must_avoid", t("contentDirector.fields.mustAvoid")],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="flex flex-col gap-1 text-sm">
              <span>{label}</span>
              <input
                className="rounded-md border px-3 py-2"
                style={{
                  borderColor: "var(--ms-border-default)",
                  background: "var(--ms-bg-surface)",
                }}
                value={form[key]}
                disabled={approved || busy}
                data-testid={`content-director-field-${key}`}
                onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))}
              />
              {fieldErrors[key] ? (
                <span className="text-xs" style={{ color: "var(--ms-danger)" }}>
                  {fieldErrors[key]}
                </span>
              ) : null}
            </label>
          ))}
          <label className="flex flex-col gap-1 text-sm">
            <span>{t("contentDirector.fields.variants")}</span>
            <select
              className="rounded-md border px-3 py-2"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              value={form.requested_variants}
              disabled={approved || busy}
              data-testid="content-director-field-variants"
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  requested_variants: Number(e.target.value),
                }))
              }
            >
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
            </select>
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <CommercialButton
            onClick={() => void saveRequest()}
            disabled={approved || busy}
            variant="secondary"
            testId="content-director-save"
          >
            {t("contentDirector.actions.save")}
          </CommercialButton>
          <CommercialButton
            onClick={() => void onGenerate()}
            disabled={approved || busy}
            testId="content-director-generate"
          >
            {t("contentDirector.actions.generate")}
          </CommercialButton>
        </div>
        <p className="mt-2 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
          {t("contentDirector.channelFormat")}
        </p>
      </CommercialCard>

      {workspace?.applied_skill_id ? (
        <p
          className="text-sm"
          style={{ color: "var(--ms-text-secondary)" }}
          data-testid="content-director-applied-skill"
        >
          {t("contentDirector.appliedSkill", {
            name: "Copywriter",
            version: workspace.applied_skill_version || "1.0.0",
          })}
        </p>
      ) : null}

      {workspace?.candidates?.length ? (
        <CommercialCard>
          <h2 className="mb-4 text-lg font-semibold">
            {t("contentDirector.candidatesHeading")}
          </h2>
          <div className="grid gap-3 md:grid-cols-3" data-testid="content-director-candidates">
            {workspace.candidates.map((cand) => (
              <button
                key={cand.asset_id}
                type="button"
                className="rounded-md border p-3 text-left"
                style={{
                  borderColor:
                    selected?.asset_id === cand.asset_id
                      ? "var(--ms-brand-primary)"
                      : "var(--ms-border-default)",
                  opacity: cand.rejected ? 0.5 : 1,
                }}
                data-testid={`content-director-candidate-${cand.candidate_index}`}
                onClick={() => {
                  setSelected(cand);
                  setEditBody(cand.body);
                }}
              >
                <div className="text-sm font-semibold">{cand.title}</div>
                <div className="mt-2 line-clamp-4 text-xs">{cand.body}</div>
                <div className="mt-2 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                  {cand.status}
                  {cand.rejected ? ` · ${t("contentDirector.rejected")}` : ""}
                </div>
              </button>
            ))}
          </div>
        </CommercialCard>
      ) : null}

      {selected ? (
        <CommercialCard>
          <h2 className="mb-4 text-lg font-semibold">{t("contentDirector.editorHeading")}</h2>
          <textarea
            className="min-h-40 w-full rounded-md border px-3 py-2 text-sm"
            style={{
              borderColor: "var(--ms-border-default)",
              background: "var(--ms-bg-surface)",
            }}
            value={editBody}
            disabled={approved || selected.rejected || busy}
            data-testid="content-director-editor"
            onChange={(e) => setEditBody(e.target.value)}
          />
          <div className="mt-2 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
            {t("contentDirector.versionLabel")}: {selected.current_version_number}
            {selected.approved_version_number
              ? ` · ${t("contentDirector.approvedVersion")}: ${selected.approved_version_number}`
              : ""}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <CommercialButton
              variant="secondary"
              disabled={approved || selected.rejected || busy}
              onClick={() => void onSaveEdit()}
              testId="content-director-save-edit"
            >
              {t("contentDirector.actions.saveEdit")}
            </CommercialButton>
            <CommercialButton
              variant="secondary"
              disabled={approved || selected.rejected || busy}
              onClick={() => void onReject()}
              testId="content-director-reject"
            >
              {t("contentDirector.actions.reject")}
            </CommercialButton>
            <CommercialButton
              disabled={approved || selected.rejected || busy}
              onClick={() => void onApprove()}
              testId="content-director-approve"
            >
              {t("contentDirector.actions.approve")}
            </CommercialButton>
          </div>
        </CommercialCard>
      ) : null}

      {approved ? (
        <CommercialAlert
          tone="success"
          title={t("contentDirector.approvedBanner")}
          testId="content-director-approved"
        />
      ) : null}
    </div>
  );
}
