import { request } from '@/utils/request';
import type { AccountDetail, AccountPage } from '@/types/account';

export function fetchRiskList(params: { search?: string; band?: string; page?: number; pageSize?: number }) {
  const query = new URLSearchParams();
  if (params.search) query.set('search', params.search);
  if (params.band) query.set('band', params.band);
  query.set('page', String(params.page || 1));
  query.set('page_size', String(params.pageSize || 20));
  return request<AccountPage>(`/accounts?${query.toString()}`);
}

export function fetchAccount(code: string) {
  return request<AccountDetail>(`/accounts/${encodeURIComponent(code)}`);
}
