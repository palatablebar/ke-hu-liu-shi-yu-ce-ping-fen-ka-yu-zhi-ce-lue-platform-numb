import { request } from '@/utils/request';
import type { ModelRun } from '@/types/model';

export function fetchModels(limit = 20) {
  return request<{ items: ModelRun[] }>(`/models?limit=${limit}`);
}

export function fetchModel(modelId: number) {
  return request<ModelRun>(`/models/${modelId}`);
}

export function trainModel(payload: { label?: string; learning_rate: number; l2: number; epochs: number }) {
  return request<ModelRun>('/models/train', { method: 'POST', body: payload });
}
