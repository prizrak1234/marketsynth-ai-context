/** H2.8C — Image generation composer draft (separate from clarification chat). */

export type IdentityFidelity = "maximum" | "high" | "balanced";
export type StyleFreedom = "low" | "medium" | "high";

export type ImageComposerSubjectType =
  | "person"
  | "product"
  | "logo"
  | "brand"
  | "object"
  | "style"
  | "environment"
  | "other";

export const PERSON_PRESERVE_OPTIONS = [
  { id: "facial_geometry", labelKey: "home.preserveFacialGeometry", defaultOn: true },
  { id: "face_shape", labelKey: "home.preserveFaceShape", defaultOn: true },
  { id: "eye_shape", labelKey: "home.preserveEyeShape", defaultOn: true },
  { id: "eye_color", labelKey: "home.preserveEyeColor", defaultOn: false },
  { id: "nose_shape", labelKey: "home.preserveNoseShape", defaultOn: true },
  { id: "lip_shape", labelKey: "home.preserveLipShape", defaultOn: true },
  { id: "skin_tone", labelKey: "home.preserveSkinTone", defaultOn: true },
  { id: "apparent_age", labelKey: "home.preserveAge", defaultOn: true },
  { id: "distinctive_features", labelKey: "home.preserveDistinctive", defaultOn: true },
  { id: "hair_color", labelKey: "home.preserveHairColor", defaultOn: false },
  { id: "hair_style", labelKey: "home.preserveHairStyle", defaultOn: false },
  { id: "body_proportions", labelKey: "home.preserveBody", defaultOn: false },
] as const;

export const PERSON_ALLOWED_OPTIONS = [
  { id: "clothing", labelKey: "home.allowClothing", defaultOn: true },
  { id: "pose", labelKey: "home.allowPose", defaultOn: true },
  { id: "facial_expression", labelKey: "home.allowExpression", defaultOn: false },
  { id: "lighting", labelKey: "home.allowLighting", defaultOn: true },
  { id: "background", labelKey: "home.allowBackground", defaultOn: true },
  { id: "environment", labelKey: "home.allowEnvironment", defaultOn: true },
  { id: "artistic_style", labelKey: "home.allowArtisticStyle", defaultOn: true },
  { id: "camera_angle", labelKey: "home.allowCameraAngle", defaultOn: false },
  { id: "hair_style", labelKey: "home.allowHairStyle", defaultOn: false },
  { id: "hair_color", labelKey: "home.allowHairColor", defaultOn: false },
  { id: "apparent_age", labelKey: "home.allowAge", defaultOn: false },
] as const;

export const PERSON_PURPOSE_OPTIONS = [
  { value: "other", labelKey: "home.refPurposeOther" },
  { value: "face_front", labelKey: "home.refPurposeFaceFront" },
  { value: "face_three_quarter", labelKey: "home.refPurposeFaceThreeQuarter" },
  { value: "face_profile", labelKey: "home.refPurposeFaceProfile" },
  { value: "face_closeup", labelKey: "home.refPurposeFaceCloseup" },
  { value: "face_reference", labelKey: "home.refPurposeFace" },
  { value: "half_body", labelKey: "home.refPurposeHalfBody" },
  { value: "full_body", labelKey: "home.refPurposeFullBody" },
  { value: "body_reference", labelKey: "home.refPurposeBody" },
  { value: "hair", labelKey: "home.refPurposeHair" },
  { value: "clothing", labelKey: "home.refPurposeClothing" },
  { value: "outfit_reference", labelKey: "home.refPurposeOutfit" },
  { value: "pose", labelKey: "home.refPurposePose" },
  { value: "pose_reference", labelKey: "home.refPurposePoseRef" },
  { value: "style_reference", labelKey: "home.refPurposeStyle" },
  { value: "composition_reference", labelKey: "home.refPurposeComposition" },
  { value: "background_reference", labelKey: "home.refPurposeBackground" },
] as const;

export type ImageGenerationComposerDraft = {
  prompt: string;
  referenceSetId: string | null;
  subjectType: ImageComposerSubjectType;
  preserveTraits: string[];
  allowedChanges: string[];
  identityFidelity: IdentityFidelity;
  styleFreedom: StyleFreedom;
  primaryReferenceId: string | null;
  referenceCount: number;
  uploading: boolean;
  consent: boolean;
};

export type GenerationReadiness = {
  ready: boolean;
  title: string;
  lines: string[];
  blockingReason: string | null;
};

export function defaultPreserveTraits(): string[] {
  return PERSON_PRESERVE_OPTIONS.filter((o) => o.defaultOn).map((o) => o.id);
}

export function defaultAllowedChanges(): string[] {
  return PERSON_ALLOWED_OPTIONS.filter((o) => o.defaultOn).map((o) => o.id);
}

export function styleFreedomForFidelity(fidelity: IdentityFidelity): StyleFreedom {
  if (fidelity === "maximum") return "low";
  if (fidelity === "high") return "medium";
  return "medium";
}

export function evaluateImageGenerationReadiness(
  draft: ImageGenerationComposerDraft,
): GenerationReadiness {
  const lines: string[] = [];
  const promptOk = draft.prompt.trim().length >= 40;
  const refsOk = draft.referenceCount >= 1 && !draft.uploading;
  const primaryOk = Boolean(draft.primaryReferenceId) || draft.referenceCount === 0;
  const traitsOk = draft.preserveTraits.length >= 1;
  const consentOk = draft.consent || draft.referenceCount === 0;

  lines.push(promptOk ? "Промпт: заполнен" : "Промпт: слишком короткий");
  lines.push(`Референсов: ${draft.referenceCount}`);
  lines.push(
    draft.primaryReferenceId
      ? "Основной референс: выбран"
      : "Основной референс: не выбран",
  );
  lines.push(
    draft.identityFidelity === "maximum"
      ? "Сходство: максимальное"
      : draft.identityFidelity === "high"
        ? "Сходство: высокое"
        : "Сходство: сбалансированное",
  );
  lines.push(`Используемые признаки: ${draft.preserveTraits.length}`);
  lines.push(
    draft.uploading ? "Загрузка файлов: в процессе" : "Загрузка файлов: завершена",
  );

  if (draft.uploading) {
    return {
      ready: false,
      title: "Дождитесь окончания загрузки",
      lines,
      blockingReason: "Дождитесь окончания загрузки файлов.",
    };
  }
  if (!promptOk) {
    return {
      ready: false,
      title: "Нужен более полный промпт",
      lines,
      blockingReason: "Опишите сцену подробнее (не меньше нескольких предложений).",
    };
  }
  if (!refsOk) {
    return {
      ready: false,
      title: "Добавьте референсы",
      lines,
      blockingReason: "Загрузите хотя бы один референс для сохранения внешности.",
    };
  }
  if (!consentOk) {
    return {
      ready: false,
      title: "Подтвердите согласие",
      lines,
      blockingReason: "Подтвердите право использовать изображения.",
    };
  }
  if (!primaryOk && draft.subjectType === "person") {
    return {
      ready: false,
      title: "Нужно выбрать основной референс лица",
      lines,
      blockingReason: "Выберите основной референс лица для максимального сходства.",
    };
  }
  if (!traitsOk && draft.subjectType === "person") {
    return {
      ready: false,
      title: "Отметьте, что сохранить",
      lines,
      blockingReason: "Выберите хотя бы один признак для сохранения.",
    };
  }

  return {
    ready: true,
    title: "Готово к генерации",
    lines,
    blockingReason: null,
  };
}

export function buildImagePromptSummary(draft: ImageGenerationComposerDraft): string[] {
  const items: string[] = [];
  const p = draft.prompt.toLowerCase();
  if (/взросл|adult|женщин|мужчин|девушк|person/.test(p)) {
    items.push("взрослый персонаж");
  }
  if (/тёмн|темн|dark\s*fantasy|фэнтези|fantasy/.test(p)) {
    items.push("тёмное фэнтези");
  }
  if (/кинематограф|cinematic|портрет|portrait/.test(p)) {
    items.push("кинематографический портрет");
  }
  if (/чёрн|черн|красн|black|red/.test(p)) {
    items.push("чёрно-красная палитра");
  }
  if (draft.preserveTraits.includes("facial_geometry")) {
    items.push("сохранение лица и возраста");
  }
  const allowed = draft.allowedChanges
    .filter((x) => ["clothing", "lighting", "background", "pose"].includes(x))
    .slice(0, 3);
  if (allowed.length) {
    items.push(`разрешено менять: ${allowed.join(", ")}`);
  }
  items.push(`используется ${draft.referenceCount} референсов`);
  return items;
}
