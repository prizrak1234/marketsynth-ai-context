import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  HOME_DEVELOPER_MODE_KEY,
  canBypassCommercialSurfaceFreeze,
  isDeveloperEnvironmentAllowed,
  isHomeDeveloperMode,
  readHomeDeveloperModeLocalFlag,
} from "./developer-mode";

type StorageMock = {
  getItem: (key: string) => string | null;
  setItem: (key: string, value: string) => void;
  removeItem: (key: string) => void;
};

function installWindowStorage(initial: Record<string, string> = {}): () => void {
  const store = { ...initial };
  const storage: StorageMock = {
    getItem: (key) => (key in store ? store[key] : null),
    setItem: (key, value) => {
      store[key] = value;
    },
    removeItem: (key) => {
      delete store[key];
    },
  };
  const prevWindow = (globalThis as { window?: typeof globalThis.window }).window;
  (globalThis as { window?: { localStorage: StorageMock } }).window = {
    localStorage: storage,
  } as typeof globalThis.window;
  return () => {
    if (prevWindow === undefined) {
      delete (globalThis as { window?: typeof globalThis.window }).window;
    } else {
      (globalThis as { window?: typeof globalThis.window }).window = prevWindow;
    }
  };
}

describe("developer-mode boundary (RUNTIME-01E)", () => {
  it("production build ignores localStorage developer flag for effective mode", () => {
    const restoreWindow = installWindowStorage({ [HOME_DEVELOPER_MODE_KEY]: "1" });
    try {
      assert.equal(readHomeDeveloperModeLocalFlag(), true);
      assert.equal(isDeveloperEnvironmentAllowed("production"), false);
      assert.equal(isHomeDeveloperMode("production"), false);
      assert.equal(canBypassCommercialSurfaceFreeze("production"), false);
    } finally {
      restoreWindow();
    }
  });

  it("development environment requires local flag for effective developer mode", () => {
    const restoreEmpty = installWindowStorage();
    try {
      assert.equal(isDeveloperEnvironmentAllowed("development"), true);
      assert.equal(isHomeDeveloperMode("development"), false);
      assert.equal(canBypassCommercialSurfaceFreeze("development"), false);
    } finally {
      restoreEmpty();
    }

    const restoreFlag = installWindowStorage({ [HOME_DEVELOPER_MODE_KEY]: "1" });
    try {
      assert.equal(isHomeDeveloperMode("development"), true);
      assert.equal(canBypassCommercialSurfaceFreeze("development"), true);
    } finally {
      restoreFlag();
    }
  });

  it("local flag alone does not imply environment allowance in production", () => {
    const restoreWindow = installWindowStorage({ [HOME_DEVELOPER_MODE_KEY]: "1" });
    try {
      assert.equal(canBypassCommercialSurfaceFreeze("production"), false);
    } finally {
      restoreWindow();
    }
  });
});
