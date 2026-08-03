import { Suspense } from "react";
import { AuthProvider } from "@/lib/auth/auth-context";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";

export default function ResetPasswordPage() {
  return (
    <AuthProvider>
      <Suspense fallback={<div className="p-8 text-sm">Загрузка…</div>}>
        <ResetPasswordForm />
      </Suspense>
    </AuthProvider>
  );
}
