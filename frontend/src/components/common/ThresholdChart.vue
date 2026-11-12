<script setup lang="ts">
import { computed } from 'vue';
import type { ThresholdPoint } from '@/types/model';

const props = defineProps<{ scan: ThresholdPoint[]; active: number }>();

const width = 640;
const height = 300;
const pad = 40;

function x(threshold: number): number {
  return pad + ((threshold - 0.1) / 0.8) * (width - pad * 2);
}

function y(value: number): number {
  return height - pad - value * (height - pad * 2);
}

const precision = computed(() => props.scan.map((point) => `${x(point.threshold)},${y(point.precision)}`).join(' '));
const recall = computed(() => props.scan.map((point) => `${x(point.threshold)},${y(point.recall)}`).join(' '));
const f1 = computed(() => props.scan.map((point) => `${x(point.threshold)},${y(point.f1)}`).join(' '));
const activePoint = computed(() => props.scan.reduce((best, point) => (Math.abs(point.threshold - props.active) < Math.abs(best.threshold - props.active) ? point : best), props.scan[0]));
const ticks = [0, 0.25, 0.5, 0.75, 1];
const thresholds = [0.1, 0.3, 0.5, 0.7, 0.9];
</script>

<template>
  <div v-if="scan.length" class="chart-frame">
    <svg :viewBox="`0 0 ${width} ${height}`" role="img" aria-label="阈值扫描：精确率 / 召回率 / F1">
      <g stroke="oklch(84% 0.026 86)" stroke-width="1">
        <line v-for="tick in ticks" :key="`h${tick}`" :x1="pad" :x2="width - pad" :y1="y(tick)" :y2="y(tick)" />
      </g>
      <polyline :points="precision" fill="none" stroke="oklch(33% 0.072 266)" stroke-width="2" />
      <polyline :points="recall" fill="none" stroke="oklch(47% 0.045 200)" stroke-width="2" />
      <polyline :points="f1" fill="none" stroke="oklch(52% 0.095 45)" stroke-width="2" stroke-dasharray="5 3" />
      <line :x1="x(active)" :x2="x(active)" y1="18" :y2="height - pad" stroke="oklch(28% 0.052 266)" stroke-dasharray="3 3" />
      <circle :cx="x(active)" :cy="y(activePoint?.f1 ?? 0)" r="4" fill="oklch(52% 0.095 45)" />
      <text :x="x(active) + 6" y="26" font-size="10" fill="oklch(28% 0.052 266)">阈值 {{ active.toFixed(2) }}</text>
      <text v-for="threshold in thresholds" :key="threshold" :x="x(threshold)" :y="height - pad + 15" text-anchor="middle" font-size="10" fill="oklch(52% 0.032 260)">{{ threshold.toFixed(1) }}</text>
      <text v-for="tick in ticks" :key="`y${tick}`" :x="pad - 8" :y="y(tick) + 4" text-anchor="end" font-size="10" fill="oklch(52% 0.032 260)">{{ tick }}</text>
      <line :x1="pad" :x2="width - pad" :y1="height - pad" :y2="height - pad" stroke="oklch(38% 0.045 264)" />
      <line :x1="pad" :x2="pad" :y1="pad" :y2="height - pad" stroke="oklch(38% 0.045 264)" />
      <text :x="width / 2" :y="height - 6" text-anchor="middle" font-size="10.5" fill="oklch(38% 0.045 264)">判定阈值</text>
    </svg>
    <div class="chart-legend">
      <span><i style="background: oklch(33% 0.072 266)" />精确率 Precision</span>
      <span><i style="background: oklch(47% 0.045 200)" />召回率 Recall</span>
      <span><i style="background: oklch(52% 0.095 45)" />F1</span>
      <span v-if="activePoint">阈值 {{ active.toFixed(2) }}：P {{ (activePoint.precision * 100).toFixed(1) }}% · R {{ (activePoint.recall * 100).toFixed(1) }}% · F1 {{ (activePoint.f1 * 100).toFixed(1) }}%</span>
    </div>
  </div>
  <div v-else class="loading">训练批次尚未产出阈值扫描</div>
</template>
