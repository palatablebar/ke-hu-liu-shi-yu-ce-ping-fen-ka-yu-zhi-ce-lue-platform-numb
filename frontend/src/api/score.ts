import { request } from '@/utils/request';
import type { ScoreBatch } from '@/types/score';
import type { PolicyDiff, PolicySwitchResult } from '@/constants/scoreLifecycle';

export function fetchBatches(limit = 20) {
  return request<{ items: ScoreBatch[] }>(`/scores?limit=${limit}`);
}

export function fetchActiveBatch() {
  return request<{ active: ScoreBatch | null }>('/scores/active');
}

export function fetchBatch(batchId: number, includeResults = false) {
  return request<ScoreBatch>(`/scores/${batchId}?include_results=${includeResults}`);
}

export function fetchPolicyDiff(batchId: number) {
  return request<PolicyDiff>(`/scores/${batchId}/diff`);
}

export function createBatch(payload: {
  model_run_id?: number;
  threshold: number;
  budget_total: number;
  cost_per_account: number;
  retention_lift: number;
}) {
  return request<ScoreBatch>('/scores', { method: 'POST', body: payload });
}

export function publishBatch(batchId: number) {
  return request<PolicySwitchResult>(`/scores/${batchId}/publish`, { method: 'POST' });
}

// 导出现行策略名单（风险图与策略台共用同一现行版本）。
export const activeExportPath = '/scores/export/active';
