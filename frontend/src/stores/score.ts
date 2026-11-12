import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { ScoreBatch } from '@/types/score';
import * as api from '@/api/score';

export const useScoreStore = defineStore('score', () => {
  const batches = ref<ScoreBatch[]>([]);
  const selected = ref<ScoreBatch | null>(null);
  const loading = ref(false);
  const creating = ref(false);
  const error = ref('');
  const notice = ref('');

  async function load(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      batches.value = (await api.fetchBatches(20)).items;
      if (batches.value.length) await select(batches.value[0].id);
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载评分批次失败';
    } finally {
      loading.value = false;
    }
  }

  async function select(batchId: number): Promise<void> {
    selected.value = await api.fetchBatch(batchId, false);
  }

  async function create(payload: {
    model_run_id?: number;
    threshold: number;
    budget_total: number;
    cost_per_account: number;
    retention_lift: number;
  }): Promise<ScoreBatch> {
    creating.value = true;
    try {
      const batch = await api.createBatch(payload);
      batches.value = [batch, ...batches.value];
      selected.value = batch;
      notice.value = `批次 #${batch.batch_no} 已生成：高风险 ${batch.summary.high_risk} 家，预算内取 ${batch.selected_count} 家`;
      return batch;
    } finally {
      creating.value = false;
    }
  }

  async function publish(batchId: number): Promise<ScoreBatch> {
    const batch = await api.publishBatch(batchId);
    selected.value = batch;
    batches.value = batches.value.map((item) => (item.id === batch.id ? batch : item));
    notice.value = `批次 #${batch.batch_no} 已发布为阈值策略（阈值 ${batch.threshold}）`;
    return batch;
  }

  return { batches, selected, loading, creating, error, notice, load, select, create, publish };
});
