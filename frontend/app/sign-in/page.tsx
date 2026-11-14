import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthPage } from "@/features/authentication/auth-page";
import { SignInForm } from "@/features/authentication/sign-in-form";

export const metadata: Metadata = { title: "Sign in" };

export default function SignInPage() {
  return (
    <AuthPage title="Sign in" intro="Sign in to report problems and follow their progress.">
      <Suspense>
        <SignInForm />
      </Suspense>
    </AuthPage>
  );
}
