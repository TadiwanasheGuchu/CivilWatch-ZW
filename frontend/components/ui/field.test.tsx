import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Field } from "./field";
import { Input } from "./input";

describe("Field", () => {
  it("links label, hint and error to the control", () => {
    render(
      <Field label="Email address" hint="We never share it." error="Enter a valid email address.">
        <Input />
      </Field>,
    );
    const input = screen.getByLabelText("Email address");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("We never share it. Enter a valid email address.");
  });

  it("is not marked invalid without an error", () => {
    render(
      <Field label="Name">
        <Input />
      </Field>,
    );
    expect(screen.getByLabelText("Name")).not.toHaveAttribute("aria-invalid");
  });
});
