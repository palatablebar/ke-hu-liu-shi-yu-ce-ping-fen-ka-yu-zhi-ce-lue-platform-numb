<script setup lang="ts">
import type { Confusion } from '@/types/model';

defineProps<{ confusion: Confusion; threshold: number }>();
</script>

<template>
  <div class="chart-frame">
    <table class="ledger">
      <thead>
        <tr>
          <th />
          <th>预测流失</th>
          <th>预测留存</th>
          <th>合计</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>实际流失</td>
          <td style="color: var(--danger)">TP {{ confusion.tp }}</td>
          <td>FN {{ confusion.fn }}</td>
          <td>{{ confusion.tp + confusion.fn }}</td>
        </tr>
        <tr>
          <td>实际留存</td>
          <td>FP {{ confusion.fp }}</td>
          <td style="color: var(--ok)">TN {{ confusion.tn }}</td>
          <td>{{ confusion.fp + confusion.tn }}</td>
        </tr>
        <tr>
          <td>合计</td>
          <td>{{ confusion.tp + confusion.fp }}</td>
          <td>{{ confusion.fn + confusion.tn }}</td>
          <td>{{ confusion.tp + confusion.fp + confusion.fn + confusion.tn }}</td>
        </tr>
      </tbody>
    </table>
    <div class="chips" style="margin-top: 10px">
      <span class="chip">阈值 {{ threshold.toFixed(2) }}</span>
      <span class="chip">精确率 {{ (confusion.precision * 100).toFixed(1) }}%</span>
      <span class="chip">召回率 {{ (confusion.recall * 100).toFixed(1) }}%</span>
      <span class="chip">F1 {{ (confusion.f1 * 100).toFixed(1) }}%</span>
      <span class="chip">命中 {{ confusion.flagged }} 家</span>
    </div>
  </div>
</template>
