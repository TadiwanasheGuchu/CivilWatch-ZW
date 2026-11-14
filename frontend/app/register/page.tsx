import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthPage } from "@/features/authentication/auth-page";
import { RegisterForm } from "@/features/authentication/register-form";

export const metadata: Metadata = { title: "Create an account" };

export default function RegisterPage() {
  return (
    <AuthPage
      title="Create an account"
      intro="With an account you can report infrastructure problems and see what your council does about them."
    >
      <Suspense>
        <RegisterForm />
      </Suspense>
    </AuthPage>
  );
}
