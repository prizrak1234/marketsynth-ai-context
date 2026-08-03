type PageHeaderProps = {
  title: string;
  description?: React.ReactNode;
};

export function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <header className="border-b border-border pb-4">
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      {description ? (
        <div className="mt-1 text-sm text-muted-foreground">{description}</div>
      ) : null}
    </header>
  );
}