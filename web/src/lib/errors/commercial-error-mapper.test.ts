import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { ApiError } from "@/lib/api/client";

import {
  isInternalErrorCode,
  mapCommercialError,
} from "./commercial-error-mapper";

const identityT = (key: string) => key;

describe("isInternalErrorCode", () => {
  it("detects snake_case domain codes", () => {
    assert.equal(isInternalErrorCode("research_idempotency_key_required"), true);
    assert.equal(isInternalErrorCode("context_missing"), true);
  });

  it("rejects commercial sentences", () => {
    assert.equal(isInternalErrorCode("Не удалось повторить"), false);
  });
});

describe("mapCommercialError", () => {
  it("never returns raw idempotency code", () => {
    const view = mapCommercialError(
      new ApiError(
        "research_idempotency_key_required",
        409,
        { detail: "research_idempotency_key_required" },
        "research_idempotency_key_required",
      ),
      identityT,
      "research",
    );
    assert.equal(view.message.includes("research_idempotency_key_required"), false);
    assert.equal(view.message.includes("idempotency_key"), false);
    assert.ok(view.message.length > 0);
  });

  it("uses safe_message from envelope when commercial", () => {
    const view = mapCommercialError(
      new ApiError(
        "ignored",
        409,
        { safe_message: "Не удалось подтвердить данные.", error_code: "x" },
        "x",
      ),
      identityT,
      "research",
    );
    assert.equal(view.message, "Не удалось подтвердить данные.");
  });

  it("maps 401 without raw code", () => {
    const view = mapCommercialError(
      new ApiError("authentication_required", 401, {}, "authentication_required"),
      identityT,
    );
    assert.equal(view.message.includes("authentication_required"), false);
  });

  it("maps 500 without status text", () => {
    const view = mapCommercialError(
      new ApiError("internal", 500, {}, "internal_error"),
      identityT,
    );
    assert.equal(view.message.includes("500"), false);
    assert.equal(view.message.includes("internal_error"), false);
  });

  it("maps 403 without raw code", () => {
    const view = mapCommercialError(
      new ApiError("forbidden", 403, {}, "forbidden"),
      identityT,
    );
    assert.equal(view.message.includes("forbidden"), false);
  });

  it("maps 404 without raw code", () => {
    const view = mapCommercialError(
      new ApiError("not_found", 404, {}, "not_found"),
      identityT,
    );
    assert.equal(view.message.includes("not_found"), false);
  });

  it("maps context missing without raw code", () => {
    const view = mapCommercialError(
      new ApiError("analysis_context_required", 409, {}, "analysis_context_required"),
      identityT,
      "research",
    );
    assert.equal(view.message.includes("analysis_context_required"), false);
  });

  it("maps validation envelope without exposing error_code", () => {
    const view = mapCommercialError(
      new ApiError("", 422, { error_code: "validation_error" }, "validation_error"),
      identityT,
    );
    assert.equal(view.message.includes("validation_error"), false);
  });
});
