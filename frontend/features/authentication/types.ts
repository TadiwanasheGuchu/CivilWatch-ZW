/** Mirrors backend `UserRead` / `SessionResponse` (app/schemas). */
export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  is_platform_admin: boolean;
  email_notifications: boolean;
  created_at: string;
}

export interface SessionData {
  user: CurrentUser;
  csrf_token: string;
  expires_at: string;
}
