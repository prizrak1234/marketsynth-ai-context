import { AppSidebar } from "@/components/layout/app-sidebar";

type AppShellProps = {
  children: React.ReactNode;
};

/** App chrome uses Marketsynth brand canvas (logo-aligned dark field). */
export function AppShell({ children }: AppShellProps) {
  return (
    <div
      className="flex min-h-screen"
      style={{
        background: "var(--ms-bg-canvas)",
        color: "var(--ms-text-primary)",
      }}
    >
      <AppSidebar />
      <main className="flex min-w-0 flex-1 flex-col">
        <div className="mx-auto w-full max-w-6xl flex-1 p-6">{children}</div>
      </main>
    </div>
  );
}
