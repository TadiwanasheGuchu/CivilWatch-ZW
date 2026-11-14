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
import { ApiError, errorMessage } from "@/lib/api-client";
import { applyServerFieldErrors } from "@/lib/form-errors";

import { register } from "./api";
import { safeNextPath } from "./redirect";
import { PASSWORD_MIN_LENGTH, registerSchema, type RegisterValues } from "./schemas";
import { useSetSession } from "./use-session";

export function RegisterForm() {
  const router = useRouter();
  const next = safeNextPath(useSearchParams().get("next"));
  const setSession = useSetSession();
  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: "", email: "", password: "" },
  });
  const mutation = useMutation({
    mutationFn: register,
    onSuccess: (session) => {
      setSession(session);
      router.replace(next);
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === "conflict") {
        form.setError("email", { type: "server", message: error.message });
        return;
      }
      applyServerFieldErrors(error, form.setError, ["full_name", "email", "password"]);
    },
  });
  const { errors } = form.formState;
  const showBanner =
    mutation.isError &&
    !(mutation.error instanceof ApiError && ["conflict", "validation_error"].includes(mutation.error.code));

  return (
    <form noValidate onSubmit={form.handleSubmit((values) => mutation.mutate(values))} className="space-y-4">
      {showBanner ? <Alert tone="error">{errorMessage(mutation.error)}</Alert> : null}
      <Field label="Full name" error={errors.full_name?.message}>
        <Input autoComplete="name" autoCapitalize="words" {...form.register("full_name")} />
      </Field>
      <Field label="Email address" error={errors.email?.message}>
        <Input type="email" autoComplete="email" inputMode="email" {...form.register("email")} />
      </Field>
      <Field
        label="Password"
        hint={`At least ${PASSWORD_MIN_LENGTH} characters. A short phrase is easier to remember.`}
        error={errors.password?.message}
      >
        <PasswordInput autoComplete="new-password" {...form.register("password")} />
      </Field>
      <Button type="submit" size="lg" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending ? "Creating account…" : "Create account"}
      </Button>
      <p className="text-center text-sm text-navy-soft">
        Already have an account?{" "}
        <Link
          href={`/sign-in?next=${encodeURIComponent(next)}`}
          className="font-medium text-teal underline underline-offset-2"
        >
          Sign in
        </Link>
      </p>
    </form>
  );
}
