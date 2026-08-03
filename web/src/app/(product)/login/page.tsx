import { Suspense } from "react";
import { AuthProvider } from "@/lib/auth/auth-context";
import { LoginForm } from "@/components/auth/login-form";

export default function LoginPage() {
  return (
    <AuthProvider>
      <Suspense fallback={<div className="p-8 text-sm">Загрузка…</div>}>
        <LoginForm />
      </Suspense>
    </AuthProvider>
  );
}
