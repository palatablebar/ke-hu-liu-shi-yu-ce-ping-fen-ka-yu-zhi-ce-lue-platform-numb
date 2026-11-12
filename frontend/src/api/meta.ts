import { request } from '@/utils/request';
import type { Overview } from '@/types/overview';

export function fetchOverview() {
  return request<Overview>('/meta/overview');
}

export function fetchAuditLogs(limit = 100) {
  return request<{ items: { id: number; actor_email: string; actor_role: string; action: string; resource_type: string; resource_id: string; created_at: string }[] }>(
    `/audit-logs?limit=${limit}`,
  );
}
