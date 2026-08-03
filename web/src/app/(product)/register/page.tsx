import { Suspense } from "react";
import { AuthProvider } from "@/lib/auth/auth-context";
import { RegisterForm } from "@/components/auth/register-form";

export default function RegisterPage() {
  return (
    <AuthProvider>
      <Suspense fallback={<div className="p-8 text-sm">Загрузка…</div>}>
        <RegisterForm />
      </Suspense>
    </AuthProvider>
  );
}
