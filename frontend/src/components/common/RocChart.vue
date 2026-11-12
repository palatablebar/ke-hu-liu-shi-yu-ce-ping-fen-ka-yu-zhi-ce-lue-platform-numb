<script setup lang="ts">
import { computed } from 'vue';
import type { RocPoint } from '@/types/model';

const props = defineProps<{ points: RocPoint[]; auc: number }>();

const width = 460;
const height = 340;
const pad = 42;

const path = computed(() => {
  if (!props.points.length) return '';
  return props.points
    .map((point, index) => {
      const x = pad + point.fpr * (width - pad * 2);
      const y = height - pad - point.tpr * (height - pad * 2);
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
});

const ticks = [0, 0.25, 0.5, 0.75, 1];
</script>

<template>
  <div class="chart-frame">
    <svg :viewBox="`0 0 ${width} ${height}`" role="img" aria-label="ROC 曲线">
      <g stroke="oklch(84% 0.026 86)" stroke-width="1">
        <line v-for="tick in ticks" :key="`h${tick}`" :x1="pad" :x2="width - pad" :y1="height - pad - tick * (height - pad * 2)" :y2="height - pad - tick * (height - pad * 2)" />
        <line v-for="tick in ticks" :key="`v${tick}`" :x1="pad + tick * (width - pad * 2)" :x2="pad + tick * (width - pad * 2)" :y1="pad" :y2="height - pad" />
      </g>
      <line :x1="pad" :x2="width - pad" :y1="height - pad" :y2="pad" stroke="oklch(64% 0.024 258)" stroke-dasharray="4 4" />
      <path :d="path" fill="none" stroke="oklch(33% 0.072 266)" stroke-width="2.4" />
      <line :x1="pad" :x2="width - pad" :y1="height - pad" :y2="height - pad" stroke="oklch(38% 0.045 264)" />
      <line :x1="pad" :x2="pad" :y1="pad" :y2="height - pad" stroke="oklch(38% 0.045 264)" />
      <text v-for="tick in ticks" :key="`lt${tick}`" :x="pad + tick * (width - pad * 2)" :y="height - pad + 16" text-anchor="middle" font-size="10" fill="oklch(52% 0.032 260)">{{ tick }}</text>
      <text v-for="tick in ticks" :key="`ly${tick}`" :x="pad - 10" :y="height - pad - tick * (height - pad * 2) + 4" text-anchor="end" font-size="10" fill="oklch(52% 0.032 260)">{{ tick }}</text>
      <text :x="width / 2" :y="height - 8" text-anchor="middle" font-size="10.5" fill="oklch(38% 0.045 264)">假阳率 FPR</text>
      <text :x="14" :y="height / 2" text-anchor="middle" font-size="10.5" fill="oklch(38% 0.045 264)" :transform="`rotate(-90 14 ${height / 2})`">真阳率 TPR</text>
      <text :x="pad + 12" :y="pad + 26" font-family="Marcellus, Georgia, serif" font-size="24" fill="oklch(28% 0.052 266)">AUC {{ auc.toFixed(4) }}</text>
    </svg>
    <div class="chart-legend">
      <span><i style="background: oklch(33% 0.072 266)" />验证月 ROC（第 5 个月，样本外）</span>
      <span><i style="background: oklch(64% 0.024 258)" />随机基线</span>
    </div>
  </div>
</template>
