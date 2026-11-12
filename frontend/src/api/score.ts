import { request } from '@/utils/request';
import type { ScoreBatch } from '@/types/score';

export function fetchBatches(limit = 20) {
  return request<{ items: ScoreBatch[] }>(`/scores?limit=${limit}`);
}

export function fetchBatch(batchId: number, includeResults = false) {
  return request<ScoreBatch>(`/scores/${batchId}?include_results=${includeResults}`);
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
  return request<ScoreBatch>(`/scores/${batchId}/publish`, { method: 'POST' });
}
