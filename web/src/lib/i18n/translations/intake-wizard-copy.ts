/** Customer-facing copy for the 7-step intake wizard (Slice E). */

export const intakeWizardCopyRu = {
  shell: {
    eyebrow: "Бриф проекта",
    title: "Проверка идеи перед исследованием",
    subtitle:
      "Семь шагов — чтобы Marketsynth понял вашу идею так же чётко, как вы.",
    stepsNav: "Шаги брифа",
    stepProgress: "Шаг {current} из {total}",
    autosaveHint: "Изменения сохраняются автоматически.",
    back: "Назад",
    backToWorkspace: "К Workspace",
    next: "Далее",
    validationBanner: "Заполните обязательные поля перед следующим шагом.",
    loadingDraft: "Загрузка черновика…",
  },
  autosave: {
    saving: "Сохраняем…",
    saved: "Изменения сохранены",
    error: "Не удалось сохранить изменения",
  },
  field: {
    requiredMarker: "Обязательно",
    optionalMarker: "Дополнительно, если известно",
  },
  money: {
    modeExact: "Точное",
    modeRange: "Диапазон",
    modeUnknown: "Пока неизвестно",
    unknownValid: "Явно неизвестно — это валидный ввод, не ошибка.",
    markUnknown: "Пометить как «пока неизвестно»",
    from: "От",
    to: "До",
  },
  steps: {
    basics: {
      title: "О проекте",
      description:
        "Базовый контекст идеи. Обязательные поля нужны, чтобы Marketsynth понимал, что именно исследовать.",
    },
    product: {
      title: "Продукт или услуга",
      description:
        "Что именно продаётся и какую проблему закрывает. Приблизительные ответы допустимы — это гипотезы, не финальный факт.",
    },
    market: {
      title: "Рынок и конкуренция",
      description:
        "Даже если рынок пока неизвестен, укажите гипотезы. Marketsynth проверит их по открытым источникам.",
      competitorsHiddenHint:
        "Поля конкурентов скрыты, потому что вы отметили «конкуренты неизвестны». Данные сохранены.",
    },
    audience: {
      title: "Целевая аудитория",
      description:
        "Это предварительное описание. Исследование подтвердит или скорректирует сегменты.",
    },
    economics: {
      title: "Экономика и ограничения",
      description:
        "Приблизительные значения допустимы. Они нужны для проверки экономических ограничений идеи.",
    },
    materials: {
      title: "Материалы",
      description:
        "Ссылки и материалы помогают исследованию, но их можно добавить позже.",
      localDraftNotice:
        "Ссылки и заметки сохраняются в черновике брифа. Загрузка файлов на сервер пока недоступна.",
      addMaterialLabel: "Добавить заметку о материале",
      addMaterialHint: "Запись сохранится в черновике — файл не загружается.",
      itemSavedLocally: "В черновике",
      emptyList: "Материалов пока нет — это допустимо.",
    },
    review: {
      title: "Обзор и готовность",
      description:
        "Проверьте, что мы правильно поняли вашу идею. После запуска Marketsynth соберёт доказательства и подготовит вывод.",
    },
  },
  review: {
    readinessTitle: "Статус готовности",
    clarificationsTitle: "Что стоит уточнить",
    startResearch: "Запустить исследование",
    starting: "Запуск…",
    backEdit: "Вернуться и изменить",
    notReadyNotice:
      "Дополните обязательные поля брифа, прежде чем запускать исследование.",
    mockModeNotice: "Для реального исследования нужен backend-режим интеграции.",
    submitError:
      "Не удалось запустить исследование. Попробуйте ещё раз или вернитесь к правкам брифа.",
    sections: {
      project: "Проект",
      product: "Продукт или услуга",
      market: "Рынок и география",
      audience: "Аудитория",
      economics: "Экономика",
      materials: "Материалы",
    },
  },
  optionalSection: {
    title: "Дополнительно, если известно",
    toggleShow: "Показать дополнительные поля",
    toggleHide: "Скрыть дополнительные поля",
  },
} as const;

export const intakeWizardCopyEn = {
  shell: {
    eyebrow: "Project brief",
    title: "Validate your idea before research",
    subtitle:
      "Seven steps so Marketsynth understands your idea as clearly as you do.",
    stepsNav: "Brief steps",
    stepProgress: "Step {current} of {total}",
    autosaveHint: "Changes save automatically.",
    back: "Back",
    backToWorkspace: "Back to workspace",
    next: "Next",
    validationBanner: "Complete required fields before the next step.",
    loadingDraft: "Loading draft…",
  },
  autosave: {
    saving: "Saving…",
    saved: "Changes saved",
    error: "Could not save changes",
  },
  field: {
    requiredMarker: "Required",
    optionalMarker: "Optional if known",
  },
  money: {
    modeExact: "Exact",
    modeRange: "Range",
    modeUnknown: "Unknown for now",
    unknownValid: "Explicitly unknown is valid input, not an error.",
    markUnknown: "Mark as unknown for now",
    from: "From",
    to: "To",
  },
  steps: {
    basics: {
      title: "About the project",
      description:
        "Core context for your idea. Required fields tell Marketsynth what to research.",
    },
    product: {
      title: "Product or service",
      description:
        "What you sell and which problem it solves. Approximate answers are fine — these are hypotheses, not final facts.",
    },
    market: {
      title: "Market and competition",
      description:
        "Even if the market is unclear, share hypotheses. Marketsynth will check them against open sources.",
      competitorsHiddenHint:
        "Competitor fields are hidden because you marked competitors as unknown. Your data is preserved.",
    },
    audience: {
      title: "Target audience",
      description:
        "This is a preliminary description. Research will confirm or refine segments.",
    },
    economics: {
      title: "Economics and constraints",
      description:
        "Approximate values are acceptable. They help test the economic constraints of your idea.",
    },
    materials: {
      title: "Materials",
      description: "Links and materials help research, but you can add them later.",
      localDraftNotice:
        "Links and notes are saved in your brief draft. File upload to the server is not available yet.",
      addMaterialLabel: "Add a material note",
      addMaterialHint: "Saved to the draft only — no file upload.",
      itemSavedLocally: "In draft",
      emptyList: "No materials yet — that is acceptable.",
    },
    review: {
      title: "Review and readiness",
      description:
        "Confirm we understood your idea. After launch, Marketsynth will gather evidence and prepare a verdict.",
    },
  },
  review: {
    readinessTitle: "Readiness status",
    clarificationsTitle: "Worth clarifying",
    startResearch: "Start research",
    starting: "Starting…",
    backEdit: "Back to edit",
    notReadyNotice: "Complete required brief fields before starting research.",
    mockModeNotice: "Real research requires backend integration mode.",
    submitError:
      "Could not start research. Try again or return to edit the brief.",
    sections: {
      project: "Project",
      product: "Product or service",
      market: "Market and geography",
      audience: "Audience",
      economics: "Economics",
      materials: "Materials",
    },
  },
  optionalSection: {
    title: "Optional if known",
    toggleShow: "Show optional fields",
    toggleHide: "Hide optional fields",
  },
} as const;
