/**
 * Workspace Task index — same source as Home: backend UserRequest (+ local fallback).
 */

import { listUserRequests } from "@/lib/api/endpoints/user-requests";
import { loadLocalWorkspaceTasks } from "@/lib/home/home-persistence";
import { userRequestToTaskItem } from "@/lib/home/user-request-mappers";
import type { WorkspaceTaskItem } from "@/lib/home/workspace-task-types";
import { getIntegrationMode } from "@/lib/integration/mode";

export type WorkspaceTaskIndexResult = {
  state: "loading" | "success" | "empty" | "error" | "mock_notice" | "unauthorized";
  items: WorkspaceTaskItem[];
  message: string | null;
  persistenceNote: string;
};

export async function loadWorkspaceTaskIndex(): Promise<WorkspaceTaskIndexResult> {
  const mode = getIntegrationMode();

  if (mode === "mock") {
    return {
      state: "mock_notice",
      items: [],
      message:
        "Mock-режим не подставляет выдуманные задачи. Переключитесь на backend или опишите задачу на Главной.",
      persistenceNote: "Mock — без серверных запросов.",
    };
  }

  try {
    const remote = await listUserRequests(100);
    const items = remote
      .map(userRequestToTaskItem)
      .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
    if (items.length === 0) {
      return {
        state: "empty",
        items: [],
        message: null,
        persistenceNote:
          "Задачи сохраняются на сервере (UserRequest). История привязана к вашей учётной записи.",
      };
    }
    return {
      state: "success",
      items,
      message: null,
      persistenceNote:
        "Источник: backend UserRequest. Локальные черновики не подменяют серверный список.",
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : "";
    if (/401|403|unauthorized/i.test(msg)) {
      return {
        state: "unauthorized",
        items: [],
        message: "Нет доступа к списку задач.",
        persistenceNote: "",
      };
    }
    // Offline / API down — labelled local fallback, never pretended as backend SoT
    const local = loadLocalWorkspaceTasks();
    if (local.length) {
      return {
        state: "success",
        items: local,
        message: null,
        persistenceNote:
          "Сервер временно недоступен. Показаны локальные черновики (authority=local_draft).",
      };
    }
    return {
      state: "error",
      items: [],
      message: "Не удалось загрузить список задач.",
      persistenceNote: "",
    };
  }
}
