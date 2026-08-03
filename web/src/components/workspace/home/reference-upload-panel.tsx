"use client";

import {
  DragEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { getApiBaseUrl, getApiKey } from "@/lib/api/config";
import {
  createReferenceSet,
  fetchReferenceLimits,
  fetchReferenceSelection,
  getReferenceSet,
  listReferenceSetAssets,
  listReferenceSets,
  patchReferenceAsset,
  patchReferenceSet,
  referenceAcceptAttr,
  uploadReferenceAsset,
  type ReferenceAssetDto,
  type ReferenceLimitsDto,
  type ReferenceSelectionDto,
} from "@/lib/api/endpoints/reference-visuals";
import {
  getImageGenerationReadiness,
  postIdentityReadiness,
  type IdentitySubsystemReadinessDto,
  type ImageGenerationReadinessDto,
} from "@/lib/api/endpoints/generated-visual-assets";
import {
  PERSON_ALLOWED_OPTIONS,
  PERSON_PRESERVE_OPTIONS,
  PERSON_PURPOSE_OPTIONS,
  buildImagePromptSummary,
  defaultAllowedChanges,
  defaultPreserveTraits,
  evaluateImageGenerationReadiness,
  styleFreedomForFidelity,
  type IdentityFidelity,
  type ImageComposerSubjectType,
  type StyleFreedom,
} from "@/lib/home/image-generation-composer";
import { useLocale } from "@/lib/i18n";
import { useAuth } from "@/lib/auth/auth-context";

type Props = {
  open: boolean;
  prompt: string;
  onReferenceSetChange: (state: {
    setId: string | null;
    count: number;
    uploading: boolean;
    primaryReferenceId: string | null;
    subjectType: string;
    preserveTraits: string[];
    allowedChanges: string[];
    identityFidelity: IdentityFidelity;
    styleFreedom: StyleFreedom;
    consent: boolean;
    ready: boolean;
  }) => void;
  onGenerateImage?: () => void;
  generateBusy?: boolean;
};

export function ReferenceUploadPanel({
  open,
  prompt,
  onReferenceSetChange,
  onGenerateImage,
  generateBusy,
}: Props) {
  const { t } = useLocale();
  const { user } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const [expanded, setExpanded] = useState(true);
  const [limits, setLimits] = useState<ReferenceLimitsDto | null>(null);
  const [setId, setSetId] = useState<string | null>(null);
  const [items, setItems] = useState<ReferenceAssetDto[]>([]);
  const [consent, setConsent] = useState(false);
  const [subjectType, setSubjectType] =
    useState<ImageComposerSubjectType>("person");
  const [primaryId, setPrimaryId] = useState<string | null>(null);
  const [selection, setSelection] = useState<ReferenceSelectionDto | null>(null);
  const [preserveTraits, setPreserveTraits] = useState<string[]>(defaultPreserveTraits);
  const [allowedChanges, setAllowedChanges] = useState<string[]>(defaultAllowedChanges);
  const [identityFidelity, setIdentityFidelity] =
    useState<IdentityFidelity>("maximum");
  const [styleFreedom, setStyleFreedom] = useState<StyleFreedom>("low");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const persistTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [providerReady, setProviderReady] =
    useState<ImageGenerationReadinessDto | null>(null);
  const [identityReady, setIdentityReady] =
    useState<IdentitySubsystemReadinessDto | null>(null);

  const maxCount = limits?.max_count ?? 15;
  const STORAGE_KEY = "ms_home_reference_set_id";

  useEffect(() => {
    if (!open) return;
    void fetchReferenceLimits()
      .then(setLimits)
      .catch(() => setLimits(null));
  }, [open]);

  // Hydrate last ReferenceSet after session is ready (retry if first call races auth).
  useEffect(() => {
    if (!open || !user) return;
    let cancelled = false;
    let attempts = 0;
    const STORAGE_KEY = "ms_home_reference_set_id";

    async function hydrateOnce() {
      attempts += 1;
      try {
        const stored =
          typeof window !== "undefined"
            ? window.localStorage.getItem(STORAGE_KEY)
            : null;
        const sets = await listReferenceSets(10);
        const best = [...sets].sort(
          (a, b) =>
            (b.reference_asset_ids?.length || 0) -
            (a.reference_asset_ids?.length || 0),
        )[0];
        // Prefer the richest owner set; ignore empty/stale localStorage ids.
        let targetId: string | null = null;
        if (
          stored &&
          sets.some(
            (s) =>
              s.id === stored && (s.reference_asset_ids?.length || 0) > 0,
          )
        ) {
          targetId = stored;
        } else if (best && (best.reference_asset_ids?.length || 0) > 0) {
          targetId = best.id;
        } else {
          targetId = best?.id ?? stored;
        }
        if (!targetId || cancelled) {
          if (!cancelled && attempts < 8) {
            window.setTimeout(() => {
              void hydrateOnce();
            }, 600);
          }
          return;
        }
        const setRow = await getReferenceSet(targetId);
        if (cancelled) return;
        const assets = await listReferenceSetAssets(targetId);
        if (cancelled) return;
        if (
          assets.length === 0 &&
          best &&
          best.id !== targetId &&
          (best.reference_asset_ids?.length || 0) > 0 &&
          attempts < 8
        ) {
          window.localStorage.setItem(STORAGE_KEY, best.id);
          window.setTimeout(() => {
            void hydrateOnce();
          }, 200);
          return;
        }
        if (assets.length === 0 && attempts < 8) {
          window.setTimeout(() => {
            void hydrateOnce();
          }, 600);
          return;
        }
        setSetId(setRow.id);
        setItems(assets);
        setPrimaryId(setRow.primary_reference_id);
        setConsent(Boolean(setRow.consent_confirmed) || assets.length > 0);
        if (setRow.subject_type === "person") setSubjectType("person");
        if (setRow.immutable_traits?.length) {
          setPreserveTraits(setRow.immutable_traits);
        }
        if (setRow.allowed_variations?.length) {
          setAllowedChanges(setRow.allowed_variations);
        }
        const notes = setRow.identity_notes || "";
        const fid = notes.match(/fidelity=(\w+)/)?.[1];
        const sty = notes.match(/style=(\w+)/)?.[1];
        if (fid === "maximum" || fid === "high" || fid === "balanced") {
          setIdentityFidelity(fid);
        }
        if (sty === "low" || sty === "medium" || sty === "high") {
          setStyleFreedom(sty);
        }
        setExpanded(true);
        try {
          const sel = await fetchReferenceSelection(targetId);
          if (!cancelled) setSelection(sel);
        } catch {
          /* ignore */
        }
        window.localStorage.setItem(STORAGE_KEY, targetId);
        if (!cancelled && assets.length > 0) {
          setInfo(
            `Восстановлен набор референсов: ${assets.length} файл(ов).`,
          );
        }
      } catch {
        if (!cancelled && attempts < 8) {
          window.setTimeout(() => {
            void hydrateOnce();
          }, 600);
        }
      }
    }

    void hydrateOnce();
    return () => {
      cancelled = true;
    };
  }, [open, user]);

  useEffect(() => {
    if (setId && typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, setId);
    }
  }, [setId]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    void getImageGenerationReadiness()
      .then((data) => {
        if (!cancelled) setProviderReady(data);
      })
      .catch(() => {
        if (!cancelled) setProviderReady(null);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    if (!open || subjectType !== "person") {
      setIdentityReady(null);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      void postIdentityReadiness({
        reference_set_id: setId,
        primary_reference_id: primaryId,
        prompt,
        consent,
        paid_approval_granted: false,
      })
        .then((data) => {
          if (!cancelled) setIdentityReady(data);
        })
        .catch(() => {
          if (!cancelled) setIdentityReady(null);
        });
    }, 350);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [open, subjectType, setId, primaryId, prompt, consent, items.length]);

  const readiness = useMemo(
    () =>
      evaluateImageGenerationReadiness({
        prompt,
        referenceSetId: setId,
        subjectType,
        preserveTraits,
        allowedChanges,
        identityFidelity,
        styleFreedom,
        primaryReferenceId: primaryId,
        referenceCount: items.length,
        uploading: busy,
        consent,
      }),
    [
      prompt,
      setId,
      subjectType,
      preserveTraits,
      allowedChanges,
      identityFidelity,
      styleFreedom,
      primaryId,
      items.length,
      busy,
      consent,
    ],
  );

  const readinessLines = useMemo(() => {
    const lines = [...readiness.lines];
    if (providerReady) {
      lines.push(
        `Провайдер: ${providerReady.identity_provider || providerReady.configured_provider}`,
      );
      if (providerReady.identity_capability_status) {
        lines.push(`Квалификация: ${providerReady.identity_capability_status}`);
      }
      if (typeof providerReady.identity_provider_input_capacity === "number") {
        lines.push(
          `Ёмкость входа провайдера: ${providerReady.identity_provider_input_capacity}`,
        );
      }
      if (providerReady.paid_approval_required) {
        lines.push("Для квалификации требуется подтверждение расходов");
      }
      if (providerReady.mock_only) {
        lines.push("Режим: mock (диагностика)");
      } else if (providerReady.real_generation_available) {
        lines.push("Режим: real");
      }
    }
    if (identityReady?.manifest_preview) {
      const m = identityReady.manifest_preview;
      lines.push(
        t("home.refTransmitCounts", {
          stored: String(m.stored_count),
          identity: String(m.identity_selected),
          style: String(m.style_selected),
          transmitted: String(m.transmitted_count),
          excluded: String(
            Math.max(
              0,
              m.stored_count - m.identity_selected - m.style_selected,
            ),
          ),
        }),
      );
    }
    if (identityReady?.safe_detail_lines?.length) {
      for (const line of identityReady.safe_detail_lines.slice(0, 3)) {
        if (!lines.includes(line)) lines.push(line);
      }
    } else if (providerReady?.identity_safe_summary) {
      lines.push(providerReady.identity_safe_summary);
    }
    return lines;
  }, [readiness.lines, providerReady, identityReady, t]);

  const blockingReason =
    readiness.blockingReason ||
    identityReady?.blocking_conditions?.find((c) => c.blocking && !c.ok)
      ?.safe_message ||
    null;

  const canGenerate =
    readiness.ready &&
    (providerReady?.can_generate !== false) &&
    (subjectType !== "person" || identityReady == null || identityReady.ready !== false || !identityReady.blocking_conditions?.some((c) => c.blocking && !c.ok && c.code !== "paid_approval_required"));


  const promptSummary = useMemo(
    () =>
      buildImagePromptSummary({
        prompt,
        referenceSetId: setId,
        subjectType,
        preserveTraits,
        allowedChanges,
        identityFidelity,
        styleFreedom,
        primaryReferenceId: primaryId,
        referenceCount: items.length,
        uploading: busy,
        consent,
      }),
    [
      prompt,
      setId,
      subjectType,
      preserveTraits,
      allowedChanges,
      identityFidelity,
      styleFreedom,
      primaryId,
      items.length,
      busy,
      consent,
    ],
  );

  useEffect(() => {
    onReferenceSetChange({
      setId,
      count: items.length,
      uploading: busy,
      primaryReferenceId: primaryId,
      subjectType,
      preserveTraits,
      allowedChanges,
      identityFidelity,
      styleFreedom,
      consent,
      ready: readiness.ready,
    });
  }, [
    setId,
    items.length,
    busy,
    primaryId,
    subjectType,
    preserveTraits,
    allowedChanges,
    identityFidelity,
    styleFreedom,
    consent,
    readiness.ready,
    onReferenceSetChange,
  ]);

  const remaining = useMemo(
    () => Math.max(0, maxCount - items.length),
    [maxCount, items.length],
  );

  const refreshSelection = useCallback(async (id: string) => {
    try {
      const sel = await fetchReferenceSelection(id);
      setSelection(sel);
    } catch {
      setSelection(null);
    }
  }, []);

  const persistProfile = useCallback(
    async (id: string) => {
      try {
        await patchReferenceSet(id, {
          subject_type: subjectType === "brand" ? "mixed" : subjectType,
          immutable_traits: preserveTraits,
          allowed_variations: allowedChanges,
          forbidden_changes: PERSON_PRESERVE_OPTIONS.map((o) => o.id).filter(
            (x) => !preserveTraits.includes(x),
          ),
          identity_notes: `fidelity=${identityFidelity};style=${styleFreedom}`,
          consent_confirmed: consent,
          primary_reference_id: primaryId,
        });
      } catch {
        /* non-blocking — generate path will retry */
      }
    },
    [
      subjectType,
      preserveTraits,
      allowedChanges,
      identityFidelity,
      styleFreedom,
      consent,
      primaryId,
    ],
  );

  useEffect(() => {
    if (!setId) return;
    if (persistTimer.current) clearTimeout(persistTimer.current);
    persistTimer.current = setTimeout(() => {
      void persistProfile(setId);
    }, 400);
    return () => {
      if (persistTimer.current) clearTimeout(persistTimer.current);
    };
  }, [setId, persistProfile]);

  const ensureSet = useCallback(async () => {
    if (setId) return setId;
    if (!consent) {
      throw new Error(t("home.refConsentRequired"));
    }
    const created = await createReferenceSet({
      title: t("home.refSetTitle"),
      subject_type: subjectType === "brand" ? "mixed" : subjectType,
      consent_confirmed: true,
      immutable_traits: preserveTraits,
    });
    setSetId(created.id);
    return created.id;
  }, [setId, consent, subjectType, preserveTraits, t]);

  const ingestFiles = useCallback(
    async (files: FileList | File[]) => {
      const list = Array.from(files);
      if (!list.length) return;
      setError(null);
      setInfo(null);
      if (!consent) {
        setError(t("home.refConsentRequired"));
        return;
      }
      if (list.length > remaining) {
        setError(t("home.refTooMany", { max: String(maxCount) }));
        return;
      }
      setBusy(true);
      try {
        const id = await ensureSet();
        let nextPrimary = primaryId;
        const attachNotes: string[] = [];
        for (let i = 0; i < list.length; i += 1) {
          const file = list[i];
          setProgress(
            t("home.refUploading", {
              current: String(i + 1),
              total: String(list.length),
            }),
          );
          const defaultPurpose = "other";
          const asset = await uploadReferenceAsset(id, file, {
            asset_purpose: defaultPurpose,
            subject_type: subjectType === "brand" ? "mixed" : subjectType,
            consent_confirmed: true,
          });
          if (asset.attach_message) attachNotes.push(asset.attach_message);
          // Do not auto-mark body/unknown as primary face.
          const canPrimary =
            subjectType !== "person" ||
            ["face_front", "face_three_quarter", "face_profile", "face_closeup", "face_reference", "identity_reference", "other"].includes(
              asset.asset_purpose,
            );
          if (asset.attach_status !== "already_attached" && !nextPrimary && canPrimary) {
            nextPrimary = asset.id;
            setPrimaryId(asset.id);
            await patchReferenceSet(id, { primary_reference_id: asset.id });
          } else if (!nextPrimary && asset.id && canPrimary) {
            nextPrimary = asset.id;
            setPrimaryId(asset.id);
          }
        }
        const refreshed = await listReferenceSetAssets(id);
        setItems(refreshed);
        await refreshSelection(id);
        await persistProfile(id);
        if (attachNotes.length) {
          setInfo(attachNotes[attachNotes.length - 1]);
        }
        if (subjectType === "person" && refreshed.length < 3) {
          setInfo((prev) =>
            [prev, t("home.refNeedMoreAngles")].filter(Boolean).join(" "),
          );
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : t("home.refUploadFailed"));
      } finally {
        setBusy(false);
        setProgress(null);
      }
    },
    [
      consent,
      remaining,
      maxCount,
      ensureSet,
      subjectType,
      primaryId,
      refreshSelection,
      persistProfile,
      t,
    ],
  );

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files?.length) {
      void ingestFiles(e.dataTransfer.files);
    }
  }

  async function markPrimary(assetId: string) {
    if (!setId) return;
    setPrimaryId(assetId);
    try {
      await patchReferenceSet(setId, { primary_reference_id: assetId });
      await refreshSelection(setId);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("home.refUploadFailed"));
    }
  }

  async function changePurpose(assetId: string, purpose: string) {
    try {
      const updated = await patchReferenceAsset(assetId, {
        asset_purpose: purpose,
        asset_purposes: [purpose],
      });
      setItems((prev) =>
        prev.map((a) => (a.id === assetId ? { ...a, ...updated } : a)),
      );
      if (setId) await refreshSelection(setId);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("home.refUploadFailed"));
    }
  }

  function toggleTrait(
    list: string[],
    setList: (next: string[]) => void,
    id: string,
  ) {
    setList(
      list.includes(id) ? list.filter((x) => x !== id) : [...list, id],
    );
  }

  if (!open) return null;

  return (
    <div
      className="rounded-xl border p-3"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid="home-reference-panel"
    >
      <button
        type="button"
        className="flex w-full items-center justify-between text-left text-sm font-semibold"
        onClick={() => setExpanded((v) => !v)}
        data-testid="home-reference-toggle"
      >
        <span>{t("home.addFiles")}</span>
        <span style={{ color: "var(--ms-text-muted)" }}>
          {items.length}/{maxCount}
        </span>
      </button>

      {expanded ? (
        <div className="mt-3 space-y-3">
          <p
            className="text-xs leading-relaxed"
            style={{ color: "var(--ms-text-secondary)" }}
            data-testid="home-reference-hint"
          >
            {t("home.refHint")}
          </p>
          <p
            className="text-xs leading-relaxed"
            style={{ color: "var(--ms-text-muted)" }}
            data-testid="home-reference-honest-copy"
          >
            {limits?.honest_copy_ru || t("home.refHonestCopy")}
          </p>

          <label className="flex items-start gap-2 text-xs">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              data-testid="home-reference-consent"
              className="mt-0.5"
            />
            <span>{t("home.refConsent")}</span>
          </label>

          <label className="flex items-center gap-2 text-xs">
            <span style={{ color: "var(--ms-text-muted)" }}>
              {t("home.refSubject")}
            </span>
            <select
              value={subjectType}
              onChange={(e) =>
                setSubjectType(e.target.value as ImageComposerSubjectType)
              }
              data-testid="home-reference-subject"
              className="rounded border px-2 py-1"
              style={{
                borderColor: "var(--ms-border-default)",
                background: "var(--ms-bg-elevated)",
              }}
            >
              <option value="person">{t("home.refSubjectPerson")}</option>
              <option value="product">{t("home.refSubjectProduct")}</option>
              <option value="logo">{t("home.refSubjectLogo")}</option>
              <option value="brand">{t("home.refSubjectBrand")}</option>
              <option value="object">{t("home.refSubjectObject")}</option>
              <option value="style">{t("home.refSubjectStyle")}</option>
              <option value="environment">
                {t("home.refSubjectEnvironment")}
              </option>
              <option value="other">{t("home.refSubjectMixed")}</option>
            </select>
          </label>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-4 py-6 text-center text-xs"
            style={{
              borderColor: dragOver
                ? "var(--ms-brand-primary)"
                : "var(--ms-border-default)",
              background: dragOver
                ? "color-mix(in srgb, var(--ms-brand-primary) 8%, transparent)"
                : "var(--ms-bg-elevated)",
            }}
            data-testid="home-reference-dropzone"
          >
            <p>{t("home.refDropHint")}</p>
            <button
              type="button"
              disabled={busy || remaining <= 0}
              className="rounded-md px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
              style={{
                background: "var(--ms-brand-primary)",
                color: "var(--ms-text-on-brand, #fff)",
              }}
              onClick={() => inputRef.current?.click()}
              data-testid="home-reference-pick"
            >
              {t("home.refPickFiles")}
            </button>
            <input
              ref={inputRef}
              type="file"
              accept={referenceAcceptAttr()}
              multiple
              className="hidden"
              data-testid="home-reference-file-input"
              onChange={(e) => {
                if (e.target.files) void ingestFiles(e.target.files);
                e.target.value = "";
              }}
            />
          </div>

          {progress ? (
            <p className="text-xs" data-testid="home-reference-progress">
              {progress}
            </p>
          ) : null}
          {info ? (
            <p
              className="text-xs"
              style={{ color: "var(--ms-text-secondary)" }}
              data-testid="home-reference-info"
            >
              {info}
            </p>
          ) : null}
          {error ? (
            <p
              className="text-xs"
              style={{ color: "#dc2626" }}
              data-testid="home-reference-error"
            >
              {error}
            </p>
          ) : null}

          {items.length > 0 ? (
            <ul
              className="grid grid-cols-2 gap-2 sm:grid-cols-3"
              data-testid="home-reference-grid"
            >
              {items.map((asset, idx) => (
                <li
                  key={asset.id}
                  className="relative overflow-hidden rounded-md border"
                  style={{ borderColor: "var(--ms-border-default)" }}
                  data-testid={`home-reference-thumb-${idx}`}
                >
                  <ReferenceThumb
                    assetId={asset.id}
                    alt={asset.original_filename}
                  />
                  <div className="space-y-1 p-1.5 text-[10px]">
                    <p style={{ color: "var(--ms-text-muted)" }}>
                      {asset.quality_status}
                      {primaryId === asset.id ? ` · ${t("home.refPrimaryMarked")}` : ""}
                    </p>
                    <select
                      value={asset.asset_purpose}
                      onChange={(e) => void changePurpose(asset.id, e.target.value)}
                      className="w-full rounded border px-1 py-0.5"
                      style={{
                        borderColor: "var(--ms-border-default)",
                        background: "var(--ms-bg-elevated)",
                      }}
                      data-testid={`home-reference-purpose-${idx}`}
                    >
                      {PERSON_PURPOSE_OPTIONS.map((p) => (
                        <option key={p.value} value={p.value}>
                          {t(p.labelKey)}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className="underline"
                      onClick={() => void markPrimary(asset.id)}
                      data-testid={`home-reference-primary-${idx}`}
                    >
                      {primaryId === asset.id
                        ? t("home.refPrimaryMarked")
                        : t("home.refMarkPrimary")}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}

          {subjectType === "person" ? (
            <div
              className="space-y-3 rounded-lg border p-3 text-xs"
              style={{ borderColor: "var(--ms-border-default)" }}
              data-testid="home-identity-controls"
            >
              <div>
                <p className="mb-2 font-semibold">{t("home.preserveSection")}</p>
                <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
                  {PERSON_PRESERVE_OPTIONS.map((opt) => (
                    <label key={opt.id} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={preserveTraits.includes(opt.id)}
                        onChange={() =>
                          toggleTrait(preserveTraits, setPreserveTraits, opt.id)
                        }
                        data-testid={`home-preserve-${opt.id}`}
                      />
                      <span>{t(opt.labelKey)}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-2 font-semibold">{t("home.allowSection")}</p>
                <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
                  {PERSON_ALLOWED_OPTIONS.map((opt) => (
                    <label key={opt.id} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={allowedChanges.includes(opt.id)}
                        onChange={() =>
                          toggleTrait(allowedChanges, setAllowedChanges, opt.id)
                        }
                        data-testid={`home-allow-${opt.id}`}
                      />
                      <span>{t(opt.labelKey)}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex flex-wrap gap-3">
                <label className="flex items-center gap-2">
                  <span style={{ color: "var(--ms-text-muted)" }}>
                    {t("home.identityFidelity")}
                  </span>
                  <select
                    value={identityFidelity}
                    onChange={(e) => {
                      const next = e.target.value as IdentityFidelity;
                      setIdentityFidelity(next);
                      setStyleFreedom(styleFreedomForFidelity(next));
                    }}
                    data-testid="home-identity-fidelity"
                    className="rounded border px-2 py-1"
                    style={{
                      borderColor: "var(--ms-border-default)",
                      background: "var(--ms-bg-elevated)",
                    }}
                  >
                    <option value="maximum">{t("home.fidelityMaximum")}</option>
                    <option value="high">{t("home.fidelityHigh")}</option>
                    <option value="balanced">{t("home.fidelityBalanced")}</option>
                  </select>
                </label>
                <label className="flex items-center gap-2">
                  <span style={{ color: "var(--ms-text-muted)" }}>
                    {t("home.styleFreedom")}
                  </span>
                  <select
                    value={styleFreedom}
                    onChange={(e) =>
                      setStyleFreedom(e.target.value as StyleFreedom)
                    }
                    data-testid="home-style-freedom"
                    className="rounded border px-2 py-1"
                    style={{
                      borderColor: "var(--ms-border-default)",
                      background: "var(--ms-bg-elevated)",
                    }}
                  >
                    <option value="low">{t("home.styleLow")}</option>
                    <option value="medium">{t("home.styleMedium")}</option>
                    <option value="high">{t("home.styleHigh")}</option>
                  </select>
                </label>
              </div>
            </div>
          ) : null}

          {selection?.selection_summary ? (
            <div
              className="space-y-1 text-xs"
              style={{ color: "var(--ms-text-secondary)" }}
              data-testid="home-reference-selection"
            >
              <p>{selection.selection_summary}</p>
              {typeof selection.identity_selected_count === "number" ? (
                <p data-testid="home-selection-counts">
                  {t("home.refTransmitCounts", {
                    stored: String(
                      selection.stored_count ??
                        identityReady?.manifest_preview?.stored_count ??
                        items.length,
                    ),
                    identity: String(selection.identity_selected_count ?? 0),
                    style: String(selection.style_selected_count ?? 0),
                    transmitted: String(
                      identityReady?.manifest_preview?.transmitted_count ??
                        identityReady?.references_provider_will_receive ??
                        (selection.primary_reference_id ? 1 : 0),
                    ),
                    excluded: String(selection.excluded_count ?? 0),
                  })}
                </p>
              ) : null}
              {identityReady?.manifest_preview?.safe_transmit_note ||
              providerReady?.identity_safe_summary ? (
                <p
                  data-testid="home-transmit-honesty"
                  style={{ color: "var(--ms-text-muted)" }}
                >
                  {identityReady?.manifest_preview?.safe_transmit_note ||
                    providerReady?.identity_safe_summary ||
                    t("home.refTransmissionPrimaryOnly")}
                </p>
              ) : null}
              {selection.roles && selection.roles.length > 0 ? (
                <ul className="mt-1 space-y-0.5" data-testid="home-selection-roles">
                  {selection.roles.map((r) => {
                    const reasonRu: Record<string, string> = {
                      not_face_reference: "Не референс лица",
                      style_only: "Только для стиля",
                      body_not_primary: "Тело не может быть основным лицом",
                      provider_limit: "Лимит провайдера",
                      duplicate_checksum: "Дубликат файла",
                      lower_quality: "Ниже качество",
                      not_selected: "Не выбрано",
                      body_only: "Только тело/поза",
                    };
                    const reason =
                      r.exclusion_reason && reasonRu[r.exclusion_reason]
                        ? reasonRu[r.exclusion_reason]
                        : null;
                    return (
                      <li key={r.reference_id}>
                        {r.role_label}
                        {r.is_primary ? ` · ${t("home.refRolePrimary")}` : ""}
                        {r.selected
                          ? ` · ${t("home.refStatusSelected")}`
                          : ` · ${t("home.refStatusExcluded")}`}
                        {!r.selected && reason ? ` — ${reason}` : ""}
                      </li>
                    );
                  })}
                </ul>
              ) : null}
            </div>
          ) : null}

          {(items.length > 0 || prompt.trim().length >= 40) ? (
            <div
              className="space-y-2 rounded-lg border p-3 text-xs"
              style={{ borderColor: "var(--ms-border-default)" }}
              data-testid="home-generation-readiness"
            >
              <p className="font-semibold" data-testid="home-readiness-title">
                {identityReady?.safe_summary || readiness.title}
              </p>
              <ul className="space-y-0.5" style={{ color: "var(--ms-text-secondary)" }}>
                {readinessLines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
              {promptSummary.length > 0 ? (
                <div data-testid="home-prompt-summary">
                  <p className="font-semibold">{t("home.whatWillBeCreated")}</p>
                  <ul className="mt-1 list-disc pl-4">
                    {promptSummary.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {blockingReason ? (
                <p style={{ color: "#b45309" }} data-testid="home-readiness-block">
                  {blockingReason}
                </p>
              ) : null}
              {canGenerate && onGenerateImage ? (
                <button
                  type="button"
                  disabled={generateBusy || busy}
                  onClick={() => onGenerateImage()}
                  className="mt-1 rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50"
                  style={{
                    background: "var(--ms-brand-primary)",
                    color: "var(--ms-text-on-brand, #fff)",
                  }}
                  data-testid="home-generate-image"
                >
                  {t("home.generateImage")}
                </button>
              ) : null}
            </div>
          ) : null}

          <p
            className="text-[11px] leading-relaxed"
            style={{ color: "var(--ms-text-muted)" }}
            data-testid="home-reference-logo-note"
          >
            {t("home.refLogoExact")}
          </p>
        </div>
      ) : null}
    </div>
  );
}

function ReferenceThumb({ assetId, alt }: { assetId: string; alt: string }) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    let revoked: string | null = null;
    let cancelled = false;
    (async () => {
      const headers = new Headers();
      const apiKey = getApiKey();
      if (apiKey) headers.set("Authorization", `Bearer ${apiKey}`);
      const res = await fetch(
        `${getApiBaseUrl()}/reference-visual-assets/${assetId}/content`,
        { credentials: "include", cache: "no-store", headers },
      );
      if (!res.ok || cancelled) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      revoked = url;
      if (!cancelled) setSrc(url);
    })().catch(() => undefined);
    return () => {
      cancelled = true;
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [assetId]);

  if (!src) {
    return (
      <div
        className="aspect-square w-full"
        style={{ background: "var(--ms-bg-elevated)" }}
      />
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} className="aspect-square w-full object-cover" />
  );
}
