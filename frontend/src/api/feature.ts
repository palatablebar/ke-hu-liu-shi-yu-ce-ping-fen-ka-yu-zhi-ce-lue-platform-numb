import { request } from '@/utils/request';
import type { FeatureCatalog, FeatureSet } from '@/types/feature';

export function fetchFeatureCatalog() {
  return request<FeatureCatalog>('/features');
}

export function fetchFeatureSets() {
  return request<{ items: FeatureSet[] }>('/features/sets');
}
