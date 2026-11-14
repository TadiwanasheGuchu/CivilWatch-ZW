import { z } from "zod";

/** Client-side mirrors of the API's rules (app/schemas/auth.py). The API re-validates. */
export const PASSWORD_MIN_LENGTH = 10;
export const PASSWORD_MAX_LENGTH = 128;

const email = z
  .string()
  .trim()
  .min(1, "Enter your email address.")
  .max(254, "Email address is too long.")
  .pipe(z.email("Enter a valid email address, like name@example.com."));

const newPassword = z
  .string()
  .min(PASSWORD_MIN_LENGTH, `Use at least ${PASSWORD_MIN_LENGTH} characters.`)
  .max(PASSWORD_MAX_LENGTH, `Use at most ${PASSWORD_MAX_LENGTH} characters.`)
  .refine((value) => value.trim().length > 0, "Password cannot be only spaces.");

const fullName = z
  .string()
  .trim()
  .min(1, "Enter your full name.")
  .max(120, "Name must be 120 characters or fewer.");

export const signInSchema = z.object({
  email,
  password: z.string().min(1, "Enter your password.").max(PASSWORD_MAX_LENGTH),
});

export const registerSchema = z
  .object({ full_name: fullName, email, password: newPassword })
  .refine((data) => data.password.trim().toLowerCase() !== data.email.toLowerCase(), {
    path: ["password"],
    message: "Password must not be the same as your email address.",
  });

export const profileSchema = z.object({ full_name: fullName });

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password.").max(PASSWORD_MAX_LENGTH),
    new_password: newPassword,
  })
  .refine((data) => data.new_password !== data.current_password, {
    path: ["new_password"],
    message: "New password must be different from your current password.",
  });

export type SignInValues = z.infer<typeof signInSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
export type ProfileValues = z.infer<typeof profileSchema>;
export type ChangePasswordValues = z.infer<typeof changePasswordSchema>;
