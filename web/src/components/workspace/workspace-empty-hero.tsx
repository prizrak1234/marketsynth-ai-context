"use client";

type Props = {
  onCreateProject?: () => void;
};

export function WorkspaceEmptyHero({ onCreateProject }: Props) {
  return (
    <section
      className="rounded-xl border px-6 py-12 text-center sm:px-10"
      style={{
        borderColor: "var(--ms-border-default)",
        background:
          "radial-gradient(ellipse 80% 60% at 50% 0%, color-mix(in srgb, var(--brand-blue) 18%, transparent), transparent 55%), var(--ms-bg-elevated)",
      }}
    >
      <h2
        className="text-2xl font-semibold tracking-tight sm:text-3xl"
        style={{ color: "var(--ms-text-primary)" }}
      >
        Начать исследование новой идеи
      </h2>
      <p
        className="mx-auto mt-3 max-w-xl text-sm leading-relaxed"
        style={{ color: "var(--ms-text-secondary)" }}
      >
        Создайте проект — агентство запустит исследование рынка, конкурентов, аудитории и рисков
        до вынесения вердикта.
      </p>
      <button
        type="button"
        onClick={onCreateProject}
        className="mt-8 inline-flex rounded-md px-6 py-3 text-sm font-semibold"
        style={{
          background: "var(--ms-brand-primary)",
          color: "var(--ms-text-primary)",
        }}
      >
        Создать проект
      </button>
    </section>
  );
}
