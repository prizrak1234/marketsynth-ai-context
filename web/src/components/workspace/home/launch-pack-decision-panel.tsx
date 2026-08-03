"use client";

import { useMemo, useState } from "react";
import type {
  LaunchPackJourneyHydration,
  VerdictDecisionCta,
} from "@/lib/api/endpoints/launch-pack";
import { submitLaunchPackNextStep } from "@/lib/api/endpoints/launch-pack";
import { ApiError } from "@/lib/api/client";
import { useLocale, labelErrorCode } from "@/lib/i18n";
import { CommercialCard } from "@/components/commercial/commercial-card";
import { CommercialPageHeader } from "@/components/commercial/commercial-page-header";
import { OfferReviewCard } from "@/components/workspace/home/offer-review-card";

type Props = {
  journey: LaunchPackJourneyHydration;
  busy?: boolean;
  onBusyChange?: (busy: boolean) => void;
  onJourneyUpdate: (journey: LaunchPackJourneyHydration) => void;
  onReviseIdea: () => void;
  onRefineInputs: () => void;
  onStopProject: () => void;
};

export function LaunchPackDecisionPanel({
  journey,
  busy,
  onBusyChange,
  onJourneyUpdate,
  onReviseIdea,
  onRefineInputs,
  onStopProject,
}: Props) {
  const { t, locale } = useLocale();
  const branch = journey.decision_branch;
  const [accepted, setAccepted] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(branch.conditions.map((c) => [c, false])),
  );
  const [overrideReason, setOverrideReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showOverride, setShowOverride] = useState(false);

  const launch = journey.launch_pack_request;
  const offer = journey.offer;
  const launchRequested =
    launch?.status === "requested" || launch?.status === "in_progress";
  const launchBlocked = launch?.status === "blocked";
  const offerWorkflow = launch?.offer_workflow_status;
  const offerBlockers = launch?.blocker_codes ?? [];

  const buildingOffer = useMemo(
    () =>
      launchRequested &&
      !offer &&
      (offerWorkflow === "requested" ||
        offerWorkflow === "building_offer" ||
        launch?.status === "requested"),
    [launchRequested, offer, offerWorkflow, launch?.status],
  );

  async function handleCta(cta: VerdictDecisionCta) {
    if (busy) return;
    setError(null);

    if (cta.requires_risk_override && !showOverride) {
      setShowOverride(true);
      return;
    }

    if (cta.requires_conditions_acceptance && branch.conditions.length > 0) {
      const allAccepted = branch.conditions.every((c) => accepted[c]);
      if (!allAccepted) {
        setError(t("cwf.errors.conditionsRequired"));
        return;
      }
    }

    onBusyChange?.(true);
    try {
      const idem = `lp-${journey.project_id}-${cta.action}-${journey.validation.output.business_verdict_id ?? "none"}`;
      const result = await submitLaunchPackNextStep(journey.project_id, {
        selected_action: cta.action,
        accepted_conditions: cta.requires_conditions_acceptance ? acceptedList : [],
        override_reason: cta.requires_risk_override ? overrideReason : undefined,
        idempotency_key: idem,
      });
      onJourneyUpdate({
        ...journey,
        decision_branch: result.decision_branch,
        next_step_decision: result.decision,
        launch_pack_request: result.launch_pack_request ?? journey.launch_pack_request,
        offer: result.offer ?? journey.offer,
        updated_at: result.decision.updated_at,
      });
      if (cta.action === "revise_idea") onReviseIdea();
      if (cta.action === "refine_inputs") onRefineInputs();
      if (cta.action === "stop_project") onStopProject();
    } catch (err) {
      const code =
        err instanceof ApiError && typeof err.body === "object" && err.body
          ? String((err.body as { detail?: string }).detail || "")
          : "";
      setError(
        (code ? labelErrorCode(locale, code) : null) ||
          (err instanceof Error ? err.message : t("section.unavailable")),
      );
    } finally {
      onBusyChange?.(false);
    }
  }

  const acceptedList = useMemo(
    () => branch.conditions.filter((c) => accepted[c]),
    [accepted, branch.conditions],
  );

  const ctas: VerdictDecisionCta[] = [
    ...(branch.primary_cta ? [branch.primary_cta] : []),
    ...branch.secondary_ctas.filter(
      (s) => s.action !== branch.primary_cta?.action,
    ),
  ].slice(0, 3);

  const showDecisionCtas = !launchRequested && !offer;

  return (
    <CommercialCard testId="launch-pack-decision-panel" className="space-y-5">
      <CommercialPageHeader
        level="panel"
        eyebrow={
          <p className="text-xs uppercase tracking-wide" style={{ color: "var(--ms-text-muted)" }}>
            {t("cwf.decision.sectionLabel")}
          </p>
        }
        title={t(branch.headline_key)}
        description={branch.explanation}
        testId="cwf-decision-headline"
      />
      <p className="text-sm font-medium" data-testid="cwf-recommended-step">
        {t(branch.recommended_next_step_key)}
      </p>

      {branch.conditions.length > 0 && !offer ? (
        <div className="space-y-2" data-testid="cwf-conditions">
          <p className="text-sm font-semibold">{t("cwf.decision.conditionsTitle")}</p>
          <ul className="space-y-2 text-sm">
            {branch.conditions.map((condition) => (
              <li key={condition}>
                <label className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    className="mt-0.5"
                    checked={Boolean(accepted[condition])}
                    disabled={launchRequested || busy}
                    onChange={(e) =>
                      setAccepted((prev) => ({ ...prev, [condition]: e.target.checked }))
                    }
                    data-testid="cwf-condition-checkbox"
                  />
                  <span>{condition}</span>
                </label>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {!offer ? (
        <div className="grid gap-4 md:grid-cols-2">
          <div data-testid="cwf-launch-pack-included">
            <p className="text-sm font-semibold">{t("cwf.launchPack.includedTitle")}</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
              {branch.launch_pack_included_keys.map((key) => (
                <li key={key}>{t(key)}</li>
              ))}
            </ul>
          </div>
          <div data-testid="cwf-launch-pack-excluded">
            <p className="text-sm font-semibold">{t("cwf.launchPack.excludedTitle")}</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm" style={{ color: "var(--ms-text-muted)" }}>
              {branch.launch_pack_excluded_keys.map((key) => (
                <li key={key}>{t(key)}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}

      {buildingOffer ? (
        <div
          className="rounded-lg border px-4 py-3 text-sm"
          style={{
            borderColor: "color-mix(in srgb, var(--ms-brand-primary) 40%, var(--ms-border-default))",
            background: "color-mix(in srgb, var(--ms-brand-primary) 8%, var(--ms-bg-surface))",
          }}
          data-testid="cwf-offer-building"
        >
          <p className="font-semibold">{t("offer.building.title")}</p>
          <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
            {t("offer.building.body")}
          </p>
        </div>
      ) : null}

      {offerBlockers.length > 0 && !offer ? (
        <div
          className="rounded-lg border px-4 py-3 text-sm"
          style={{
            borderColor: "var(--ms-danger, #b42318)",
            background: "color-mix(in srgb, var(--ms-danger, #b42318) 6%, var(--ms-bg-surface))",
          }}
          data-testid="cwf-offer-blocked"
        >
          <p className="font-semibold">{t("offer.blocked.title")}</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {offerBlockers.map((code) => (
              <li key={code}>{labelErrorCode(locale, code) || t(`offer.blocked.${code}`) || code}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {launchRequested && !offer && !buildingOffer && offerBlockers.length === 0 ? (
        <div
          className="rounded-lg border px-4 py-3 text-sm"
          style={{
            borderColor: "color-mix(in srgb, var(--ms-brand-primary) 40%, var(--ms-border-default))",
            background: "color-mix(in srgb, var(--ms-brand-primary) 8%, var(--ms-bg-surface))",
          }}
          data-testid="cwf-launch-pack-requested"
        >
          <p className="font-semibold">{t("cwf.launchPack.requestedTitle")}</p>
          <p className="mt-1" style={{ color: "var(--ms-text-secondary)" }}>
            {t("cwf.launchPack.requestedBody")}
          </p>
        </div>
      ) : null}

      {launchBlocked ? (
        <p className="text-sm" style={{ color: "var(--ms-danger, #b42318)" }} data-testid="cwf-launch-pack-blocked">
          {t("cwf.launchPack.blocked")}
        </p>
      ) : null}

      {offer ? (
        <OfferReviewCard
          projectId={journey.project_id}
          offer={offer}
          busy={busy}
          onBusyChange={onBusyChange}
          onOfferUpdate={(updated) =>
            onJourneyUpdate({
              ...journey,
              offer: updated,
              launch_pack_request: journey.launch_pack_request
                ? {
                    ...journey.launch_pack_request,
                    offer_status: updated.status,
                    offer_version: updated.version_number,
                    offer_workflow_status:
                      updated.approval_status === "approved"
                        ? "offer_approved"
                        : updated.approval_status === "rejected"
                          ? "offer_rejected"
                          : "offer_review_required",
                  }
                : journey.launch_pack_request,
            })
          }
        />
      ) : null}

      {showOverride ? (
        <div className="space-y-2" data-testid="cwf-risk-override">
          <label className="text-sm font-semibold" htmlFor="cwf-override-reason">
            {t("cwf.decision.overrideLabel")}
          </label>
          <textarea
            id="cwf-override-reason"
            rows={3}
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
            className="w-full rounded-md border px-3 py-2 text-sm"
            style={{
              borderColor: "var(--ms-border-default)",
              background: "var(--ms-bg-canvas)",
            }}
          />
        </div>
      ) : null}

      {showDecisionCtas ? (
        <div className="flex flex-wrap gap-2">
          {ctas.map((cta, index) => (
            <button
              key={`${cta.action}-${index}`}
              type="button"
              disabled={busy}
              className="rounded-md px-4 py-2.5 text-sm font-semibold disabled:opacity-50"
              style={
                cta.is_primary
                  ? {
                      background: "var(--ms-brand-primary)",
                      color: "var(--ms-text-on-brand, #fff)",
                    }
                  : {
                      border: "1px solid var(--ms-border-default)",
                      color: "var(--ms-text-primary)",
                    }
              }
              data-testid={`cwf-cta-${cta.action}`}
              onClick={() => void handleCta(cta)}
            >
              {t(cta.label_key)}
            </button>
          ))}
        </div>
      ) : null}

      {error ? (
        <p className="text-sm" style={{ color: "var(--ms-danger, #b42318)" }}>
          {error}
        </p>
      ) : null}
    </CommercialCard>
  );
}
