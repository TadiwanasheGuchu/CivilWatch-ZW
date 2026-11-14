"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { errorMessage } from "@/lib/api-client";
import { applyServerFieldErrors } from "@/lib/form-errors";

import { updateProfile } from "./api";
import { profileSchema, type ProfileValues } from "./schemas";
import type { SessionData } from "./types";
import { useSetSession } from "./use-session";

export function ProfileForm({ session }: { session: SessionData }) {
  const setSession = useSetSession();
  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: session.user.full_name },
  });
  const mutation = useMutation({
    mutationFn: (values: ProfileValues) => updateProfile(values, session.csrf_token),
    onSuccess: (user) => {
      setSession({ ...session, user });
      form.reset({ full_name: user.full_name });
    },
    onError: (error) => applyServerFieldErrors(error, form.setError, ["full_name"]),
  });

  return (
    <form noValidate onSubmit={form.handleSubmit((values) => mutation.mutate(values))} className="space-y-4">
      <Field label="Full name" error={form.formState.errors.full_name?.message}>
        <Input autoComplete="name" autoCapitalize="words" {...form.register("full_name")} />
      </Field>
      <Field label="Email address" hint="Your email address cannot be changed yet.">
        <Input type="email" value={session.user.email} readOnly disabled />
      </Field>
      {mutation.isSuccess && !form.formState.isDirty ? (
        <Alert tone="success">Your name has been updated.</Alert>
      ) : null}
      {mutation.isError && Object.keys(form.formState.errors).length === 0 ? (
        <Alert tone="error">{errorMessage(mutation.error)}</Alert>
      ) : null}
      <Button type="submit" disabled={mutation.isPending || !form.formState.isDirty}>
        {mutation.isPending ? "Saving…" : "Save name"}
      </Button>
    </form>
  );
}
