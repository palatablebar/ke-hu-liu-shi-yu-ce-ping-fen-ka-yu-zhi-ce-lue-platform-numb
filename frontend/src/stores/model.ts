import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type { ModelRun } from '@/types/model';
import * as api from '@/api/model';
import { sleep } from '@/utils/sleep';

export const useModelStore = defineStore('model', () => {
  const models = ref<ModelRun[]>([]);
  const selectedId = ref<number | null>(null);
  const detail = ref<ModelRun | null>(null);
  const loading = ref(false);
  const error = ref('');
  const training = ref(false);

  const selected = computed(() => detail.value || models.value.find((model) => model.id === selectedId.value) || null);
  const succeeded = computed(() => models.value.filter((model) => model.status === 'succeeded'));

  async function load(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      models.value = (await api.fetchModels(20)).items;
      if (!selectedId.value && models.value.length) selectedId.value = models.value[0].id;
      if (selectedId.value) detail.value = await api.fetchModel(selectedId.value);
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载训练批次失败';
    } finally {
      loading.value = false;
    }
  }

  async function select(modelId: number): Promise<void> {
    selectedId.value = modelId;
    detail.value = await api.fetchModel(modelId);
  }

  async function poll(modelId: number, timeoutMs = 90_000): Promise<ModelRun | null> {
    const started = Date.now();
    for (;;) {
      const run = await api.fetchModel(modelId);
      detail.value = run;
      models.value = models.value.map((item) => (item.id === run.id ? run : item));
      if (run.status === 'succeeded' || run.status === 'failed') return run;
      if (Date.now() - started > timeoutMs) return run;
      await sleep(900);
    }
  }

  async function train(payload: { learning_rate: number; l2: number; epochs: number; label?: string }): Promise<ModelRun> {
    training.value = true;
    try {
      const run = await api.trainModel(payload);
      models.value = [run, ...models.value];
      selectedId.value = run.id;
      return run;
    } finally {
      training.value = false;
    }
  }

  return { models, selectedId, detail, loading, error, training, selected, succeeded, load, select, poll, train };
});
