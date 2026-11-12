<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import AppShell from '@/components/common/AppShell.vue';
import Plate from '@/components/common/Plate.vue';
import RiskTable from '@/components/common/RiskTable.vue';
import AccountDrawer from '@/components/common/AccountDrawer.vue';
import PaginationBar from '@/components/common/PaginationBar.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorNotice from '@/components/common/ErrorNotice.vue';
import StatusSeal from '@/components/common/StatusSeal.vue';
import { useAuthStore } from '@/stores/auth';
import { useAccountStore } from '@/stores/account';
import { useDebouncedSearch } from '@/hooks/useDebouncedSearch';
import { useAsyncResource } from '@/hooks/useAsyncResource';
import { fetchOverview } from '@/api/meta';
import type { Overview } from '@/types/overview';
import type { RiskRow } from '@/types/account';
import { RISK_BAND_LABELS, RISK_BAND_ORDER, RISK_BAND_TONE } from '@/constants/riskBand';
import { formatDate } from '@/utils/formatDate';

const auth = useAuthStore();
const store = useAccountStore();
const { keyword, debounced } = useDebouncedSearch('');
const band = ref('');
const pageNo = ref(1);
const drawerOpen = ref(false);
const selectedKey = ref('');
const { data: overviewData, run: loadOverview } = useAsyncResource<Overview>(null);

const summary = computed(() => store.page?.batch?.summary || null);
const bandSizes = computed(() => summary.value?.band_sizes || {});
const totalBand = computed(() => Object.values(bandSizes.value).reduce((sum, value) => sum + value, 0) || 1);

function load() {
  store.load(debounced.value, band.value, pageNo.value, 20);
}

function openDetail(row: RiskRow) {
  selectedKey.value = row.account_code;
  drawerOpen.value = true;
  store.loadDetail(row.account_code);
}

watch([debounced, band], () => {
  pageNo.value = 1;
  load();
});
watch(pageNo, load);

onMounted(async () => {
  await Promise.all([load(), loadOverview(() => fetchOverview())]);
});
</script>

<template>
  <AppShell>
    <header class="page__head reveal">
      <div>
        <p class="eyebrow">Chart sheet 01 · Risk</p>
        <h1 class="page__title">客户风险图</h1>
        <p class="page__kicker">
          名单只跟随已发布的<strong>现行策略</strong>，按流失概率从高到低排列；草稿调整在发布前不会出现在这里。
          {{ auth.isCsm ? '你的账号只看得到自己名下客户（服务端按 CSM 过滤）。' : '点开任意客户能看到概率、风险档与三条原因。' }}
        </p>
      </div>
      <div class="page__meta">
        现行策略：{{ store.page?.batch ? `v${store.page.batch.policy_version ?? '—'} · 阈值 ${store.page.batch.threshold}` : '尚未发布' }}<br />
        评分客户：{{ summary?.scored ?? '—' }} 家 · 高风险 {{ summary?.high_risk ?? '—' }} 家
      </div>
    </header>

    <div class="page__body">
      <ErrorNotice v-if="store.error" :message="store.error" @retry="load()" />

      <div class="split split--main">
        <Plate title="风险名单" kicker="Risk roster" hint="按概率降序 · 显示 Top1 原因与预算内排名">
          <template #actions>
            <StatusSeal :label="auth.isCsm ? '仅自己客户' : '全量名单'" :tone="auth.isCsm ? 'seal--medium' : 'seal--indigo'" />
          </template>

          <div class="toolbar" style="margin-bottom: 10px">
            <div class="field toolbar__grow">
              <span class="field__label">搜索客户 / 编号</span>
              <input v-model="keyword" class="input" placeholder="海岳科技 / ACC-0130" />
            </div>
            <div class="field">
              <span class="field__label">风险档</span>
              <select v-model="band" class="select" style="min-width: 120px">
                <option value="">全部风险档</option>
                <option v-for="item in RISK_BAND_ORDER" :key="item" :value="item">{{ RISK_BAND_LABELS[item] }}</option>
              </select>
            </div>
          </div>

          <div v-if="store.loading && !store.page" class="loading">读取评分名单…</div>
          <EmptyState
            v-else-if="!store.page || !store.page.items.length"
            title="没有匹配的客户"
            text="清空筛选，或确认是否已发布现行策略（草稿不会驱动风险名单）。"
          >
            <button class="btn btn--small" style="margin-top: 10px" type="button" @click="keyword = ''; band = ''; load()">清空筛选</button>
          </EmptyState>
          <template v-else>
            <RiskTable :rows="store.page.items" :selected-key="selectedKey" @select="openDetail" />
            <PaginationBar
              :page="store.page.page"
              :pages="store.page.pages"
              :total="store.page.total"
              :page-size="store.page.page_size"
              @change="pageNo = $event"
            />
          </template>
        </Plate>

        <div class="stack">
          <Plate title="批次摘要" kicker="Batch summary" hint="阈值与预算决定触达范围">
            <div v-if="!summary" class="loading">暂无评分批次</div>
            <template v-else>
              <div class="grid-stats" style="grid-template-columns: 1fr 1fr">
                <div class="stat">
                  <span class="stat__label">高风险</span>
                  <span class="stat__value" style="color: var(--danger)">{{ summary.high_risk }}</span>
                  <span class="stat__note">P ≥ {{ summary.threshold }}</span>
                </div>
                <div class="stat">
                  <span class="stat__label">预算内名单</span>
                  <span class="stat__value">{{ summary.selected_count }}</span>
                  <span class="stat__note">K = {{ summary.k }} · 预算 ¥{{ summary.budget_total }}</span>
                </div>
                <div class="stat">
                  <span class="stat__label">预期挽回</span>
                  <span class="stat__value" style="font-size: 1.1rem">¥{{ (summary.total_expected_save / 10000).toFixed(1) }}万</span>
                  <span class="stat__note">人均 ¥{{ summary.avg_expected_save.toFixed(0) }}</span>
                </div>
                <div class="stat">
                  <span class="stat__label">验证 AUC</span>
                  <span class="stat__value">{{ summary.model_auc.toFixed(4) }}</span>
                  <span class="stat__note">样本外第 5 月</span>
                </div>
              </div>
              <p class="small muted" style="margin-top: 10px">
                期望挽回口径：{{ summary.expected_save_formula }}（可挽留比例 {{ summary.retention_lift }}）
              </p>
            </template>
          </Plate>

          <Plate title="风险分档" kicker="Risk bands" hint="按评分三等分；档内 lift = 档均分 / 全体均分">
            <div v-if="!bandSizes.high" class="loading">暂无分档</div>
            <div v-else class="stack" style="gap: 10px">
              <div v-for="item in RISK_BAND_ORDER" :key="item">
                <div class="spread small">
                  <span>
                    <StatusSeal :label="RISK_BAND_LABELS[item]" :tone="RISK_BAND_TONE[item]" />
                    　lift {{ (summary?.band_lift?.[item] ?? 0).toFixed(2) }}
                  </span>
                  <span class="numeral">{{ bandSizes[item] }} 家</span>
                </div>
                <div class="check-bar" style="margin-top: 4px">
                  <div class="check-bar__fill" :class="{ 'check-bar__fill--warn': item === 'high' }" :style="{ width: `${Math.round(((bandSizes[item] || 0) / totalBand) * 100)}%` }" />
                </div>
              </div>
              <div class="legend" style="margin-top: 4px">
                <span><i class="is-high" />高风险</span>
                <span><i class="is-medium" />中风险</span>
                <span><i class="is-low" />低风险</span>
              </div>
            </div>
          </Plate>

          <Plate title="海图注记" kicker="Chart note">
            <div class="stack" style="gap: 8px">
              <p class="small">
                名单只回答「先找谁」，不回答「一定流失」。触达前请核对工单与合同条款；
                CSM 的客户由 <span class="mono">csm_owner_email</span> 归属。
              </p>
              <p class="small muted">
                现行策略发布于：{{ store.page?.batch ? formatDate(store.page.batch.published_at || store.page.batch.created_at) : '—' }} ·
                策略版本 v{{ store.page?.batch?.policy_version ?? '—' }} · 模型批次 #{{ store.page?.batch?.model_run_id ?? '—' }}
              </p>
              <p class="small muted">
                整体流失率 {{ ((overviewData?.churn_rate ?? 0) * 100).toFixed(1) }}%（5 个月 1200 行特征）。
              </p>
            </div>
          </Plate>
        </div>
      </div>
    </div>

    <AccountDrawer v-if="drawerOpen" :detail="store.detail" :loading="store.detailLoading" @close="drawerOpen = false" />
  </AppShell>
</template>
