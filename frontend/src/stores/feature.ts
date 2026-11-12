import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { FeatureCatalog } from '@/types/feature';
import * as api from '@/api/feature';

export const useFeatureStore = defineStore('feature', () => {
  const catalog = ref<FeatureCatalog | null>(null);
  const loading = ref(false);
  const error = ref('');

  async function load(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      catalog.value = await api.fetchFeatureCatalog();
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载特征统计失败';
    } finally {
      loading.value = false;
    }
  }

  return { catalog, loading, error, load };
});
