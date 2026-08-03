"use client";

import { useCallback, useEffect, useState } from "react";
import { CommercialAlert } from "@/components/commercial/commercial-alert";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialLoadingState } from "@/components/commercial/commercial-loading-state";
import {
  approveVisualDirectorCandidate,
  createVisualDirectorRequest,
  fetchVisualCandidateBlob,
  fetchVisualDirectorWorkspace,
  generateVisualDirectorVariants,
  patchVisualDirectorRequest,
  rejectVisualDirectorCandidate,
  type VisualDirectorCandidate,
  type VisualDirectorWorkspace,
} from "@/lib/api/endpoints/visual-director";
import { useLocale } from "@/lib/i18n";

type Props = {
  projectId: string;
};

type FormState = {
  title: string;
  objective: string;
  scene_description: string;
  subject: string;
  style: string;
  audience: string;
  mood: string;
  aspect_ratio: string;
  text_overlay: string;
  must_include: string;
  must_avoid: string;
  language: string;
  requested_variants: number;
};

const emptyForm: FormState = {
  title: "",
  objective: "",
  scene_description: "",
  subject: "",
  style: "clean commercial",
  audience: "",
  mood: "confident",
  aspect_ratio: "1:1",
  text_overlay: "",
  must_include: "",
  must_avoid: "",
  language: "ru",
  requested_variants: 2,
};

function CandidateThumb({
  projectId,
  assetId,
  alt,
  testId,
}: {
  projectId: string;
  assetId: string;
  alt: string;
  testId: string;
}) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    void (async () => {
      try {
        const blob = await fetchVisualCandidateBlob(projectId, assetId);
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      } catch {
        if (!cancelled) setSrc(null);
      }
    })();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [projectId, assetId]);
  if (!src) {
    return (
      <div
        className="h-36 w-full animate-pulse rounded-md"
        style={{ background: "var(--ms-bg-surface)" }}
      />
    );
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} className="h-36 w-full rounded-md object-cover" data-testid={testId} />;
}

export function VisualDirectorPanel({ projectId }: Props) {
  const { t } = useLocale();
  const [workspace, setWorkspace] = useState<VisualDirectorWorkspace | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [selected, setSelected] = useState<VisualDirectorCandidate | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [confirmOverlay, setConfirmOverlay] = useState(false);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [genLock, setGenLock] = useState(false);

  const reload = useCallback(async () => {
    const state = await fetchVisualDirectorWorkspace(projectId);
    setWorkspace(state);
    if (state.request) {
      setForm({
        title: state.request.title,
        objective: state.request.objective,
        scene_description: state.request.scene_description,
        subject: state.request.subject,
        style: state.request.style,
        audience: state.request.audience,
        mood: state.request.mood,
        aspect_ratio: state.request.aspect_ratio,
        text_overlay: state.request.text_overlay,
        must_include: state.request.must_include,
        must_avoid: state.request.must_avoid,
        language: state.request.language,
        requested_variants: state.request.requested_variants,
      });
      const approved = state.candidates.find((c) => c.asset_id === state.approved_asset_id);
      const first = approved ?? state.candidates.find((c) => !c.rejected) ?? null;
      setSelected(first);
    }
  }, [projectId]);

  useEffect(() => {
    void reload().catch(() => setError(t("visualDirector.loadError")));
  }, [reload, t]);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    if (!selected) {
      setPreviewSrc(null);
      return;
    }
    void (async () => {
      try {
        const blob = await fetchVisualCandidateBlob(projectId, selected.asset_id);
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setPreviewSrc(objectUrl);
      } catch {
        if (!cancelled) setPreviewSrc(null);
      }
    })();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [projectId, selected]);

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (!form.title.trim()) next.title = t("visualDirector.validation.required");
    if (!form.objective.trim()) next.objective = t("visualDirector.validation.required");
    if (!form.scene_description.trim())
      next.scene_description = t("visualDirector.validation.required");
    if (!form.subject.trim()) next.subject = t("visualDirector.validation.required");
    if (!form.audience.trim()) next.audience = t("visualDirector.validation.required");
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  }

  async function saveRequest(): Promise<string | null> {
    if (!validate()) return null;
    setBusy(true);
    setError(null);
    try {
      const saved = workspace?.request
        ? await patchVisualDirectorRequest(projectId, workspace.request.id, form)
        : await createVisualDirectorRequest(projectId, form);
      await reload();
      return saved.id;
    } catch {
      setError(t("visualDirector.saveError"));
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function onGenerate() {
    if (!validate() || genLock) return;
    setGenLock(true);
    setBusy(true);
    setError(null);
    try {
      let requestId = workspace?.request?.id ?? null;
      if (!requestId) {
        const created = await createVisualDirectorRequest(projectId, form);
        requestId = created.id;
      } else if (!workspace?.approved_asset_id) {
        await patchVisualDirectorRequest(projectId, requestId, form);
      }
      await generateVisualDirectorVariants(
        projectId,
        requestId,
        `vd-gen-${requestId}`,
      );
      await reload();
    } catch {
      setError(t("visualDirector.generateError"));
    } finally {
      setBusy(false);
      setGenLock(false);
    }
  }

  async function onApprove() {
    if (!workspace?.request || !selected) return;
    setBusy(true);
    setError(null);
    try {
      await approveVisualDirectorCandidate(
        projectId,
        workspace.request.id,
        selected.asset_id,
        Boolean(form.text_overlay.trim()) ? confirmOverlay : false,
      );
      await reload();
    } catch {
      setError(t("visualDirector.approveError"));
    } finally {
      setBusy(false);
    }
  }

  async function onReject() {
    if (!workspace?.request || !selected) return;
    setBusy(true);
    try {
      await rejectVisualDirectorCandidate(
        projectId,
        workspace.request.id,
        selected.asset_id,
      );
      await reload();
    } catch {
      setError(t("visualDirector.rejectError"));
    } finally {
      setBusy(false);
    }
  }

  async function onDownload() {
    if (!selected || !previewSrc) return;
    const a = document.createElement("a");
    a.href = previewSrc;
    a.download = `${selected.title || "image"}.png`;
    a.click();
  }

  const approved = Boolean(workspace?.approved_asset_id);
  const runFailed = workspace?.active_run?.status === "failed";
  const waiting = workspace?.next_action === "wait_generation";

  return (
    <div className="space-y-6" data-testid="visual-director-panel">
      {error ? (
        <CommercialAlert tone="danger" title={error} testId="visual-director-error" />
      ) : null}
      {runFailed ? (
        <CommercialAlert
          tone="danger"
          title={workspace?.active_run?.error_message || t("visualDirector.generateError")}
        />
      ) : null}
      {busy || waiting ? (
        <CommercialLoadingState label={t("visualDirector.working")} />
      ) : null}

      <CommercialCard>
        <h2 className="mb-4 text-lg font-semibold">{t("visualDirector.requestHeading")}</h2>
        <p className="mb-4 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          {t("visualDirector.manualContextNote")}
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          {(
            [
              ["title", t("visualDirector.fields.title")],
              ["objective", t("visualDirector.fields.objective")],
              ["scene_description", t("visualDirector.fields.scene")],
              ["subject", t("visualDirector.fields.subject")],
              ["style", t("visualDirector.fields.style")],
              ["audience", t("visualDirector.fields.audience")],
              ["mood", t("visualDirector.fields.mood")],
              ["text_overlay", t("visualDirector.fields.textOverlay")],
              ["must_include", t("visualDirector.fields.mustInclude")],
              ["must_avoid", t("visualDirector.fields.mustAvoid")],
              ["language", t("visualDirector.fields.language")],
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
                data-testid={`visual-director-field-${key}`}
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
            <span>{t("visualDirector.fields.aspect")}</span>
            <select
              className="rounded-md border px-3 py-2"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              value={form.aspect_ratio}
              disabled={approved || busy}
              data-testid="visual-director-field-aspect_ratio"
              onChange={(e) =>
                setForm((prev) => ({ ...prev, aspect_ratio: e.target.value }))
              }
            >
              <option value="1:1">1:1</option>
              <option value="16:9">16:9</option>
              <option value="9:16">9:16</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span>{t("visualDirector.fields.variants")}</span>
            <select
              className="rounded-md border px-3 py-2"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-surface)",
              }}
              value={form.requested_variants}
              disabled={approved || busy}
              data-testid="visual-director-field-variants"
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
              <option value={4}>4</option>
            </select>
          </label>
        </div>
        {workspace?.related_text_preview ? (
          <p className="mt-3 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {t("visualDirector.relatedText")}: {workspace.related_text_preview}
          </p>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-2">
          <CommercialButton
            onClick={() => void saveRequest()}
            disabled={approved || busy}
            variant="secondary"
            testId="visual-director-save"
          >
            {t("visualDirector.actions.save")}
          </CommercialButton>
          <CommercialButton
            onClick={() => void onGenerate()}
            disabled={approved || busy || genLock}
            testId="visual-director-generate"
          >
            {t("visualDirector.actions.generate")}
          </CommercialButton>
        </div>
        <p className="mt-2 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
          {t("visualDirector.formatNote")}
        </p>
      </CommercialCard>

      {workspace?.applied_skill_id ? (
        <p
          className="text-sm"
          style={{ color: "var(--ms-text-secondary)" }}
          data-testid="visual-director-applied-skill"
        >
          {t("visualDirector.appliedSkill", {
            name: "Visual Generation",
            version: workspace.applied_skill_version || "1.0.0",
          })}
        </p>
      ) : null}

      {workspace?.candidates?.length ? (
        <CommercialCard>
          <h2 className="mb-4 text-lg font-semibold">
            {t("visualDirector.candidatesHeading")}
          </h2>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4" data-testid="visual-director-candidates">
            {workspace.candidates.map((cand) => (
              <button
                key={cand.asset_id}
                type="button"
                className="rounded-md border p-2 text-left"
                style={{
                  borderColor:
                    selected?.asset_id === cand.asset_id
                      ? "var(--ms-brand-primary)"
                      : "var(--ms-border-default)",
                  opacity: cand.rejected ? 0.5 : 1,
                }}
                data-testid={`visual-director-candidate-${cand.candidate_index}`}
                onClick={() => setSelected(cand)}
              >
                <CandidateThumb
                  projectId={projectId}
                  assetId={cand.asset_id}
                  alt={cand.title}
                  testId={`visual-director-thumb-${cand.candidate_index}`}
                />
                <div className="mt-2 text-sm font-semibold">{cand.title}</div>
                <div className="mt-1 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
                  {cand.status}
                  {cand.rejected ? ` · ${t("visualDirector.rejected")}` : ""}
                  {cand.stale ? ` · ${t("visualDirector.stale")}` : ""}
                </div>
              </button>
            ))}
          </div>
        </CommercialCard>
      ) : null}

      {selected ? (
        <CommercialCard>
          <h2 className="mb-4 text-lg font-semibold">{t("visualDirector.previewHeading")}</h2>
          {previewSrc ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={previewSrc}
              alt={selected.title}
              className="max-h-[480px] w-full rounded-md object-contain"
              data-testid="visual-director-preview"
            />
          ) : null}
          <div className="mt-2 text-xs" style={{ color: "var(--ms-text-secondary)" }}>
            {t("visualDirector.versionLabel")}: {selected.current_version_number}
            {selected.approved_version_number
              ? ` · ${t("visualDirector.approvedVersion")}: ${selected.approved_version_number}`
              : ""}
            {selected.checksum ? ` · ${selected.checksum.slice(0, 18)}…` : ""}
          </div>
          {form.text_overlay.trim() && !approved ? (
            <label className="mt-3 flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={confirmOverlay}
                onChange={(e) => setConfirmOverlay(e.target.checked)}
                data-testid="visual-director-confirm-overlay"
              />
              {t("visualDirector.confirmOverlay")}
            </label>
          ) : null}
          <div className="mt-4 flex flex-wrap gap-2">
            <CommercialButton
              variant="secondary"
              disabled={!previewSrc}
              onClick={() => void onDownload()}
              testId="visual-director-download"
            >
              {t("visualDirector.actions.download")}
            </CommercialButton>
            <CommercialButton
              variant="secondary"
              disabled={approved || selected.rejected || busy}
              onClick={() => void onReject()}
              testId="visual-director-reject"
            >
              {t("visualDirector.actions.reject")}
            </CommercialButton>
            <CommercialButton
              disabled={
                approved ||
                selected.rejected ||
                busy ||
                (Boolean(form.text_overlay.trim()) && !confirmOverlay)
              }
              onClick={() => void onApprove()}
              testId="visual-director-approve"
            >
              {t("visualDirector.actions.approve")}
            </CommercialButton>
            <CommercialButton
              variant="secondary"
              disabled={approved || busy || genLock}
              onClick={() => void onGenerate()}
              testId="visual-director-regenerate"
            >
              {t("visualDirector.actions.regenerate")}
            </CommercialButton>
          </div>
        </CommercialCard>
      ) : null}

      {approved ? (
        <CommercialAlert
          tone="success"
          title={t("visualDirector.approvedBanner")}
          testId="visual-director-approved"
        />
      ) : null}
    </div>
  );
}
