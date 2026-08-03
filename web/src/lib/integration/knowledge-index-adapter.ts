/**
 * Knowledge index — do not equate all memory with user-facing Knowledge.
 * No approved Knowledge SoT → honest empty.
 */

import { getIntegrationMode } from "@/lib/integration/mode";

export type KnowledgeIndexResult = {
  state: "empty" | "mock_notice";
  items: never[];
  message: string;
};

export async function loadKnowledgeIndex(): Promise<KnowledgeIndexResult> {
  const mode = getIntegrationMode();
  if (mode === "mock") {
    return {
      state: "mock_notice",
      items: [],
      message:
        "Mock-режим не показывает выдуманные знания. Backend Knowledge SoT для пользователя ещё не утверждён.",
    };
  }
  return {
    state: "empty",
    items: [],
    message:
      "Раздел знаний будет собирать подтверждённые выводы и повторно используемые материалы после завершения проектов.",
  };
}
