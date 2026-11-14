"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { PasswordInput } from "@/components/ui/password-input";
import { ApiError, errorMessage } from "@/lib/api-client";
import { applyServerFieldErrors } from "@/lib/form-errors";

import { changePassword } from "./api";
import { changePasswordSchema, PASSWORD_MIN_LENGTH, type ChangePasswordValues } from "./schemas";
import type { SessionData } from "./types";

export function ChangePasswordForm({ session }: { session: SessionData }) {
  const form = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: "", new_password: "" },
  });
  const mutation = useMutation({
    mutationFn: (values: ChangePasswordValues) => changePassword(values, session.csrf_token),
    onSuccess: () => form.reset(),
    onError: (error) => {
      if (error instanceof ApiError && error.code === "invalid_current_password") {
        form.setError("current_password", { type: "server", message: error.message });
        return;
      }
      applyServerFieldErrors(error, form.setError, ["current_password", "new_password"]);
    },
  });
  const { errors } = form.formState;
  const fieldError = Boolean(errors.current_password || errors.new_password);

  return (
    <form noValidate onSubmit={form.handleSubmit((values) => mutation.mutate(values))} className="space-y-4">
      <Field label="Current password" error={errors.current_password?.message}>
        <PasswordInput autoComplete="current-password" {...form.register("current_password")} />
      </Field>
      <Field
        label="New password"
        hint={`At least ${PASSWORD_MIN_LENGTH} characters.`}
        error={errors.new_password?.message}
      >
        <PasswordInput autoComplete="new-password" {...form.register("new_password")} />
      </Field>
      {mutation.isSuccess ? (
        <Alert tone="success" title="Password changed">
          You have been signed out on every other device.
        </Alert>
      ) : null}
      {mutation.isError && !fieldError ? <Alert tone="error">{errorMessage(mutation.error)}</Alert> : null}
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Changing…" : "Change password"}
      </Button>
    </form>
  );
}
