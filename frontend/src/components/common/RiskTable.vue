<script setup lang="ts">
import type { RiskRow } from '@/types/account';
import { RISK_BAND_TONE } from '@/constants/riskBand';
import StatusSeal from './StatusSeal.vue';

defineProps<{ rows: RiskRow[]; selectedKey?: string }>();
defineEmits<{ select: [row: RiskRow] }>();

function money(value: number): string {
  return value >= 10000 ? `${(value / 10000).toFixed(1)} 万` : `¥${value.toFixed(0)}`;
}
</script>

<template>
  <div class="ledger-wrap">
    <table class="ledger">
      <thead>
        <tr>
          <th>客户</th>
          <th>分数</th>
          <th>风险档</th>
          <th>年化合同额</th>
          <th>Top 原因</th>
          <th>预算内</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in rows"
          :key="row.account_code"
          class="is-clickable"
          :class="{ 'is-selected': selectedKey === row.account_code }"
          @click="$emit('select', row)"
        >
          <td>
            <div>{{ row.company_name }}</div>
            <div class="small muted ledger__code">{{ row.account_code }} · {{ row.industry }} · {{ row.plan }}</div>
          </td>
          <td>
            <div class="scorebar">
              <div class="scorebar__track"><div class="scorebar__fill" :style="{ width: `${Math.min(100, row.score * 100)}%` }" /></div>
              <span class="scorebar__value">{{ row.score.toFixed(3) }}</span>
            </div>
          </td>
          <td><StatusSeal :label="row.band_label" :tone="RISK_BAND_TONE[row.band] || 'seal--neutral'" /></td>
          <td class="mono small">{{ money(row.monthly_fee * 12) }}</td>
          <td class="small">{{ row.reasons[0]?.label || '—' }}</td>
          <td class="small">
            <span v-if="row.selected" style="color: var(--rust)">#{{ row.rank }}</span>
            <span v-else class="muted">—</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
