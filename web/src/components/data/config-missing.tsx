type ConfigMissingProps = {
  title: string;
  lines?: string[];
  /** developer = show env hints; customer = safe message only */
  variant?: "developer" | "customer";
};

export function ConfigMissing({
  title,
  lines = [],
  variant = "developer",
}: ConfigMissingProps) {
  if (variant === "customer") {
    return (
      <div
        role="alert"
        className="rounded-lg border px-4 py-6 text-sm"
        style={{
          borderColor: "var(--ms-border-default)",
          background: "var(--ms-bg-surface)",
        }}
        data-testid="config-missing-customer"
      >
        <p className="font-medium">{title}</p>
      </div>
    );
  }

  return (
    <div
      role="alert"
      className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm"
      data-testid="config-missing-developer"
    >
      <p className="font-medium text-amber-950 dark:text-amber-100">{title}</p>
      {lines.length > 0 ? (
        <ul className="mt-2 list-inside list-disc space-y-1 text-muted-foreground">
          {lines.map((line) => (
            <li key={line}>
              <code className="text-xs">{line}</code>
            </li>
          ))}
        </ul>
      ) : null}
      <p className="mt-3 text-xs text-muted-foreground">
        Copy <code className="text-xs">web/.env.example</code> to{" "}
        <code className="text-xs">web/.env.local</code> and restart{" "}
        <code className="text-xs">npm run dev</code>.
      </p>
    </div>
  );
}

export function ApiKeyMissing() {
  return (
    <ConfigMissing
      variant="developer"
      title="API key missing"
      lines={["NEXT_PUBLIC_BOTFAZER_API_KEY=bfz_your_key_here"]}
    />
  );
}

export function ProjectIdMissing() {
  return (
    <ConfigMissing
      variant="developer"
      title="Project ID missing"
      lines={["NEXT_PUBLIC_BOTFAZER_PROJECT_ID=your-project-uuid"]}
    />
  );
}

export function CustomerApiUnavailable() {
  return (
    <ConfigMissing
      variant="customer"
      title="Сервис временно недоступен"
    />
  );
}
