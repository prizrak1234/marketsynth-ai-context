"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import {
  analyzeBusinessIntent,
  clarifyBusinessIntent,
  completeBusinessBrief,
  confirmBusinessBrief,
  createCampaignFromBusinessOperator,
} from "@/lib/api/endpoints/business-operator";
import type {
  BusinessOperatorAnalyzeResponse,
  BusinessOperatorClarification,
  BusinessOperatorClarifyResponse,
  CampaignBriefFields,
  CampaignBriefQuestion,
} from "@/lib/api/types/business-operator";

const SCENARIO_LABELS: Record<string, string> = {
  dental_clinic_lead_gen: "Dental Clinic Lead Gen",
  restaurant_launch: "Restaurant Launch",
  expert_blogger_content_machine: "Expert / Blogger Content Machine",
  telegram_bot_saas_launch: "Telegram Bot / SaaS Launch",
  local_service_promo: "Local Service Promo",
};

type AssistState = BusinessOperatorAnalyzeResponse | BusinessOperatorClarifyResponse;

type BusinessOperatorPanelProps = {
  projectId: string;
  onCampaignCreated?: (campaignId: string) => void;
};

function scenarioLabel(scenarioId: string) {
  return SCENARIO_LABELS[scenarioId] ?? scenarioId.replace(/_/g, " ");
}

function optionLabel(value: string) {
  return value.replace(/_/g, " ");
}

function ClarificationForm({
  questions,
  answers,
  onAnswerChange,
  onSubmit,
  isPending,
}: {
  questions: BusinessOperatorClarification[];
  answers: Record<string, string>;
  onAnswerChange: (field: string, value: string) => void;
  onSubmit: () => void;
  isPending: boolean;
}) {
  const requiredPending = questions.some(
    (question) => question.required && !answers[question.missing_field],
  );

  return (
    <div className="space-y-3">
      <p className="text-[10px] font-medium uppercase text-muted-foreground">
        Clarification needed
      </p>
      {questions.map((question) => (
        <div key={question.missing_field} className="rounded border border-border p-2">
          <p className="font-medium">{question.question}</p>
          <p className="mb-2 text-[10px] text-muted-foreground">{question.reason}</p>
          <div className="flex flex-wrap gap-1">
            {question.options.map((option) => (
              <button
                key={option}
                type="button"
                className={`rounded border px-2 py-0.5 text-[10px] ${
                  answers[question.missing_field] === option
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-muted/30"
                }`}
                onClick={() => onAnswerChange(question.missing_field, option)}
              >
                {optionLabel(option)}
              </button>
            ))}
          </div>
        </div>
      ))}
      <Button size="sm" disabled={isPending || requiredPending} onClick={onSubmit}>
        {isPending ? "Updating…" : "Submit answers"}
      </Button>
    </div>
  );
}

function BriefQuestionsForm({
  questions,
  answers,
  onAnswerChange,
  onSubmit,
  isPending,
}: {
  questions: CampaignBriefQuestion[];
  answers: Record<string, string>;
  onAnswerChange: (field: string, value: string) => void;
  onSubmit: () => void;
  isPending: boolean;
}) {
  const requiredPending = questions.some(
    (question) => question.required && !answers[question.field]?.trim(),
  );

  return (
    <div className="space-y-2">
      {questions.filter((question) => question.required).map((question) => (
        <div key={question.field} className="rounded border border-border p-2">
          <label className="mb-1 block text-[10px] font-medium">{question.question}</label>
          {question.options.length ? (
            <div className="mb-1 flex flex-wrap gap-1">
              {question.options.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={`rounded border px-2 py-0.5 text-[10px] ${
                    answers[question.field] === option
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border bg-muted/30"
                  }`}
                  onClick={() => onAnswerChange(question.field, option)}
                >
                  {optionLabel(option)}
                </button>
              ))}
            </div>
          ) : null}
          <input
            className="w-full rounded border border-input bg-background px-2 py-1 text-xs"
            value={answers[question.field] ?? ""}
            onChange={(event) => onAnswerChange(question.field, event.target.value)}
          />
        </div>
      ))}
      <Button size="sm" disabled={isPending || requiredPending} onClick={onSubmit}>
        {isPending ? "Saving…" : "Update brief"}
      </Button>
    </div>
  );
}

export function BusinessOperatorPanel({
  projectId,
  onCampaignCreated,
}: BusinessOperatorPanelProps) {
  const [message, setMessage] = useState("");
  const [assistState, setAssistState] = useState<AssistState | null>(null);
  const [clarificationAnswers, setClarificationAnswers] = useState<Record<string, string>>({});
  const [briefDraft, setBriefDraft] = useState<CampaignBriefFields | null>(null);
  const [briefCompleteness, setBriefCompleteness] = useState<
    AssistState["brief_completeness"] | null
  >(null);
  const [briefAnswers, setBriefAnswers] = useState<Record<string, string>>({});
  const [confirmedBriefId, setConfirmedBriefId] = useState<string | null>(null);

  const syncBrief = (result: AssistState) => {
    setBriefDraft(result.brief_draft);
    setBriefCompleteness(result.brief_completeness);
    setConfirmedBriefId(null);
  };

  const analyzeMutation = useMutation({
    mutationFn: () => analyzeBusinessIntent(projectId, { message: message.trim() }),
    onSuccess: (result) => {
      setAssistState(result);
      setClarificationAnswers({});
      syncBrief(result);
      setBriefAnswers({});
    },
  });

  const clarifyMutation = useMutation({
    mutationFn: () => {
      if (!assistState) throw new Error("No prior analysis");
      return clarifyBusinessIntent(projectId, {
        previous_intent: assistState.intent,
        answers: clarificationAnswers,
      });
    },
    onSuccess: (result) => {
      setAssistState(result);
      syncBrief(result);
      if (result.confidence_gate_passed) {
        setClarificationAnswers({});
      }
    },
  });

  const briefCompleteMutation = useMutation({
    mutationFn: () => {
      if (!assistState || !briefDraft) throw new Error("No brief draft");
      return completeBusinessBrief(projectId, {
        intent: assistState.intent,
        recommended_scenario: assistState.recommended_scenario,
        brief: briefDraft,
        answers: briefAnswers,
      });
    },
    onSuccess: (result) => {
      setBriefDraft(result.brief_draft);
      setBriefCompleteness(result.brief_completeness);
      setConfirmedBriefId(null);
    },
  });

  const briefConfirmMutation = useMutation({
    mutationFn: () => {
      if (!assistState || !briefDraft) throw new Error("No brief draft");
      return confirmBusinessBrief(projectId, {
        intent: assistState.intent,
        recommended_scenario: assistState.recommended_scenario,
        brief: briefDraft,
      });
    },
    onSuccess: (result) => {
      setBriefDraft(result.brief_draft);
      setBriefCompleteness(result.brief_completeness);
      setConfirmedBriefId(result.brief.id);
    },
  });

  const createMutation = useMutation({
    mutationFn: () => {
      if (!assistState?.confidence_gate_passed || !confirmedBriefId) {
        throw new Error("Brief must be confirmed before creating campaign");
      }
      return createCampaignFromBusinessOperator(projectId, {
        intent: assistState.intent,
        brief_id: confirmedBriefId,
      });
    },
    onSuccess: (result) => {
      onCampaignCreated?.(result.campaign.id);
    },
  });

  const analyzeError =
    analyzeMutation.error instanceof ApiError ? analyzeMutation.error.message : null;
  const clarifyError =
    clarifyMutation.error instanceof ApiError ? clarifyMutation.error.message : null;
  const briefError =
    briefCompleteMutation.error instanceof ApiError
      ? briefCompleteMutation.error.message
      : briefConfirmMutation.error instanceof ApiError
        ? briefConfirmMutation.error.message
        : null;
  const createError =
    createMutation.error instanceof ApiError ? createMutation.error.message : null;

  const canAnalyze = Boolean(message.trim()) && !analyzeMutation.isPending;
  const canConfirmBrief =
    assistState?.confidence_gate_passed &&
    briefCompleteness?.passed &&
    !briefConfirmMutation.isPending;

  return (
    <div className="mb-3 rounded-lg border border-primary/30 bg-primary/5 p-3">
      <h3 className="text-sm font-semibold">Business operator</h3>
      <p className="mb-2 text-xs text-muted-foreground">
        Describe your goal, confirm intent, complete the campaign brief, then create the campaign.
      </p>

      <form
        className="flex flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (!canAnalyze) return;
          analyzeMutation.mutate();
        }}
      >
        <textarea
          className="min-h-[72px] rounded border border-input bg-background px-2 py-1 text-xs"
          placeholder="Мне нужны лиды для стоматологии"
          value={message}
          onChange={(event) => {
            setMessage(event.target.value);
            setAssistState(null);
            setClarificationAnswers({});
            setBriefDraft(null);
            setBriefCompleteness(null);
            setConfirmedBriefId(null);
          }}
        />
        <Button type="submit" size="sm" disabled={!canAnalyze}>
          {analyzeMutation.isPending ? "Analyzing…" : "Analyze"}
        </Button>
      </form>

      {analyzeError ? <p className="mt-2 text-xs text-destructive">{analyzeError}</p> : null}

      {assistState && briefDraft && briefCompleteness ? (
        <div className="mt-3 space-y-3 rounded-md border border-border bg-background p-2 text-xs">
          <div className="flex items-center justify-between gap-2 text-[10px]">
            <span className="text-muted-foreground">
              Confidence: {(assistState.intent.confidence * 100).toFixed(0)}%
            </span>
            <span className={assistState.confidence_gate_passed ? "text-green-600" : "text-amber-600"}>
              {assistState.confidence_gate_passed ? "Intent ready" : "Intent needs clarification"}
            </span>
          </div>

          {!assistState.confidence_gate_passed && assistState.clarification_questions.length ? (
            <ClarificationForm
              questions={assistState.clarification_questions}
              answers={clarificationAnswers}
              onAnswerChange={(field, value) =>
                setClarificationAnswers((prev) => ({ ...prev, [field]: value }))
              }
              onSubmit={() => clarifyMutation.mutate()}
              isPending={clarifyMutation.isPending}
            />
          ) : null}

          {clarifyError ? <p className="text-destructive">{clarifyError}</p> : null}

          {assistState.confidence_gate_passed ? (
            <>
              <div className="rounded border border-dashed border-border p-2">
                <p className="mb-1 text-[10px] font-medium uppercase text-muted-foreground">
                  Campaign brief
                </p>
                <p className="text-[10px] text-muted-foreground">
                  Scenario: {scenarioLabel(assistState.recommended_scenario)}
                </p>
                <p className="text-[10px] text-muted-foreground">
                  Completeness: {briefCompleteness.score}/{briefCompleteness.threshold}
                  {briefCompleteness.passed ? " — ready" : " — missing fields"}
                </p>
                <div className="mt-2 grid gap-1 text-[10px]">
                  <p>Industry: {briefDraft.industry ?? "—"}</p>
                  <p>Goal: {briefDraft.goal ?? "—"}</p>
                  <p>Offer: {briefDraft.offer ?? "—"}</p>
                  <p>Audience: {briefDraft.target_audience ?? "—"}</p>
                </div>
              </div>

              {!briefCompleteness.passed && briefCompleteness.missing_questions.length ? (
                <BriefQuestionsForm
                  questions={briefCompleteness.missing_questions}
                  answers={briefAnswers}
                  onAnswerChange={(field, value) =>
                    setBriefAnswers((prev) => ({ ...prev, [field]: value }))
                  }
                  onSubmit={() => briefCompleteMutation.mutate()}
                  isPending={briefCompleteMutation.isPending}
                />
              ) : null}

              {briefError ? <p className="text-destructive">{briefError}</p> : null}

              <Button
                size="sm"
                variant="outline"
                disabled={!canConfirmBrief}
                onClick={() => briefConfirmMutation.mutate()}
              >
                {briefConfirmMutation.isPending
                  ? "Confirming…"
                  : confirmedBriefId
                    ? "Brief confirmed"
                    : "Confirm brief"}
              </Button>

              {assistState.preview ? (
                <div className="rounded border border-dashed border-border p-2">
                  <p className="mb-1 text-[10px] font-medium uppercase text-muted-foreground">
                    Campaign preview
                  </p>
                  <p className="font-semibold">{assistState.preview.campaign_name}</p>
                </div>
              ) : null}

              <Button
                size="sm"
                disabled={createMutation.isPending || !confirmedBriefId}
                onClick={() => createMutation.mutate()}
              >
                {createMutation.isPending ? "Creating…" : "Create campaign"}
              </Button>
              {createError ? <p className="text-destructive">{createError}</p> : null}
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
