export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  merchant_id: string | null;
  role: string;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: string;
  merchant_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
