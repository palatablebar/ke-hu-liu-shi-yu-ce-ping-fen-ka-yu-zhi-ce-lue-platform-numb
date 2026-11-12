export type Role = 'admin' | 'analyst' | 'csm';

export interface User {
  id: number;
  email: string;
  display_name: string;
  role: Role;
}

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiErrorBody {
  error?: { code?: string; message?: string; request_id?: string };
}
