<script setup lang="ts">
import type { AccountDetail } from '@/types/account';
import { RISK_BAND_TONE } from '@/constants/riskBand';
import { FEATURE_LABELS } from '@/constants/features';
import StatusSeal from './StatusSeal.vue';
import EmptyState from './EmptyState.vue';

defineProps<{ detail: AccountDetail | null; loading: boolean }>();
const emit = defineEmits<{ close: [] }>();

const trendKeys = ['usage_days', 'tickets_open', 'nps', 'invoice_overdue_days'];

function series(detail: AccountDetail, key: string): number[] {
  return detail.months.map((month) => Number(month.features[key] ?? 0));
}

function sparkPath(values: number[], width = 150, height = 40): string {
  if (!values.length) return '';
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * width;
      const y = height - ((value - min) / span) * (height - 6) - 3;
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}
</script>

<template>
  <div class="drawer-backdrop" @click.self="emit('close')">
    <aside class="drawer" role="dialog" aria-label="客户详情">
      <div class="spread" style="margin-bottom: 14px">
        <div>
          <p class="eyebrow">Customer plate · 客户分幅</p>
          <h2 class="page__title" style="font-size: var(--step-2)">{{ detail?.account.company_name || '…' }}</h2>
        </div>
        <button class="btn btn--small" type="button" @click="emit('close')">关闭</button>
      </div>

      <div v-if="loading" class="loading">正在读取客户剖面…</div>
      <EmptyState v-else-if="!detail" title="没有客户剖面" text="选择左侧名单中的一家客户。" />
      <template v-else>
        <div class="grid-stats">
          <div class="stat">
            <span class="stat__label">流失概率</span>
            <span class="stat__value">{{ detail.score ? detail.score.score.toFixed(3) : '—' }}</span>
            <span class="stat__note">{{ detail.score?.band_label || '未评分' }}</span>
          </div>
          <div class="stat">
            <span class="stat__label">年化合同额</span>
            <span class="stat__value" style="font-size: 1.15rem">¥{{ Math.round(detail.account.monthly_fee * 12 / 1000) }}k</span>
            <span class="stat__note">席位 {{ detail.account.seats }}</span>
          </div>
          <div class="stat">
            <span class="stat__label">CSM</span>
            <span class="stat__value" style="font-size: 1rem">{{ detail.account.csm_owner_name }}</span>
            <span class="stat__note">{{ detail.account.region }} · {{ detail.account.plan }}</span>
          </div>
        </div>

        <h3 class="plate__title" style="margin-top: 20px; font-size: 1rem">风险原因 Top3（系数 × 标准化值）</h3>
        <div class="stack" style="gap: 8px; margin-top: 8px">
          <div v-for="(reason, index) in detail.score?.reasons || []" :key="reason.feature" class="note-line">
            <span class="numeral">{{ index + 1 }}.</span>
            {{ FEATURE_LABELS[reason.feature] || reason.label }} = {{ reason.raw_value }}
            <span class="muted">（z={{ reason.z_value }}，贡献 {{ reason.contribution > 0 ? '+' : '' }}{{ reason.contribution }}）</span>
          </div>
          <p v-if="!detail.score?.reasons?.length" class="small muted">该客户未出现在最新评分批次中。</p>
        </div>

        <h3 class="plate__title" style="margin-top: 20px; font-size: 1rem">近 5 个月走势</h3>
        <div class="grid-stats" style="grid-template-columns: 1fr 1fr; margin-top: 8px">
          <div v-for="key in trendKeys" :key="key" class="stat" style="gap: 6px">
            <span class="stat__label">{{ FEATURE_LABELS[key] }}</span>
            <svg viewBox="0 0 150 40" preserveAspectRatio="none" style="width: 100%; height: 34px">
              <path :d="sparkPath(series(detail, key))" fill="none" stroke="oklch(33% 0.072 266)" stroke-width="1.6" />
            </svg>
            <span class="small muted">{{ series(detail, key).join(' → ') }}</span>
          </div>
        </div>

        <h3 class="plate__title" style="margin-top: 20px; font-size: 1rem">月度特征明细</h3>
        <div class="ledger-wrap" style="max-height: 220px; margin-top: 8px">
          <table class="ledger">
            <thead>
              <tr>
                <th>月份</th>
                <th>活跃天数</th>
                <th>未结工单</th>
                <th>NPS</th>
                <th>逾期天数</th>
                <th>标签</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="month in detail.months" :key="month.month">
                <td class="mono">{{ month.month }}</td>
                <td>{{ month.features.usage_days }}</td>
                <td>{{ month.features.tickets_open }}</td>
                <td>{{ month.features.nps }}</td>
                <td>{{ month.features.invoice_overdue_days }}</td>
                <td>
                  <StatusSeal v-if="month.churn_next_30d" label="实际流失" tone="seal--high" />
                  <StatusSeal v-else label="留存" tone="seal--low" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="small muted" style="margin-top: 10px">
          契约到期 {{ detail.account.contract_end }} · 风险档 {{ detail.score?.band_label || '—' }}（
          <StatusSeal :label="detail.score?.band_label || '未评分'" :tone="RISK_BAND_TONE[detail.score?.band || 'low'] || 'seal--neutral'" />
          ）
        </p>
      </template>
    </aside>
  </div>
</template>
