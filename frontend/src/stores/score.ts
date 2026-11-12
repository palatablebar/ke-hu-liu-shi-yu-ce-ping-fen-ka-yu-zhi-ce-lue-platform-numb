import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type { ScoreBatch } from '@/types/score';
import type { PolicyDiff, PolicySwitchResult } from '@/constants/scoreLifecycle';
import { SCORE_LIFECYCLE } from '@/constants/scoreLifecycle';
import * as api from '@/api/score';

export const useScoreStore = defineStore('score', () => {
  const batches = ref<ScoreBatch[]>([]);
  const active = ref<ScoreBatch | null>(null);
  const selected = ref<ScoreBatch | null>(null);
  const diff = ref<PolicyDiff | null>(null);
  const lastSwitch = ref<PolicySwitchResult | null>(null);
  const loading = ref(false);
  const creating = ref(false);
  const publishing = ref(false);
  const diffLoading = ref(false);
  const error = ref('');
  const notice = ref('');

  const drafts = computed(() => batches.value.filter((item) => item.lifecycle === SCORE_LIFECYCLE.DRAFT));
  const history = computed(() => batches.value.filter((item) => item.lifecycle === SCORE_LIFECYCLE.ARCHIVED));
  const ledger = computed(() => batches.value);

  function _upsert(batch: ScoreBatch): void {
    const idx = batches.value.findIndex((item) => item.id === batch.id);
    if (idx >= 0) batches.value.splice(idx, 1, batch);
    else batches.value.unshift(batch);
    if (active.value?.id === batch.id) active.value = batch;
    if (selected.value?.id === batch.id) selected.value = batch;
  }

  async function load(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      const [list, activeResp] = await Promise.all([api.fetchBatches(50), api.fetchActiveBatch()]);
      batches.value = list.items;
      active.value = activeResp.active;
      // 默认选中现行策略；没有现行策略时落到第一个草稿。
      const preferred = active.value || batches.value.find((item) => item.lifecycle === SCORE_LIFECYCLE.DRAFT) || null;
      if (preferred) await select(preferred.id);
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载评分批次失败';
    } finally {
      loading.value = false;
    }
  }

  async function select(batchId: number): Promise<void> {
    selected.value = await api.fetchBatch(batchId, false);
    await loadDiff(batchId);
  }

  async function loadDiff(batchId: number): Promise<void> {
    diffLoading.value = true;
    try {
      diff.value = await api.fetchPolicyDiff(batchId);
    } catch {
      diff.value = null;
    } finally {
      diffLoading.value = false;
    }
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
      _upsert(batch);
      selected.value = batch;
      await loadDiff(batch.id);
      if (batch.reused) {
        notice.value = `同一策略已存在（#${batch.batch_no} · ${lifecycleLabel(batch.lifecycle)}），未新增版本`;
      } else {
        notice.value = `草稿 #${batch.batch_no} 已生成：高风险 ${batch.summary.high_risk} 家，预算内取 ${batch.selected_count} 家；现行策略未变更`;
      }
      return batch;
    } finally {
      creating.value = false;
    }
  }

  async function publish(batchId: number): Promise<PolicySwitchResult> {
    publishing.value = true;
    try {
      const result = await api.publishBatch(batchId);
      lastSwitch.value = result;
      // 重新拉取编年，确保旧版本归档、新版本生效的状态全局一致。
      const [list, activeResp] = await Promise.all([api.fetchBatches(50), api.fetchActiveBatch()]);
      batches.value = list.items;
      active.value = activeResp.active;
      selected.value = result.active;
      await loadDiff(result.active.id);
      if (result.switched) {
        const from = result.previous ? `v${result.previous.policy_version} → ` : '';
        notice.value = `策略切换完成：${from}v${result.active.policy_version} 成为唯一现行策略，旧版本已归档保留`;
      } else {
        notice.value = `v${result.active.policy_version} 已是现行策略，重复发布未产生新版本`;
      }
      return result;
    } finally {
      publishing.value = false;
    }
  }

  function lifecycleLabel(value: string): string {
    return value === SCORE_LIFECYCLE.ACTIVE
      ? '现行策略'
      : value === SCORE_LIFECYCLE.ARCHIVED
        ? '历史版本'
        : '草稿';
  }

  return {
    batches,
    active,
    selected,
    diff,
    lastSwitch,
    drafts,
    history,
    ledger,
    loading,
    creating,
    publishing,
    diffLoading,
    error,
    notice,
    load,
    select,
    loadDiff,
    create,
    publish,
  };
});
