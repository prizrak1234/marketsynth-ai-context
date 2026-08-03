"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { canBypassCommercialSurfaceFreeze } from "@/lib/home/developer-mode";
import { CANONICAL_COMMERCIAL_ROUTES, canonicalIntakeHref, workspaceProjectHref } from "@/lib/routes/commercial-routes";
import { useLocale } from "@/lib/i18n";

type LegacyCommercialGuardProps = {
  children: React.ReactNode;
  /** i18n key for feature name in notice */
  featureKey: string;
  redirectHref?: string;
};

/** Redirect commercial users away from frozen/legacy surfaces (developer mode bypass). */
export function LegacyCommercialGuard({
  children,
  featureKey,
  redirectHref = CANONICAL_COMMERCIAL_ROUTES.workspaceHome,
}: LegacyCommercialGuardProps) {
  const router = useRouter();
  const { t } = useLocale();
  const allowed = canBypassCommercialSurfaceFreeze();

  useEffect(() => {
    if (!allowed) {
      router.replace(redirectHref);
    }
  }, [allowed, redirectHref, router]);

  if (allowed) {
    return children;
  }

  return (
    <div
      className="mx-auto max-w-lg space-y-4 rounded-xl border p-6"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
      data-testid="legacy-commercial-notice"
    >
      <p className="text-sm font-semibold">{t("commercial.surface.legacyNoticeTitle")}</p>
      <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
        {t("commercial.surface.legacyNoticeBody", { feature: t(featureKey) })}
      </p>
      <Link
        href={canonicalIntakeHref()}
        className="inline-flex rounded-md px-4 py-2 text-sm font-semibold"
        style={{
          background: "var(--ms-brand-primary)",
          color: "var(--ms-text-on-brand, #fff)",
        }}
        data-testid="legacy-commercial-canonical-cta"
      >
        {t("commercial.surface.goToCanonical")}
      </Link>
    </div>
  );
}

type LegacyProjectPipelineGuardProps = {
  projectId: string;
  children: React.ReactNode;
};

export function LegacyProjectPipelineGuard({
  projectId,
  children,
}: LegacyProjectPipelineGuardProps) {
  const router = useRouter();
  const allowed = canBypassCommercialSurfaceFreeze();
  const redirectHref = workspaceProjectHref(projectId);

  useEffect(() => {
    if (!allowed) {
      router.replace(redirectHref);
    }
  }, [allowed, redirectHref, router]);

  if (allowed) {
    return children;
  }

  return (
    <LegacyCommercialGuard featureKey="commercial.surface.features.projectPipeline" redirectHref={redirectHref}>
      {null}
    </LegacyCommercialGuard>
  );
}
