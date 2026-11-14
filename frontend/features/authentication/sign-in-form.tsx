"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { errorMessage } from "@/lib/api-client";
import { applyServerFieldErrors } from "@/lib/form-errors";

import { signIn } from "./api";
import { safeNextPath } from "./redirect";
import { signInSchema, type SignInValues } from "./schemas";
import { useSetSession } from "./use-session";

export function SignInForm() {
  const router = useRouter();
  const next = safeNextPath(useSearchParams().get("next"));
  const setSession = useSetSession();
  const form = useForm<SignInValues>({
    resolver: zodResolver(signInSchema),
    defaultValues: { email: "", password: "" },
  });
  const mutation = useMutation({
    mutationFn: signIn,
    onSuccess: (session) => {
      setSession(session);
      router.replace(next);
    },
    onError: (error) => {
      applyServerFieldErrors(error, form.setError, ["email", "password"]);
      form.resetField("password");
    },
  });
  const { errors } = form.formState;

  return (
    <form noValidate onSubmit={form.handleSubmit((values) => mutation.mutate(values))} className="space-y-4">
      {mutation.isError ? <Alert tone="error">{errorMessage(mutation.error)}</Alert> : null}
      <Field label="Email address" error={errors.email?.message}>
        <Input type="email" autoComplete="email" inputMode="email" {...form.register("email")} />
      </Field>
      <Field label="Password" error={errors.password?.message}>
        <PasswordInput autoComplete="current-password" {...form.register("password")} />
      </Field>
      <Button type="submit" size="lg" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending ? "Signing in…" : "Sign in"}
      </Button>
      <p className="text-center text-sm text-navy-soft">
        New to CivicWatch?{" "}
        <Link
          href={`/register?next=${encodeURIComponent(next)}`}
          className="font-medium text-teal underline underline-offset-2"
        >
          Create an account
        </Link>
      </p>
    </form>
  );
}
