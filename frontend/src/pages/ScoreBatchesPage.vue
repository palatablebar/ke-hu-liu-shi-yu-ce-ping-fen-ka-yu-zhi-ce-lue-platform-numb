<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import AppShell from '@/components/common/AppShell.vue';
import Plate from '@/components/common/Plate.vue';
import StatusSeal from '@/components/common/StatusSeal.vue';
import RiskTable from '@/components/common/RiskTable.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorNotice from '@/components/common/ErrorNotice.vue';
import { useAuthStore } from '@/stores/auth';
import { useScoreStore } from '@/stores/score';
import { useModelStore } from '@/stores/model';
import { fetchBatch } from '@/api/score';
import { downloadCsv } from '@/utils/request';
import { RISK_BAND_LABELS, RISK_BAND_ORDER, RISK_BAND_TONE } from '@/constants/riskBand';
import { formatDateTime } from '@/utils/formatDate';
import type { RiskRow } from '@/types/account';
import type { ScoreBatch } from '@/types/score';

const auth = useAuthStore();
const scoreStore = useScoreStore();
const modelStore = useModelStore();

const threshold = ref(0.35);
const budget = ref(12500);
const costPerAccount = ref(500);
const retentionLift = ref(0.35);
const localError = ref('');
const resultsBatch = ref<ScoreBatch | null>(null);
const topRows = ref<RiskRow[]>([]);

const selected = computed(() => scoreStore.selected);
const summary = computed(() => selected.value?.summary || null);
const latestModel = computed(() => modelStore.models.find((model) => model.status === 'succeeded') || null);
const scan = computed(() => latestModel.value?.threshold_scan || []);
const topModel = computed(() => modelStore.detail || latestModel.value);

async function loadResults(batchId?: number) {
  const id = batchId || selected.value?.id;
  if (!id) return;
  try {
    const batch = await fetchBatch(id, true);
    resultsBatch.value = batch;
    const rows = ((batch.results || []) as unknown as RiskRow[]).filter((row) => row.selected);
    topRows.value = rows.sort((a, b) => (a.rank || 999) - (b.rank || 999));
  } catch {
    topRows.value = [];
  }
}

async function createBatch() {
  localError.value = '';
  if (!auth.canScore) {
    localError.value = '当前角色不能创建评分批次（服务端 403）';
    return;
  }
  if (threshold.value <= 0.05 || threshold.value >= 0.95) {
    localError.value = '阈值需在 0.05 ~ 0.95 之间';
    return;
  }
  try {
    const batch = await scoreStore.create({
      model_run_id: topModel.value?.id,
      threshold: threshold.value,
      budget_total: budget.value,
      cost_per_account: costPerAccount.value,
      retention_lift: retentionLift.value,
    });
    await loadResults(batch.id);
  } catch (err) {
    localError.value = err instanceof Error ? err.message : '创建评分批次失败';
  }
}

async function publish() {
  if (!selected.value) return;
  localError.value = '';
  try {
    await scoreStore.publish(selected.value.id);
  } catch (err) {
    localError.value = err instanceof Error ? err.message : '发布失败';
  }
}

async function exportCsv() {
  if (!selected.value) return;
  localError.value = '';
  try {
    await downloadCsv(`/scores/${selected.value.id}/export`, `churnmod_${selected.value.label}_top${selected.value.selected_count}.csv`);
    scoreStore.notice = `已导出 ${selected.value.selected_count} 家触达名单与原因 CSV`;
  } catch (err) {
    localError.value = err instanceof Error ? err.message : '导出失败';
  }
}

function chooseBatch(batchId: number) {
  scoreStore.select(batchId).then(() => loadResults(batchId));
}

watch(selected, (batch) => {
  if (batch) {
    threshold.value = batch.threshold;
    budget.value = batch.budget_total;
    costPerAccount.value = batch.cost_per_account;
    retentionLift.value = batch.retention_lift;
  }
});

onMounted(async () => {
  await Promise.all([scoreStore.load(), modelStore.load()]);
  await loadResults();
});
</script>

<template>
  <AppShell>
    <header class="page__head reveal">
      <div>
        <p class="eyebrow">Chart sheet 04 · Policy</p>
        <h1 class="page__title">阈值策略与触达预算</h1>
        <p class="page__kicker">
          阈值决定「谁进池」，预算决定「先找谁」；名单按概率降序切到 K 家，每家具名三条原因。
        </p>
      </div>
      <div class="page__meta">
        当前批次：{{ selected ? `#${selected.batch_no} · ${selected.published ? '已发布' : '草稿'}` : '—' }}<br />
        操作权限：{{ auth.canPublish ? '可发布' : auth.canScore ? '可创建（发布需 admin）' : '只读（403）' }}
      </div>
    </header>

    <div class="page__body">
      <ErrorNotice v-if="scoreStore.error" :message="scoreStore.error" @retry="scoreStore.load()" />
      <p v-if="scoreStore.notice" class="note-line">{{ scoreStore.notice }}</p>
      <p v-if="localError" class="form-error">{{ localError }}</p>

      <div class="split split--main">
        <div class="stack">
          <Plate title="预算内触达名单" kicker="Top-K outreach" :hint="selected ? `阈值 ${selected.threshold} · 预算 ¥${selected.budget_total} · 成本 ¥${selected.cost_per_account}/家` : ''">
            <template #actions>
              <button class="btn btn--small" type="button" :disabled="!selected" @click="exportCsv">导出名单 CSV</button>
              <button
                class="btn btn--primary btn--small"
                type="button"
                :disabled="!selected || selected.published || !auth.canPublish"
                @click="publish"
              >
                {{ selected?.published ? '已发布' : auth.canPublish ? '发布为阈值策略' : '仅 admin 可发布' }}
              </button>
            </template>
            <div v-if="!topRows.length" class="loading">该批次没有预算内名单……</div>
            <RiskTable v-else :rows="topRows" />
            <p class="small muted" style="margin-top: 10px">
              预期挽回合计 ¥{{ summary?.total_expected_save?.toFixed?.(0) ?? '—' }} ·
              人均 ¥{{ summary?.avg_expected_save?.toFixed?.(0) ?? '—' }} · 口径：年化合同额 × P(流失) × 可挽留比例
            </p>
          </Plate>

          <Plate title="批次编年" kicker="Score batches" hint="每次评分记录阈值、预算与名单">
            <div class="ledger-wrap" style="max-height: 260px">
              <table class="ledger">
                <thead>
                  <tr>
                    <th>批次</th>
                    <th>阈值</th>
                    <th>预算</th>
                    <th>高风险</th>
                    <th>名单</th>
                    <th>发布</th>
                    <th>时间</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="batch in scoreStore.batches" :key="batch.id" class="is-clickable" :class="{ 'is-selected': batch.id === selected?.id }" @click="chooseBatch(batch.id)">
                    <td class="numeral">#{{ batch.batch_no }}</td>
                    <td class="mono">{{ batch.threshold }}</td>
                    <td class="mono">¥{{ batch.budget_total }}</td>
                    <td class="mono">{{ batch.summary?.high_risk }}</td>
                    <td class="mono">{{ batch.selected_count }}</td>
                    <td><StatusSeal :label="batch.published ? '已发布' : '未发布'" :tone="batch.published ? 'seal--low' : 'seal--neutral'" /></td>
                    <td class="small muted">{{ formatDateTime(batch.created_at) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Plate>
        </div>

        <div class="stack">
          <Plate title="新建评分批次" kicker="New batch" hint="选择阈值与预算后按当前模型重算">
            <form class="stack" @submit.prevent="createBatch">
              <div class="field">
                <span class="field__label">判定阈值（0.05 ~ 0.95）</span>
                <input v-model.number="threshold" class="input" type="number" step="0.01" min="0.05" max="0.95" />
              </div>
              <div class="field">
                <span class="field__label">触达预算（元）</span>
                <input v-model.number="budget" class="input" type="number" step="500" min="500" />
              </div>
              <div class="field">
                <span class="field__label">单客成本（元）</span>
                <input v-model.number="costPerAccount" class="input" type="number" step="100" min="100" />
              </div>
              <div class="field">
                <span class="field__label">可挽留比例</span>
                <input v-model.number="retentionLift" class="input" type="number" step="0.05" min="0.05" max="1" />
              </div>
              <button class="btn btn--rust" type="submit" :disabled="scoreStore.creating || !auth.canScore">
                {{ scoreStore.creating ? '评分中…' : auth.canScore ? '生成名单' : '当前角色只读' }}
              </button>
              <p class="small muted">
                模型批次 {{ topModel ? `#${topModel.run_no} · AUC ${topModel.metrics?.auc}` : '—' }} ·
                K = floor(预算 / 单客成本)
              </p>
            </form>
          </Plate>

          <Plate title="阈值扫描" kicker="Threshold scan" hint="0.10 ~ 0.90；当前阈值高亮">
            <div class="ledger-wrap" style="max-height: 240px">
              <table class="ledger">
                <thead>
                  <tr>
                    <th>阈值</th>
                    <th>精确率</th>
                    <th>召回率</th>
                    <th>F1</th>
                    <th>命中</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="point in scan.filter((item) => Math.round(item.threshold * 100) % 5 === 0)"
                    :key="point.threshold"
                    :style="{ background: Math.abs(point.threshold - threshold) < 0.005 ? 'var(--sand)' : undefined }"
                  >
                    <td class="mono">{{ point.threshold.toFixed(2) }}</td>
                    <td class="mono">{{ (point.precision * 100).toFixed(1) }}%</td>
                    <td class="mono">{{ (point.recall * 100).toFixed(1) }}%</td>
                    <td class="mono">{{ (point.f1 * 100).toFixed(1) }}%</td>
                    <td class="mono">{{ point.flagged }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Plate>

          <Plate title="分档与发布" kicker="Bands & policy">
            <div v-if="!summary" class="loading">暂无批次</div>
            <template v-else>
              <div class="stack" style="gap: 8px">
                <div v-for="band in RISK_BAND_ORDER" :key="band" class="spread small">
                  <StatusSeal :label="RISK_BAND_LABELS[band]" :tone="RISK_BAND_TONE[band]" />
                  <span class="numeral">{{ summary.band_sizes?.[band] ?? 0 }} 家 · lift {{ (summary.band_lift?.[band] ?? 0).toFixed(2) }}</span>
                </div>
              </div>
              <p class="small muted" style="margin-top: 10px">
                {{ selected?.published ? `策略已由 ${selected.published_by} 于 ${formatDateTime(selected.published_at)} 发布。` : '发布后该批次成为当期阈值策略，后续批次可再次覆盖。' }}
              </p>
            </template>
          </Plate>
        </div>
      </div>
    </div>
  </AppShell>
</template>
