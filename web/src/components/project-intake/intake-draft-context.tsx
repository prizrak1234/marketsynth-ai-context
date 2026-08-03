"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { createEmptyDraft } from "@/lib/project-intake/schema";
import { evaluateIntakeReadiness } from "@/lib/project-intake/readiness";
import {
  clearIntakeDraft,
  loadIntakeDraft,
  saveIntakeDraft,
} from "@/lib/project-intake/storage";
import type {
  IntakeStepId,
  ProjectIntakeDraft,
} from "@/lib/project-intake/types";

export type IntakeSaveStatus = "idle" | "saving" | "saved" | "error";

type IntakeContextValue = {
  draft: ProjectIntakeDraft;
  hydrated: boolean;
  saveStatus: IntakeSaveStatus;
  setDraft: (updater: (prev: ProjectIntakeDraft) => ProjectIntakeDraft) => void;
  patchDraft: (partial: Partial<ProjectIntakeDraft>) => void;
  setStep: (step: IntakeStepId) => void;
  persist: () => void;
  saveDraftNotice: () => string;
  resetDraft: () => void;
  refreshReadiness: () => void;
};

const IntakeContext = createContext<IntakeContextValue | null>(null);

export function IntakeDraftProvider({ children }: { children: ReactNode }) {
  const [draft, setDraftState] = useState<ProjectIntakeDraft>(() => createEmptyDraft());
  const [hydrated, setHydrated] = useState(false);
  const [saveStatus, setSaveStatus] = useState<IntakeSaveStatus>("idle");

  useEffect(() => {
    setDraftState(loadIntakeDraft());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    setSaveStatus("saving");
    const saveTimer = window.setTimeout(() => {
      try {
        saveIntakeDraft(draft);
        setSaveStatus("saved");
      } catch {
        setSaveStatus("error");
      }
    }, 400);
    const idleTimer = window.setTimeout(() => {
      setSaveStatus((current) => (current === "saved" ? "idle" : current));
    }, 4000);
    return () => {
      window.clearTimeout(saveTimer);
      window.clearTimeout(idleTimer);
    };
  }, [draft, hydrated]);

  const setDraft = useCallback(
    (updater: (prev: ProjectIntakeDraft) => ProjectIntakeDraft) => {
      setDraftState((prev) => updater(prev));
    },
    [],
  );

  const patchDraft = useCallback((partial: Partial<ProjectIntakeDraft>) => {
    setDraftState((prev) => ({ ...prev, ...partial }));
  }, []);

  const setStep = useCallback((step: IntakeStepId) => {
    setDraftState((prev) => ({ ...prev, currentStep: step }));
  }, []);

  const persist = useCallback(() => {
    saveIntakeDraft(draft);
  }, [draft]);

  const saveDraftNotice = useCallback(() => {
    const next = {
      ...draft,
      savedAsDraftAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setDraftState(next);
    saveIntakeDraft(next);
    return "Черновик сохранён локально (localStorage). Полный бриф на backend пока не выгружается.";
  }, [draft]);

  const resetDraft = useCallback(() => {
    clearIntakeDraft();
    setDraftState(createEmptyDraft());
  }, []);

  const refreshReadiness = useCallback(() => {
    setDraftState((prev) => ({
      ...prev,
      readiness: evaluateIntakeReadiness(prev),
    }));
  }, []);

  const value = useMemo(
    () => ({
      draft,
      hydrated,
      saveStatus,
      setDraft,
      patchDraft,
      setStep,
      persist,
      saveDraftNotice,
      resetDraft,
      refreshReadiness,
    }),
    [
      draft,
      hydrated,
      saveStatus,
      setDraft,
      patchDraft,
      setStep,
      persist,
      saveDraftNotice,
      resetDraft,
      refreshReadiness,
    ],
  );

  return <IntakeContext.Provider value={value}>{children}</IntakeContext.Provider>;
}

export function useIntakeDraft(): IntakeContextValue {
  const ctx = useContext(IntakeContext);
  if (!ctx) {
    throw new Error("useIntakeDraft must be used within IntakeDraftProvider");
  }
  return ctx;
}
