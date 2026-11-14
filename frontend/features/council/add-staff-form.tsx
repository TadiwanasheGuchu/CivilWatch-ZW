"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { ApiError, errorMessage } from "@/lib/api-client";
import { applyServerFieldErrors } from "@/lib/form-errors";

import { addMember, councilKeys } from "./api";
import { COUNCIL_ROLES, ROLE_DESCRIPTIONS, ROLE_LABELS } from "./labels";

const schema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Enter the person's email address.")
    .pipe(z.email("Enter a valid email address.")),
  role: z.enum(COUNCIL_ROLES, { message: "Choose a role." }),
});
type Values = z.infer<typeof schema>;

export function AddStaffForm({ councilId, csrfToken }: { councilId: string; csrfToken: string }) {
  const queryClient = useQueryClient();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", role: "verification_officer" },
  });
  const mutation = useMutation({
    mutationFn: (values: Values) => addMember(councilId, values, csrfToken),
    onSuccess: () => {
      form.reset({ email: "", role: form.getValues("role") });
      void queryClient.invalidateQueries({ queryKey: councilKeys.membersRoot(councilId) });
      void queryClient.invalidateQueries({ queryKey: ["council", councilId, "audit"] });
    },
    onError: (error) => {
      if (error instanceof ApiError && (error.status === 404 || error.status === 409)) {
        form.setError("email", { type: "server", message: error.message });
        return;
      }
      applyServerFieldErrors(error, form.setError, ["email", "role"]);
    },
  });
  const { errors } = form.formState;
  const selectedRole = useWatch({ control: form.control, name: "role" });

  return (
    <form noValidate onSubmit={form.handleSubmit((values) => mutation.mutate(values))} className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <Field
          label="Email address"
          hint="The person must already have a CivicWatch account."
          error={errors.email?.message}
        >
          <Input type="email" inputMode="email" autoComplete="off" {...form.register("email")} />
        </Field>
        <Field label="Role" hint={ROLE_DESCRIPTIONS[selectedRole]} error={errors.role?.message}>
          <Select {...form.register("role")}>
            {COUNCIL_ROLES.map((role) => (
              <option key={role} value={role}>
                {ROLE_LABELS[role]}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      {mutation.isSuccess ? (
        <Alert tone="success">
          {mutation.data.full_name} was added as {ROLE_LABELS[mutation.data.role]}.
        </Alert>
      ) : null}
      {mutation.isError && !errors.email && !errors.role ? (
        <Alert tone="error">{errorMessage(mutation.error)}</Alert>
      ) : null}
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Adding…" : "Add staff member"}
      </Button>
    </form>
  );
}
