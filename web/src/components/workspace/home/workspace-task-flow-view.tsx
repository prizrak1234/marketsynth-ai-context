"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { IntentCategory } from "@/lib/home/intent-routing";
import { buildAssistantHref } from "@/lib/home/intent-navigation";
import { labelTaskType, useLocale } from "@/lib/i18n";

/** Legacy ?intent= entry — redirect to AI assistant with preserved context. */
export function WorkspaceTaskFlowView() {
  const params = useSearchParams();
  const router = useRouter();
  const { locale } = useLocale();
  const intent = (params.get("intent") || "general") as IntentCategory;

  useEffect(() => {
    const label = labelTaskType(locale, intent);
    const task =
      intent === "content"
        ? "Подготовить пост для Telegram-канала."
        : intent === "youtube"
          ? "Подготовить сценарий для YouTube."
          : intent === "social_media"
            ? "Подготовить контент-план."
            : label;
    router.replace(buildAssistantHref(task, intent === "general" ? null : intent));
  }, [intent, locale, router]);

  return (
    <div className="p-8 text-sm" data-testid="workspace-task-flow-redirect">
      …
    </div>
  );
}
