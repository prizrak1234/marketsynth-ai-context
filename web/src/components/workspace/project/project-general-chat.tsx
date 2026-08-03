"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CommercialButton } from "@/components/commercial/commercial-button";
import { CommercialCard } from "@/components/commercial/commercial-card";
import {
  fetchProjectGeneral,
  sendProjectGeneralMessage,
  type PccGeneralMessage,
} from "@/lib/api/endpoints/project-command-center";
import { useLocale } from "@/lib/i18n";

type Props = {
  projectId: string;
};

const QUICK = [
  { id: "text", message: "Напиши Telegram-пост для проекта" },
  { id: "image", message: "Создай изображение к материалам проекта" },
  { id: "keywords", message: "Проверь частотность ключевых фраз" },
  { id: "capabilities", message: "Покажи возможности агентства" },
] as const;

const CAPABILITY_LABEL_RU: Record<string, string> = {
  "project.content_director": "Контент",
  "project.research": "Проверка идеи",
  "project.integrations": "Интеграции",
  "launch.visuals": "Видео",
  "workspace.knowledge": "Материалы",
};

const CAPABILITY_LABEL_EN: Record<string, string> = {
  "project.content_director": "Content",
  "project.research": "Idea research",
  "project.integrations": "Integrations",
  "launch.visuals": "Video",
  "workspace.knowledge": "Materials",
};

const SKILL_LABEL_RU: Record<string, string> = {
  "marketsynth.copywriter": "Копирайтер",
  "marketsynth.visual_generation": "Генерация изображений",
  "marketsynth.xmlriver.wordstat": "Wordstat",
  "marketsynth.avito": "Avito",
};

const SKILL_LABEL_EN: Record<string, string> = {
  "marketsynth.copywriter": "Copywriter",
  "marketsynth.visual_generation": "Image generation",
  "marketsynth.xmlriver.wordstat": "Wordstat",
  "marketsynth.avito": "Avito",
};

export function ProjectGeneralChat({ projectId }: Props) {
  const { t, locale } = useLocale();
  const router = useRouter();
  const capabilityLabels = locale === "en" ? CAPABILITY_LABEL_EN : CAPABILITY_LABEL_RU;
  const skillLabels = locale === "en" ? SKILL_LABEL_EN : SKILL_LABEL_RU;
  const [messages, setMessages] = useState<PccGeneralMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const conv = await fetchProjectGeneral(projectId);
      setMessages(conv.messages);
    } catch {
      setError(t("projectGeneral.loadError"));
    }
  }, [projectId, t]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await sendProjectGeneralMessage(projectId, trimmed);
      setMessages(res.conversation.messages);
      setDraft("");
    } catch {
      setError(t("projectGeneral.sendError"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="space-y-4" data-testid="project-general-chat" id="pcc-general">
      <div>
        <h2 className="text-lg font-semibold" style={{ color: "var(--ms-text-primary)" }}>
          {t("projectGeneral.title")}
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--ms-text-secondary)" }}>
          {t("projectGeneral.subtitle")}
        </p>
      </div>

      <CommercialCard padding="md" testId="project-general-thread">
        {messages.length === 0 ? (
          <p
            className="text-sm"
            style={{ color: "var(--ms-text-muted)" }}
            data-testid="project-general-empty"
          >
            {t("projectGeneral.empty")}
          </p>
        ) : (
          <ul className="max-h-72 space-y-3 overflow-y-auto">
            {messages.map((m) => (
              <li
                key={m.id}
                className="rounded-md border px-3 py-2 text-sm"
                style={{ borderColor: "var(--ms-border-default)" }}
                data-testid={`project-general-message-${m.role}`}
              >
                <p className="text-xs font-medium uppercase" style={{ color: "var(--ms-text-muted)" }}>
                  {m.role === "user" ? t("projectGeneral.you") : t("projectGeneral.agency")}
                </p>
                <p className="mt-1 whitespace-pre-wrap">{m.content}</p>
                {m.role === "assistant" && (m.capability_id || m.skill_id || m.next_href) ? (
                  <div
                    className="mt-2 space-y-1 text-xs"
                    style={{ color: "var(--ms-text-muted)" }}
                    data-testid="project-general-route"
                  >
                    {m.capability_id ? (
                      <p>
                        {t("projectGeneral.capability")}:{" "}
                        {capabilityLabels[m.capability_id] || t("projectGeneral.capabilityFallback")}
                      </p>
                    ) : null}
                    {m.skill_id ? (
                      <p>
                        {t("projectGeneral.skill")}:{" "}
                        {skillLabels[m.skill_id] || t("projectGeneral.skillFallback")}
                      </p>
                    ) : null}
                    {m.requires_paid ? <p>{t("projectGeneral.requiresPaid")}</p> : null}
                    {m.requires_external ? <p>{t("projectGeneral.requiresExternal")}</p> : null}
                    {m.requires_approval ? <p>{t("projectGeneral.requiresApproval")}</p> : null}
                    {m.next_href && m.next_action_label ? (
                      <CommercialButton
                        className="mt-2"
                        onClick={() => router.push(m.next_href!)}
                        testId="project-general-follow-route"
                      >
                        {m.next_action_label}
                      </CommercialButton>
                    ) : null}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </CommercialCard>

      <div className="flex flex-wrap gap-2" data-testid="project-general-quick-actions">
        {QUICK.map((q) => (
          <CommercialButton
            key={q.id}
            variant="secondary"
            disabled={busy}
            onClick={() => void send(q.message)}
            testId={`project-general-quick-${q.id}`}
          >
            {t(`projectGeneral.quick.${q.id}`)}
          </CommercialButton>
        ))}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <label className="min-w-0 flex-1 text-sm">
          <span className="sr-only">{t("projectGeneral.inputLabel")}</span>
          <textarea
            className="min-h-[88px] w-full rounded-md border px-3 py-2 text-sm"
            style={{
              borderColor: "var(--ms-border-default)",
              background: "var(--ms-bg-surface)",
              color: "var(--ms-text-primary)",
            }}
            value={draft}
            disabled={busy}
            data-testid="project-general-input"
            placeholder={t("projectGeneral.placeholder")}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send(draft);
              }
            }}
          />
        </label>
        <CommercialButton
          disabled={busy || !draft.trim()}
          onClick={() => void send(draft)}
          testId="project-general-send"
        >
          {busy ? t("projectGeneral.sending") : t("projectGeneral.send")}
        </CommercialButton>
      </div>
      {error ? (
        <p className="text-sm" style={{ color: "var(--ms-danger, #b42318)" }}>
          {error}
        </p>
      ) : null}
    </section>
  );
}
