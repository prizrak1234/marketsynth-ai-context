import { Suspense } from "react";
import { AuthProvider } from "@/lib/auth/auth-context";
import { ActivateInviteForm } from "@/components/auth/activate-invite-form";

export default function ActivateInvitePage() {
  return (
    <AuthProvider>
      <Suspense fallback={<div className="p-8 text-sm">Загрузка…</div>}>
        <ActivateInviteForm />
      </Suspense>
    </AuthProvider>
  );
}
