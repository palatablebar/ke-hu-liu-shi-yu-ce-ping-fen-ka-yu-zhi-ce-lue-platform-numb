const BASE = '/api';
const TOKEN_KEY = 'churnmod_token';

export class RequestError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || '';
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  raw?: boolean;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';

  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method: options.method || 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new RequestError(0, 'network_error', '网络不可达，请检查后端容器是否健康');
  }

  if (options.raw) {
    if (!response.ok) throw await toError(response);
    return (await response.blob()) as unknown as T;
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) {
      clearToken();
      window.dispatchEvent(new CustomEvent('churnmod:unauthorized'));
    }
    const body = payload as { error?: { code?: string; message?: string } };
    throw new RequestError(
      response.status,
      body.error?.code || 'http_error',
      body.error?.message || `请求失败（HTTP ${response.status}）`,
    );
  }
  return payload as T;
}

async function toError(response: Response): Promise<RequestError> {
  const payload = await response.json().catch(() => ({}));
  const body = payload as { error?: { code?: string; message?: string } };
  return new RequestError(response.status, body.error?.code || 'http_error', body.error?.message || '请求失败');
}

export async function downloadCsv(path: string, filename: string): Promise<void> {
  const token = getToken();
  const response = await fetch(`${BASE}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!response.ok) {
    const error = await toError(response);
    throw error;
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
