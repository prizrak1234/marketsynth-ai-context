import { Suspense } from "react";
import { AuthProvider } from "@/lib/auth/auth-context";
import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";

export default function ForgotPasswordPage() {
  return (
    <AuthProvider>
      <Suspense fallback={<div className="p-8 text-sm">Загрузка…</div>}>
        <ForgotPasswordForm />
      </Suspense>
    </AuthProvider>
  );
}
