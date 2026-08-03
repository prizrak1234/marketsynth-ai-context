type PlaceholderPanelProps = {
  title: string;
  apiHint: string;
  children?: React.ReactNode;
};

export function PlaceholderPanel({ title, apiHint, children }: PlaceholderPanelProps) {
  return (
    <section className="rounded-lg border border-dashed border-border bg-muted/20 p-4">
      <h2 className="text-sm font-medium">{title}</h2>
      <p className="mt-1 font-mono text-xs text-muted-foreground">{apiHint}</p>
      {children ? <div className="mt-3 text-sm text-muted-foreground">{children}</div> : null}
    </section>
  );
}
