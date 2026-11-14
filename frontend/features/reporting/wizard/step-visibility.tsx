"use client";

import { Globe, Lock } from "lucide-react";

import { ChoiceCard } from "@/components/ui/choice-card";

import type { StepProps } from "./step-props";

export function VisibilityStep({ draft, update, errors }: StepProps) {
  return (
    <fieldset className="space-y-2" aria-describedby={errors.visibility ? "visibility-error" : undefined}>
      <legend className="mb-1 text-sm text-navy-soft">This cannot be changed after you send the report.</legend>
      <ChoiceCard
        name="visibility"
        value="PUBLIC"
        checked={draft.visibility === "PUBLIC"}
        onChange={() => update({ visibility: "PUBLIC" })}
        icon={<Globe aria-hidden="true" className="size-5" />}
        title="Public"
        description="Anyone can see the problem, its photos and progress once the council has verified it. Your name is never shown."
      />
      <ChoiceCard
        name="visibility"
        value="PRIVATE"
        checked={draft.visibility === "PRIVATE"}
        onChange={() => update({ visibility: "PRIVATE" })}
        icon={<Lock aria-hidden="true" className="size-5" />}
        title="Private"
        description="Only you and council staff can see it. Choose this if the report or photos show private property or people."
      />
      {errors.visibility ? (
        <p id="visibility-error" className="text-sm font-medium text-red-text">
          {errors.visibility}
        </p>
      ) : null}
    </fieldset>
  );
}
