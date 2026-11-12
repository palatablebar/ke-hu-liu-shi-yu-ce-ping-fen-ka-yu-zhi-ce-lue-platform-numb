<script setup lang="ts">
import { computed } from 'vue';
import type { Coefficient } from '@/types/model';
import { FEATURE_LABELS } from '@/constants/features';

const props = defineProps<{ coefficients: Coefficient[]; limit?: number }>();

interface Item {
  name: string;
  label: string;
  value: number;
  width: number;
  positive: boolean;
}

const maxAbs = computed(() => Math.max(...props.coefficients.filter((item) => item.group !== 'intercept').map((item) => Math.abs(item.coefficient)), 0.001));

const items = computed<Item[]>(() =>
  props.coefficients
    .filter((item) => item.group !== 'intercept')
    .sort((a, b) => Math.abs(b.coefficient) - Math.abs(a.coefficient))
    .slice(0, props.limit || 16)
    .map((item) => {
      const label = item.name.includes('=') ? item.name.split('=')[1] : FEATURE_LABELS[item.name] || item.name;
      return {
        name: item.name,
        label,
        value: item.coefficient,
        width: Math.min(100, (Math.abs(item.coefficient) / maxAbs.value) * 100),
        positive: item.coefficient >= 0,
      };
    }),
);
</script>

<template>
  <div class="stack" style="gap: 8px">
    <div v-for="item in items" :key="item.name" style="display: grid; grid-template-columns: 160px minmax(0, 1fr) 78px; gap: 10px; align-items: center; font-size: 0.74rem">
      <span class="small">{{ item.label }}<span v-if="item.name.includes('=')" class="muted">（one-hot）</span></span>
      <div style="position: relative; height: 12px; background: oklch(88% 0.024 88)">
        <div
          :style="{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: item.positive ? '50%' : `${50 - item.width / 2}%`,
            width: `${item.width / 2}%`,
            background: item.positive ? 'oklch(48% 0.12 28)' : 'oklch(47% 0.06 152)',
          }"
        />
        <div style="position: absolute; left: 50%; top: -2px; bottom: -2px; width: 1px; background: oklch(52% 0.032 260)" />
      </div>
      <span class="mono" style="text-align: right" :style="{ color: item.positive ? 'var(--danger)' : 'var(--ok)' }">{{ item.value.toFixed(3) }}</span>
    </div>
    <p class="small muted">红条 = 推高流失概率，绿条 = 降低流失概率；按标准化后的系数排序（L2 已加）。</p>
  </div>
</template>
