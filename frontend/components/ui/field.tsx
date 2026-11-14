import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from "react";

interface FieldControlProps {
  id?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}

interface FieldProps {
  label: string;
  hint?: ReactNode;
  error?: string;
  children: ReactElement<FieldControlProps>;
}

/**
 * Label, optional hint and error message wired to one control with the
 * correct id, aria-invalid and aria-describedby.
 */
export function Field({ label, hint, error, children }: FieldProps) {
  const generatedId = useId();
  const id = (isValidElement(children) && children.props.id) || generatedId;
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-navy">
        {label}
      </label>
      {hint ? (
        <p id={hintId} className="text-sm text-slate">
          {hint}
        </p>
      ) : null}
      {cloneElement(children, {
        id,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": describedBy,
      })}
      {error ? (
        <p id={errorId} className="text-sm font-medium text-red-text">
          {error}
        </p>
      ) : null}
    </div>
  );
}
