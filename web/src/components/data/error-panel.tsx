type ErrorPanelProps = {
  title?: string;
  message: string;
};

export function ErrorPanel({
  title = "Failed to load data",
  message,
}: ErrorPanelProps) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive"
    >
      <p className="font-medium">{title}</p>
      <p className="mt-1 text-destructive/90">{message}</p>
    </div>
  );
}
