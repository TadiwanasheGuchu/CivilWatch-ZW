"use client";

import { LoadError, LoadingRows } from "@/components/ui/page-states";
import { errorMessage } from "@/lib/api-client";

import { ChoiceCard } from "@/components/ui/choice-card";

import { useCategories } from "../hooks";
import type { StepProps } from "./step-props";

export function CategoryStep({ draft, update, errors }: StepProps) {
  const { data, isPending, isError, error, refetch } = useCategories();
  if (!data && isPending) return <LoadingRows label="Loading categories" rows={4} />;
  if (!data && isError) return <LoadError message={errorMessage(error)} onRetry={() => void refetch()} />;

  return (
    <fieldset aria-describedby={errors.categoryId ? "category-error" : undefined}>
      <legend className="mb-3 text-sm text-navy-soft">Choose the closest match.</legend>
      <div className="grid gap-2 sm:grid-cols-2">
        {(data ?? []).map((category) => (
          <ChoiceCard
            key={category.id}
            name="category"
            value={category.id}
            checked={draft.categoryId === category.id}
            onChange={() => update({ categoryId: category.id })}
            title={category.name}
            description={category.description}
          />
        ))}
      </div>
      {errors.categoryId ? (
        <p id="category-error" className="mt-2 text-sm font-medium text-red-text">
          {errors.categoryId}
        </p>
      ) : null}
    </fieldset>
  );
}
