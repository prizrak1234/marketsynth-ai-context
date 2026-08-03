"use client";

/**
 * Execution phase — Conversation + reference fidelity (H2.8A).
 * Not a Home. Shown after Verdict → Next Step on Canonical Commercial Home.
 */

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { AnimateImagePanel } from "@/components/workspace/home/animate-image-panel";
import { HomeConversation } from "@/components/workspace/home/home-conversation";
import { ReferenceUploadPanel } from "@/components/workspace/home/reference-upload-panel";
import {
  clarifyUserRequest,
  createUserRequest,
  listUserRequests,
  reviewContentDraft,
} from "@/lib/api/endpoints/user-requests";
import { listGeneratedVisualAssets } from "@/lib/api/endpoints/generated-visual-assets";
import { getOwnerVideoAcceptancePreview } from "@/lib/api/endpoints/video-clips";
import type { ContentDraftReviewAction } from "@/lib/api/types/user-requests";
import { reviewNotesFromAssets } from "@/lib/home/asset-review-hydration";
import {
  newClientMessageId,
  newIdempotencyKey,
  type ChatSubmitState,
} from "@/lib/chat/chat-message-contract";
import { mapCommercialError } from "@/lib/errors/commercial-error-mapper";
import { type IntentCategory } from "@/lib/home/intent-routing";
import {
  newId,
  saveHomeConversation,
  upsertLocalTaskFromRoute,
  createDraft,
  type HomeChatMessage,
} from "@/lib/home/home-persistence";
import {
  conversationFromUserRequests,
  userRequestToRoute,
  userRequestToTaskItem,
} from "@/lib/home/user-request-mappers";
import { useLocale } from "@/lib/i18n";
import { useVideoStudioCapabilities } from "@/lib/video-studio/use-video-capabilities";

type Props = {
  /** Seed from agency verdict flow (optional). */
  seedText?: string;
  /** Scenario from intent router (optional). */
  initialScenario?: IntentCategory | null;
  onBack?: () => void;
  /** Override back link label (owner video preview). */
  backLabelKey?: string;
  /** Owner-only canonical video acceptance preview (no research gate). */
  ownerVideoPreview?: boolean;
};

export function HomeExecutionPanel({
  seedText = "",
  initialScenario = null,
  onBack,
  backLabelKey,
  ownerVideoPreview = false,
}: Props) {
  const { t } = useLocale();
  const { data: videoCaps } = useVideoStudioCapabilities();
  const videoGenerationReady = videoCaps?.single_clip_generation_available === true;
  const [animateSourceAssetId, setAnimateSourceAssetId] = useState<string | null>(null);
  const [initialReviewNotes, setInitialReviewNotes] = useState<Record<string, string>>({});
  const [draftText, setDraftText] = useState(seedText);
  const [messages, setMessages] = useState<HomeChatMessage[]>([]);
  const [pendingClarifyId, setPendingClarifyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftBusyId, setDraftBusyId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [submitState, setSubmitState] = useState<ChatSubmitState>("idle");
  const sendInFlightRef = useRef(false);
  const hydrateInFlightRef = useRef(false);
  const pendingSubmitKeysRef = useRef<{
    text: string;
    clientMessageId: string;
    idempotencyKey: string;
  } | null>(null);

  const [referenceSetId, setReferenceSetId] = useState<string | null>(null);
  const [referenceCount, setReferenceCount] = useState(0);
  const [referenceUploading, setReferenceUploading] = useState(false);
  const [composerReady, setComposerReady] = useState(false);
  const [composerPrimaryId, setComposerPrimaryId] = useState<string | null>(null);
  const [composerPreserve, setComposerPreserve] = useState<string[]>([]);
  const [composerAllowed, setComposerAllowed] = useState<string[]>([]);
  const [composerFidelity, setComposerFidelity] = useState("maximum");
  const [composerStyle, setComposerStyle] = useState("low");

  const onReferenceSetChange = useCallback(
    (state: {
      setId: string | null;
      count: number;
      uploading: boolean;
      primaryReferenceId: string | null;
      subjectType: string;
      preserveTraits: string[];
      allowedChanges: string[];
      identityFidelity: string;
      styleFreedom: string;
      consent: boolean;
      ready: boolean;
    }) => {
      setReferenceSetId(state.setId);
      setReferenceCount(state.count);
      setReferenceUploading(state.uploading);
      setComposerReady(state.ready);
      setComposerPrimaryId(state.primaryReferenceId);
      setComposerPreserve(state.preserveTraits);
      setComposerAllowed(state.allowedChanges);
      setComposerFidelity(state.identityFidelity);
      setComposerStyle(state.styleFreedom);
      if (state.count > 0 && state.setId) {
        setPendingClarifyId(null);
      }
    },
    [],
  );

  const hydrateFromBackend = useCallback(async () => {
    if (hydrateInFlightRef.current) return;
    hydrateInFlightRef.current = true;
    try {
      const [rows, assets] = await Promise.all([
        listUserRequests(100),
        listGeneratedVisualAssets(100),
      ]);
      const notes = reviewNotesFromAssets(assets, {
        accepted: t("home.acceptResult"),
        rejected: t("home.rejectResultShort"),
      });
      setInitialReviewNotes(notes);

      if (ownerVideoPreview) {
        const binding = await getOwnerVideoAcceptancePreview();
        const sourceId = binding.source_image_asset_id;
        const previewNotes: Record<string, string> = { ...notes };
        if (binding.source_user_accepted) {
          previewNotes[sourceId] = t("home.acceptResult");
        }
        if (binding.video_user_accepted === true && binding.result_asset_id) {
          previewNotes[binding.result_asset_id] = t("home.acceptResult");
        } else if (binding.video_user_accepted === false && binding.result_asset_id) {
          previewNotes[binding.result_asset_id] = t("home.rejectResultShort");
        }
        setInitialReviewNotes(previewNotes);

        const requestId = binding.user_request_id || newId("owner-preview");
        const userMsg: HomeChatMessage = {
          id: newId("msg"),
          role: "user",
          text: binding.seed_brief,
          created_at: new Date().toISOString(),
        };
        const assistantMsg: HomeChatMessage = {
          id: newId("msg"),
          role: "assistant",
          text: t("home.animateImage.restoredFromLineage"),
          created_at: new Date().toISOString(),
          route: {
            kind: "specialist_task",
            category: "image_generation",
            label: "image_generation",
            clarificationQuestion: null,
            nextActionLabel: "",
            nextHref: null,
            requiresProject: false,
            assistantMessage: "",
          },
          skillCode: "image.generate_visual",
          generatedVisualAssetIds: [sourceId],
          generationStatus: "succeeded",
          generationWarnings: [],
          requestId,
        };
        setMessages([userMsg, assistantMsg]);
        setAnimateSourceAssetId(sourceId);
      } else {
        const conv = conversationFromUserRequests(rows);
        setMessages(conv.messages);
        const newest = rows[0];
        setPendingClarifyId(
          newest?.status === "needs_clarification" ? newest.id : null,
        );
        saveHomeConversation({ draftText: "", messages: conv.messages, lastDraft: conv.lastDraft });
      }
    } catch {
      /* keep empty */
    } finally {
      hydrateInFlightRef.current = false;
      setHydrated(true);
    }
  }, [ownerVideoPreview, t]);

  useEffect(() => {
    void hydrateFromBackend();
  }, [hydrateFromBackend]);

  useEffect(() => {
    if (seedText.trim()) setDraftText(seedText.trim());
  }, [seedText]);

  async function submitText(
    text: string,
    scenario: IntentCategory | null,
    extraSkillInputs?: Record<string, string>,
  ) {
    if (sendInFlightRef.current) return;

    const trimmed = text.trim();
    if (!trimmed && !scenario) {
      setError(t("home.needTask"));
      return;
    }
    if (referenceUploading) {
      setError(t("home.refUploadInProgress"));
      return;
    }

    sendInFlightRef.current = true;
    setError(null);
    setLoading(true);
    setSubmitState("submitting");

    const effectiveText =
      trimmed || (scenario ? t(`task.type.${scenario}`) : t("task.type.general"));

    const reuseKeys =
      pendingSubmitKeysRef.current?.text === effectiveText
        ? pendingSubmitKeysRef.current
        : null;
    const clientMessageId = reuseKeys?.clientMessageId ?? newClientMessageId();
    const idempotencyKey = reuseKeys?.idempotencyKey ?? newIdempotencyKey(clientMessageId);
    if (!reuseKeys) {
      pendingSubmitKeysRef.current = { text: effectiveText, clientMessageId, idempotencyKey };
    }

    try {
      const skillInputs: Record<string, string> = {
        ...(referenceSetId ? { reference_set_id: referenceSetId } : {}),
        ...(extraSkillInputs || {}),
      };
      const skillInputsOrUndefined =
        Object.keys(skillInputs).length > 0 ? skillInputs : undefined;

      const looksLikeNewTask =
        effectiveText.length > 100 ||
        /(?:напиши|создай|сгенерируй|сделай\s+изображен)/i.test(effectiveText) ||
        Boolean(referenceSetId && effectiveText.trim().length >= 40);

      setSubmitState("accepted");

      let dto;
      if (pendingClarifyId && !scenario && !looksLikeNewTask) {
        dto = await clarifyUserRequest(
          pendingClarifyId,
          effectiveText,
          skillInputsOrUndefined,
        );
      } else {
        dto = await createUserRequest({
          text: effectiveText,
          selected_scenario: scenario,
          skill_inputs: skillInputsOrUndefined,
          client_message_id: clientMessageId,
          idempotency_key: idempotencyKey,
        });
      }

      setSubmitState("completed");
      setPendingClarifyId(dto.status === "needs_clarification" ? dto.id : null);

      const route = userRequestToRoute(dto);
      const status = route.kind === "clarify" ? "needs_clarification" : "routed";
      const draft = createDraft(effectiveText, scenario, status, route);
      draft.id = dto.id;

      upsertLocalTaskFromRoute({
        text: effectiveText,
        category: scenario,
        route,
        draft,
      });

      const task = userRequestToTaskItem(dto);
      const { loadLocalWorkspaceTasks, saveLocalWorkspaceTasks } = await import(
        "@/lib/home/home-persistence"
      );
      const others = loadLocalWorkspaceTasks().filter((x) => x.id !== task.id);
      saveLocalWorkspaceTasks([task, ...others]);

      setDraftText("");
      pendingSubmitKeysRef.current = null;
      await hydrateFromBackend();
    } catch (err) {
      setSubmitState("failed");
      setError(mapCommercialError(err, t, "general").message);
    } finally {
      setLoading(false);
      sendInFlightRef.current = false;
      setSubmitState("idle");
    }
  }

  async function generateImageFromComposer() {
    if (sendInFlightRef.current) return;

    const trimmed = draftText.trim();
    if (!composerReady || !referenceSetId) {
      setError(t("home.needTask"));
      return;
    }
    if (referenceUploading) {
      setError(t("home.refUploadInProgress"));
      return;
    }
    setPendingClarifyId(null);
    setError(null);
    sendInFlightRef.current = true;
    setLoading(true);
    setSubmitState("submitting");

    const clientMessageId = newClientMessageId();
    const idempotencyKey = newIdempotencyKey(clientMessageId);

    try {
      const skillInputs: Record<string, string> = {
        reference_set_id: referenceSetId,
        force_image_generation: "true",
        identity_fidelity: composerFidelity,
        style_freedom: composerStyle,
        preserve_traits: composerPreserve.join(","),
        allowed_changes: composerAllowed.join(","),
        ...(composerPrimaryId ? { primary_reference_id: composerPrimaryId } : {}),
      };
      const dto = await createUserRequest({
        text: trimmed,
        selected_scenario: "image_generation",
        skill_inputs: skillInputs,
        client_message_id: clientMessageId,
        idempotency_key: idempotencyKey,
      });
      const route = userRequestToRoute(dto);
      const draft = createDraft(trimmed, "image_generation", "routed", route);
      draft.id = dto.id;
      setPendingClarifyId(null);
      upsertLocalTaskFromRoute({
        text: trimmed,
        category: "image_generation",
        route,
        draft,
      });
      setDraftText("");
      setSubmitState("completed");
      await hydrateFromBackend();
    } catch (err) {
      setSubmitState("failed");
      setError(mapCommercialError(err, t, "general").message);
    } finally {
      setLoading(false);
      sendInFlightRef.current = false;
      setSubmitState("idle");
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (composerReady && referenceSetId && draftText.trim().length >= 40) {
      void generateImageFromComposer();
      return;
    }
    void submitText(draftText, initialScenario);
  }

  return (
    <section
      className="space-y-4"
      data-testid="home-execution-panel"
      data-hydrated={hydrated ? "1" : "0"}
      data-submit-state={submitState}
      data-owner-video-preview={ownerVideoPreview ? "true" : "false"}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-semibold" data-testid="home-execution-title">
          {t("execution.title")}
        </h2>
        {onBack ? (
          <button
            type="button"
            className="text-sm underline"
            style={{ color: "var(--ms-text-secondary)" }}
            data-testid="home-execution-back"
            onClick={onBack}
          >
            {t(backLabelKey ?? "execution.backToVerdict")}
          </button>
        ) : null}
      </div>
      <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
        {t("execution.subtitle")}
      </p>

      <HomeConversation
        messages={messages}
        loading={loading}
        error={error}
        initialReviewNotes={initialReviewNotes}
        draftBusyId={draftBusyId}
        onReviewDraft={(msg, action: ContentDraftReviewAction) => {
          const requestId = msg.requestId;
          if (!requestId) return;
          if (action === "create_variant" || action === "request_revision") {
            const idx = messages.findIndex((m) => m.id === msg.id);
            const prior = [...messages.slice(0, idx)]
              .reverse()
              .find((m) => m.role === "user");
            setDraftBusyId(requestId);
            void reviewContentDraft(requestId, action)
              .then(() => {
                if (prior?.text) {
                  const suffix =
                    action === "create_variant" ? "\n\n(вариант)" : "\n\n(доработай)";
                  return submitText(`${prior.text}${suffix}`, null);
                }
                return hydrateFromBackend();
              })
              .finally(() => setDraftBusyId(null));
            return;
          }
          setDraftBusyId(requestId);
          void reviewContentDraft(requestId, action)
            .then(() => hydrateFromBackend())
            .finally(() => setDraftBusyId(null));
        }}
        onRetryGeneration={(msg) => {
          const idx = messages.findIndex((m) => m.id === msg.id);
          const prior = [...messages.slice(0, idx)].reverse().find((m) => m.role === "user");
          if (prior?.text) void submitText(prior.text, null);
        }}
        onCreateVariant={(msg) => {
          const idx = messages.findIndex((m) => m.id === msg.id);
          const prior = [...messages.slice(0, idx)].reverse().find((m) => m.role === "user");
          if (prior?.text) void submitText(`${prior.text}\n\n(вариант)`, null);
        }}
        onStrengthenLikeness={(msg) => {
          const idx = messages.findIndex((m) => m.id === msg.id);
          const prior = [...messages.slice(0, idx)].reverse().find((m) => m.role === "user");
          const parentId = msg.generatedVisualAssetIds?.[0];
          if (prior?.text) {
            void submitText(prior.text, null, {
              strengthen_likeness: "true",
              ...(parentId ? { parent_asset_id: parentId } : {}),
            });
          }
        }}
        onCreateVideoFromImage={(msg) => {
          const assetId = msg.generatedVisualAssetIds?.[0];
          if (assetId) setAnimateSourceAssetId(assetId);
        }}
      />

      {animateSourceAssetId ? (
        <AnimateImagePanel
          sourceImageAssetId={animateSourceAssetId}
          generationEnabled={videoGenerationReady}
          ownerVideoPreview={ownerVideoPreview}
          onClose={() => setAnimateSourceAssetId(null)}
          onVideoReviewChange={() => void hydrateFromBackend()}
        />
      ) : null}

      {!ownerVideoPreview ? (
      <form onSubmit={onSubmit} className="space-y-3" data-testid="home-intent-form">
        <label htmlFor="home-intent-input" className="sr-only">
          {t("execution.promptLabel")}
        </label>
        <textarea
          id="home-intent-input"
          rows={4}
          value={draftText}
          onChange={(e) => {
            setError(null);
            setDraftText(e.target.value);
          }}
          placeholder={
            referenceCount > 0
              ? t("home.placeholder")
              : pendingClarifyId
                ? t("home.clarifyPlaceholder")
                : t("home.placeholder")
          }
          className="w-full resize-y rounded-xl border px-4 py-3 text-sm leading-relaxed"
          style={{
            borderColor: "var(--ms-border-default)",
            background: "var(--ms-bg-surface)",
            color: "var(--ms-text-primary)",
          }}
          data-testid="home-intent-input"
        />
        <ReferenceUploadPanel
          open
          prompt={draftText}
          onReferenceSetChange={onReferenceSetChange}
          onGenerateImage={() => void generateImageFromComposer()}
          generateBusy={loading}
        />
        {referenceCount > 0 ? (
          <p
            className="text-xs"
            style={{ color: "var(--ms-text-secondary)" }}
            data-testid="home-refs-will-use"
          >
            {t("home.refsWillUse", { count: String(referenceCount) })}
          </p>
        ) : null}
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={loading || referenceUploading}
            className="rounded-md px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
            style={{
              background: "var(--ms-brand-primary)",
              color: "var(--ms-text-on-brand, #fff)",
            }}
            data-testid="home-intent-submit"
          >
            {composerReady ? t("home.generateImage") : t("execution.send")}
          </button>
        </div>
      </form>
      ) : null}
    </section>
  );
}
