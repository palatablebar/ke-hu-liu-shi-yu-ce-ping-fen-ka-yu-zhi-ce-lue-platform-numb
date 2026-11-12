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
import { fetchBatch, activeExportPath } from '@/api/score';
import { downloadCsv } from '@/utils/request';
import { RISK_BAND_LABELS, RISK_BAND_ORDER, RISK_BAND_TONE } from '@/constants/riskBand';
import {
  SCORE_LIFECYCLE,
  SCORE_LIFECYCLE_LABELS,
  SCORE_LIFECYCLE_TONES,
} from '@/constants/scoreLifecycle';
import { formatDateTime } from '@/utils/formatDate';
import type { RiskRow } from '@/types/account';
import type { ScoreBatch } from '@/types/score';
import type { PolicyParamChange } from '@/constants/scoreLifecycle';

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
const activeBatch = computed(() => scoreStore.active);
const summary = computed(() => selected.value?.summary || null);
const diff = computed(() => scoreStore.diff);
const latestModel = computed(() => modelStore.models.find((model) => model.status === 'succeeded') || null);
const scan = computed(() => latestModel.value?.threshold_scan || []);
const topModel = computed(() => modelStore.detail || latestModel.value);

const PARAM_LABELS: Record<string, string> = {
  threshold: '判定阈值',
  budget_total: '触达预算',
  cost_per_account: '单客成本',
  retention_lift: '可挽留比例',
};

function lifecycleSeal(batch: ScoreBatch) {
  return {
    label: SCORE_LIFECYCLE_LABELS[batch.lifecycle] || batch.lifecycle,
    tone: SCORE_LIFECYCLE_TONES[batch.lifecycle] || 'seal--neutral',
  };
}

function versionText(batch: ScoreBatch): string {
  if (batch.policy_version != null) return `v${batch.policy_version}`;
  return `草稿 #${batch.batch_no}`;
}

async function loadResults(batchId?: number) {
  const id = batchId || selected.value?.id;
  if (!id) {
    topRows.value = [];
    resultsBatch.value = null;
    return;
  }
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
    localError.value = '当前角色不能创建评分草稿（服务端 403）';
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
    localError.value = err instanceof Error ? err.message : '创建评分草稿失败';
  }
}

async function publish() {
  if (!selected.value) return;
  localError.value = '';
  try {
    await scoreStore.publish(selected.value.id);
    await loadResults(selected.value.id);
  } catch (err) {
    localError.value = err instanceof Error ? err.message : '发布失败';
  }
}

async function exportActiveCsv() {
  if (!activeBatch.value) {
    localError.value = '还没有现行策略，请先发布一个草稿';
    return;
  }
  localError.value = '';
  try {
    await downloadCsv(
      activeExportPath,
      `churnmod_policy_v${activeBatch.value.policy_version}_top${activeBatch.value.selected_count}.csv`,
    );
    scoreStore.notice = `已导出现行策略 v${activeBatch.value.policy_version} 的 ${activeBatch.value.selected_count} 家触达名单 CSV`;
  } catch (err) {
    localError.value = err instanceof Error ? err.message : '导出失败';
  }
}

function chooseBatch(batchId: number) {
  scoreStore.select(batchId).then(() => loadResults(batchId));
}

function fmtParam(change: PolicyParamChange): string {
  const digits = change.field === 'threshold' || change.field === 'retention_lift' ? 2 : 0;
  const v = change.current;
  return v == null ? '—' : digits === 2 ? v.toFixed(2) : `¥${v.toLocaleString()}`;
}
function fmtParamNew(change: PolicyParamChange): string {
  const digits = change.field === 'threshold' || change.field === 'retention_lift' ? 2 : 0;
  return digits === 2 ? change.candidate.toFixed(2) : `¥${change.candidate.toLocaleString()}`;
}

watch(selected, (batch) => {
  if (batch) {
    threshold.value = batch.threshold;
    budget.value = batch.budget_total;
    costPerAccount.value = batch.cost_per_account;
    retentionLift.value = batch.retention_lift;
    loadResults(batch.id);
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
          草稿、现行策略、历史版本三态分离：草稿只做候选对比，发布后才一次性切换为唯一现行策略，
          客户风险图与导出名单始终跟随同一现行版本。
        </p>
      </div>
      <div class="page__meta">
        现行策略：{{ activeBatch ? `v${activeBatch.policy_version} · 阈值 ${activeBatch.threshold}` : '尚未发布' }}<br />
        操作权限：{{ auth.canPublish ? '可发布' : auth.canScore ? '可建草稿（发布需 admin）' : '只读（403）' }}
      </div>
    </header>

    <div class="page__body">
      <ErrorNotice v-if="scoreStore.error" :message="scoreStore.error" @retry="scoreStore.load()" />
      <p v-if="scoreStore.notice" class="note-line">{{ scoreStore.notice }}</p>
      <p v-if="localError" class="form-error">{{ localError }}</p>

      <div class="split split--main">
        <div class="stack">
          <!-- 现行策略：风险图与导出共同跟随的唯一版本 -->
          <Plate
            title="现行策略 · 预算内触达名单"
            kicker="Active policy · Top-K outreach"
            :hint="activeBatch ? `v${activeBatch.policy_version} · 阈值 ${activeBatch.threshold} · 预算 ¥${activeBatch.budget_total} · 成本 ¥${activeBatch.cost_per_account}/家` : '尚无现行策略'"
          >
            <template #actions>
              <button class="btn btn--small" type="button" :disabled="!activeBatch" @click="exportActiveCsv">
                导出现行名单 CSV
              </button>
              <button
                v-if="selected && selected.lifecycle === SCORE_LIFECYCLE.DRAFT"
                class="btn btn--primary btn--small"
                type="button"
                :disabled="!auth.canPublish || scoreStore.publishing"
                @click="publish"
              >
                {{ scoreStore.publishing ? '切换中…' : auth.canPublish ? '发布并一次性切换' : '仅 admin 可发布' }}
              </button>
              <StatusSeal
                v-else-if="selected"
                :label="lifecycleSeal(selected).label"
                :tone="lifecycleSeal(selected).tone"
              />
            </template>

            <div v-if="!activeBatch" class="loading">
              还没有现行策略。请在右侧生成草稿并由 admin 发布；发布前风险图与导出不会被任何草稿改动。
            </div>
            <template v-else>
              <p class="small muted" style="margin: 0 0 8px">
                当前查看：<strong>{{ versionText(selected || activeBatch) }}</strong>
                <template v-if="selected && selected.id !== activeBatch.id">
                  （非现行版本，仅用于复核，不能对外导出）
                </template>
              </p>
              <div v-if="!topRows.length" class="loading">该版本没有预算内名单……</div>
              <RiskTable v-else :rows="topRows" />
              <p class="small muted" style="margin-top: 10px">
                预期挽回合计 ¥{{ summary?.total_expected_save?.toFixed?.(0) ?? '—' }} ·
                人均 ¥{{ summary?.avg_expected_save?.toFixed?.(0) ?? '—' }} · 口径：年化合同额 × P(流失) × 可挽留比例
              </p>
            </template>
          </Plate>

          <!-- 候选差异：选中草稿/任意版本相对现行策略 -->
          <Plate
            title="候选差异（相对现行策略）"
            kicker="Candidate diff"
            :hint="diff?.current ? `对照现行 v${diff.current.policy_version}` : '当前没有现行策略，发布后即首个版本'"
          >
            <div v-if="!diff" class="loading">暂无差异数据……</div>
            <template v-else>
              <div class="grid-stats" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 10px">
                <div class="stat">
                  <span class="stat__label">高风险池</span>
                  <span class="stat__value">{{ diff.summary.candidate_high_risk }}</span>
                  <span class="stat__note">现行 {{ diff.summary.current_high_risk }}</span>
                </div>
                <div class="stat">
                  <span class="stat__label">预算内名单</span>
                  <span class="stat__value">{{ diff.summary.candidate_selected }}</span>
                  <span class="stat__note">现行 {{ diff.summary.current_selected }}</span>
                </div>
                <div class="stat">
                  <span class="stat__label">新进名单</span>
                  <span class="stat__value" style="color: var(--rust)">+{{ diff.summary.selected_added }}</span>
                  <span class="stat__note">高风险新增 {{ diff.summary.high_risk_added }}</span>
                </div>
                <div class="stat">
                  <span class="stat__label">移出名单</span>
                  <span class="stat__value">-{{ diff.summary.selected_removed }}</span>
                  <span class="stat__note">高风险移出 {{ diff.summary.high_risk_removed }}</span>
                </div>
              </div>

              <table class="ledger" style="margin-bottom: 10px">
                <thead>
                  <tr><th>参数</th><th>现行</th><th>候选</th><th>变化</th></tr>
                </thead>
                <tbody>
                  <tr v-for="change in diff.param_changes" :key="change.field">
                    <td class="small">{{ PARAM_LABELS[change.field] || change.field }}</td>
                    <td class="mono small">{{ fmtParam(change) }}</td>
                    <td class="mono small">{{ fmtParamNew(change) }}</td>
                    <td>
                      <StatusSeal
                        :label="change.changed ? '调整' : '一致'"
                        :tone="change.changed ? 'seal--medium' : 'seal--neutral'"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>

              <div class="split" style="gap: 12px">
                <div>
                  <p class="small" style="color: var(--rust); margin: 4px 0">
                    新进预算名单（{{ diff.selected_added.length }}）
                  </p>
                  <div class="ledger-wrap" style="max-height: 180px">
                    <table class="ledger">
                      <thead><tr><th>客户</th><th>分数</th><th>排名</th></tr></thead>
                      <tbody>
                        <tr v-for="row in diff.selected_added.slice(0, 20)" :key="row.account_code">
                          <td class="small">{{ row.company_name }} <span class="muted">{{ row.account_code }}</span></td>
                          <td class="mono small">{{ row.score.toFixed(3) }}</td>
                          <td class="mono small">#{{ row.rank ?? '—' }}</td>
                        </tr>
                        <tr v-if="!diff.selected_added.length"><td colspan="3" class="small muted">无变化</td></tr>
                      </tbody>
                    </table>
                  </div>
                </div>
                <div>
                  <p class="small" style="margin: 4px 0">移出预算名单（{{ diff.selected_removed.length }}）</p>
                  <div class="ledger-wrap" style="max-height: 180px">
                    <table class="ledger">
                      <thead><tr><th>客户</th><th>分数</th><th>原排名</th></tr></thead>
                      <tbody>
                        <tr v-for="row in diff.selected_removed.slice(0, 20)" :key="row.account_code">
                          <td class="small">{{ row.company_name }} <span class="muted">{{ row.account_code }}</span></td>
                          <td class="mono small">{{ row.score.toFixed(3) }}</td>
                          <td class="mono small">#{{ row.rank ?? '—' }}</td>
                        </tr>
                        <tr v-if="!diff.selected_removed.length"><td colspan="3" class="small muted">无变化</td></tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </template>
          </Plate>

          <!-- 版本编年：草稿 / 现行 / 历史分组可见 -->
          <Plate title="版本编年" kicker="Policy ledger" hint="草稿不生效；现行策略全局唯一；历史版本只留不生效">
            <div class="ledger-wrap" style="max-height: 300px">
              <table class="ledger">
                <thead>
                  <tr>
                    <th>版本</th>
                    <th>状态</th>
                    <th>阈值</th>
                    <th>预算</th>
                    <th>高风险</th>
                    <th>名单</th>
                    <th>发布人 / 时间</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="batch in scoreStore.ledger"
                    :key="batch.id"
                    class="is-clickable"
                    :class="{ 'is-selected': batch.id === selected?.id }"
                    @click="chooseBatch(batch.id)"
                  >
                    <td class="numeral">{{ versionText(batch) }}</td>
                    <td><StatusSeal :label="lifecycleSeal(batch).label" :tone="lifecycleSeal(batch).tone" /></td>
                    <td class="mono">{{ batch.threshold }}</td>
                    <td class="mono">¥{{ batch.budget_total }}</td>
                    <td class="mono">{{ batch.summary?.high_risk }}</td>
                    <td class="mono">{{ batch.selected_count }}</td>
                    <td class="small muted">
                      <template v-if="batch.published_at">
                        {{ batch.published_by }} · {{ formatDateTime(batch.published_at) }}
                      </template>
                      <template v-else>—</template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-if="scoreStore.lastSwitch" class="small muted" style="margin-top: 8px">
              上次切换：{{ scoreStore.lastSwitch.switched ? '成功' : '无需切换' }} ·
              现行版本数校验 = {{ scoreStore.lastSwitch.active_count }}（恒为 1）
              <template v-if="scoreStore.lastSwitch.previous">
                · 旧 v{{ scoreStore.lastSwitch.previous.policy_version }} 已归档
              </template>
            </p>
          </Plate>
        </div>

        <div class="stack">
          <Plate title="新建评分草稿" kicker="New draft" hint="同模型同参数重复执行直接复用，不新增版本；草稿不改变现行名单">
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
                {{ scoreStore.creating ? '评分中…' : auth.canScore ? '生成草稿名单' : '当前角色只读' }}
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
                <template v-if="selected?.lifecycle === SCORE_LIFECYCLE.ACTIVE">
                  现行策略 v{{ selected.policy_version }}，由 {{ selected.published_by }} 于
                  {{ formatDateTime(selected.published_at) }} 发布；风险图与导出均跟随此版本。
                </template>
                <template v-else-if="selected?.lifecycle === SCORE_LIFECYCLE.ARCHIVED">
                  历史版本 v{{ selected.policy_version }}，已被新版本接替，永久保留但不再生效，不能重复发布或导出。
                </template>
                <template v-else>
                  草稿仅用于候选对比；点击「发布并一次性切换」后，旧现行策略原子归档，本草稿成为唯一现行版本。
                </template>
              </p>
            </template>
          </Plate>
        </div>
      </div>
    </div>
  </AppShell>
</template>
