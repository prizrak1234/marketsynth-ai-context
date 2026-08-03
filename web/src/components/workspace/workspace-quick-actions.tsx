"use client";

type Props = {
  onCreateProject?: () => void;
  onImport?: () => void;
  onContinue?: () => void;
  onKnowledge?: () => void;
};

const ACTIONS: Array<{
  key: keyof Props;
  label: string;
  primary?: boolean;
}> = [
  { key: "onCreateProject", label: "Создать проект", primary: true },
  { key: "onImport", label: "Импортировать материалы" },
  { key: "onContinue", label: "Продолжить исследование" },
  { key: "onKnowledge", label: "Открыть Knowledge" },
];

export function WorkspaceQuickActions(props: Props) {
  return (
    <section
      className="rounded-xl border p-5"
      style={{
        borderColor: "var(--ms-border-default)",
        background: "var(--ms-bg-surface)",
      }}
    >
      <h2
        className="text-sm font-semibold uppercase tracking-[0.14em]"
        style={{ color: "var(--ms-brand-secondary)" }}
      >
        Quick Actions
      </h2>
      <div className="mt-4 flex flex-wrap gap-2">
        {ACTIONS.map((a) => {
          const handler = props[a.key];
          return (
            <button
              key={a.key}
              type="button"
              onClick={handler}
              className="rounded-md px-3 py-2 text-xs font-semibold"
              style={
                a.primary
                  ? {
                      background: "var(--ms-brand-primary)",
                      color: "var(--ms-text-primary)",
                    }
                  : {
                      background: "var(--ms-bg-elevated)",
                      color: "var(--ms-text-secondary)",
                      boxShadow: "inset 0 0 0 1px var(--ms-border-default)",
                    }
              }
            >
              {a.label}
            </button>
          );
        })}
      </div>
      <p className="mt-3 text-[11px]" style={{ color: "var(--ms-text-muted)" }}>
        Действия пока локальные (mock). Backend wiring — в следующих фазах.
      </p>
    </section>
  );
}
