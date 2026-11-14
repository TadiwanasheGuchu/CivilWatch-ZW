"use client";

import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

import type { StepProps } from "./step-props";

export function DetailsStep({ draft, update, errors }: StepProps) {
  return (
    <div className="space-y-4">
      <Field label="Short title" hint="For example: Deep pothole outside the clinic" error={errors.title}>
        <Input
          value={draft.title}
          maxLength={120}
          autoCapitalize="sentences"
          onChange={(event) => update({ title: event.target.value })}
        />
      </Field>
      <Field
        label="What is the problem?"
        hint={`Size, danger, how long it has been there. ${draft.description.trim().length}/2000`}
        error={errors.description}
      >
        <Textarea
          value={draft.description}
          maxLength={2000}
          rows={5}
          autoCapitalize="sentences"
          onChange={(event) => update({ description: event.target.value })}
        />
      </Field>
    </div>
  );
}
