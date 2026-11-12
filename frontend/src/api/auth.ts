import { request } from '@/utils/request';
import type { User } from '@/types/api';

export function login(email: string, password: string) {
  return request<{ access_token: string; token_type: string; user: User }>('/auth/login', {
    method: 'POST',
    body: { email, password },
  });
}

export function me() {
  return request<User>('/auth/me');
}
