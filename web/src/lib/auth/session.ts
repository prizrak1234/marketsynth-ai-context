/** Session / current-user types (CPH.3). */

export type AuthUser = {
  id: string;
  email: string | null;
  display_name: string | null;
  role: string;
  is_active: boolean;
  last_login_at: string | null;
};

export type LoginResult = {
  user: AuthUser;
  session_id: string;
  expires_at: string;
  auth_method: string;
};
