<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import AppShell from '@/components/common/AppShell.vue';
import Plate from '@/components/common/Plate.vue';
import StatusSeal from '@/components/common/StatusSeal.vue';
import RocChart from '@/components/common/RocChart.vue';
import ThresholdChart from '@/components/common/ThresholdChart.vue';
import ConfusionMatrix from '@/components/common/ConfusionMatrix.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorNotice from '@/components/common/ErrorNotice.vue';
import { useAuthStore } from '@/stores/auth';
import { useModelStore } from '@/stores/model';
import { MODEL_STATUS_LABELS, MODEL_STATUS_TONE } from '@/constants/modelStatus';
import { formatDateTime, durationSeconds } from '@/utils/formatDate';
import { sleep } from '@/utils/sleep';

const auth = useAuthStore();
const store = useModelStore();

const notice = ref('');
const showTrain = ref(false);
const learningRate = ref(0.15);
const l2 = ref(0.02);
const epochs = ref(1800);

const detail = computed(() => store.selected);
const metrics = computed(() => detail.value?.metrics || null);
const confusion = computed(() => metrics.value?.confusion_035 || null);

onMounted(() => store.load());

async function startTrain() {
  notice.value = '';
  try {
    const run = await store.train({
      learning_rate: learningRate.value,
      l2: l2.value,
      epochs: epochs.value,
    });
    notice.value = `训练批次 #${run.run_no} 已提交到 Celery worker，等待评估指标…`;
    const finished = await store.poll(run.id);
    if (finished?.status === 'succeeded') {
      notice.value = `训练完成：AUC ${finished.metrics.auc}，PR-AUC ${finished.metrics.pr_auc}，验证月 ${finished.metrics.validation_rows} 行 / 正例 ${finished.metrics.validation_positives}。`;
    } else if (finished) {
      notice.value = `训练失败：${finished.error_message || '未知错误'}`;
    }
    await store.load();
  } catch (err) {
    notice.value = err instanceof Error ? err.message : '发起训练失败';
  }
}
</script>

<template>
  <AppShell>
    <header class="page__head reveal">
      <div>
        <p class="eyebrow">Chart sheet 02 · Evaluation</p>
        <h1 class="page__title">模型评估</h1>
        <p class="page__kicker">
          numpy 手写逻辑回归：标准化与 one-hot 只用前 4 个月拟合，第 5 个月留作验证；曲线全部由后端返回的散点自绘。
        </p>
      </div>
      <div class="page__meta">
        最近训练：{{ store.models[0] ? `#${store.models[0].run_no} ${MODEL_STATUS_LABELS[store.models[0].status]}` : '—' }}<br />
        训练权限：{{ auth.canTrain ? '可发起' : '只读（analyst/admin 之外 403）' }}
      </div>
    </header>

    <div class="page__body">
      <ErrorNotice v-if="store.error" :message="store.error" @retry="store.load()" />
      <p v-if="notice" class="note-line">{{ notice }}</p>

      <div class="split split--eval">
        <Plate title="训练批次" kicker="Model runs" hint="按运行顺序倒排">
          <template #actions>
            <button class="btn btn--primary btn--small" type="button" :disabled="!auth.canTrain" @click="showTrain = !showTrain">
              {{ showTrain ? '收起' : '发起训练' }}
            </button>
          </template>

          <form v-if="showTrain" class="stack" style="margin-bottom: 12px" @submit.prevent="startTrain">
            <div class="row" style="gap: 8px">
              <div class="field" style="flex: 1">
                <span class="field__label">学习率</span>
                <input v-model.number="learningRate" class="input" type="number" step="0.01" min="0.01" max="2" />
              </div>
              <div class="field" style="flex: 1">
                <span class="field__label">L2</span>
                <input v-model.number="l2" class="input" type="number" step="0.005" min="0" max="1" />
              </div>
              <div class="field" style="flex: 1">
                <span class="field__label">迭代轮数</span>
                <input v-model.number="epochs" class="input" type="number" step="100" min="100" max="6000" />
              </div>
            </div>
            <button class="btn btn--rust btn--small" type="submit" :disabled="store.training">
              {{ store.training ? '提交中…' : '提交训练（Celery）' }}
            </button>
            <p v-if="!auth.canTrain" class="small muted">当前角色不能发起训练，服务端会返回 403。</p>
          </form>

          <div v-if="store.loading && !store.models.length" class="loading">读取训练批次…</div>
          <EmptyState v-else-if="!store.models.length" title="还没有训练批次" text="seed 会写入基线批次；分析师也可以手动发起训练。" />
          <div v-else class="stack" style="gap: 8px">
            <button
              v-for="run in store.models"
              :key="run.id"
              type="button"
              class="plate"
              style="padding: 10px 12px; text-align: left; cursor: pointer; width: 100%; border-color: var(--rule-soft)"
              :style="{ borderColor: run.id === detail?.id ? 'var(--rust)' : 'var(--rule-soft)' }"
              @click="store.select(run.id)"
            >
              <div class="spread">
                <span class="numeral">No. {{ run.run_no }}</span>
                <StatusSeal :label="MODEL_STATUS_LABELS[run.status]" :tone="MODEL_STATUS_TONE[run.status]" />
              </div>
              <p class="small" style="margin-top: 4px">{{ run.label }}</p>
              <p class="small muted">
                AUC {{ run.metrics?.auc ?? '—' }} · PR {{ run.metrics?.pr_auc ?? '—' }}
              </p>
              <p class="small muted">{{ formatDateTime(run.finished_at || run.created_at) }}</p>
            </button>
          </div>
        </Plate>

        <div class="stack">
          <Plate title="批次指标" kicker="Metrics" :hint="detail?.warning || ''">
            <template #actions>
              <StatusSeal v-if="detail" :label="MODEL_STATUS_LABELS[detail.status]" :tone="MODEL_STATUS_TONE[detail.status]" />
            </template>
            <div v-if="!detail" class="loading">选择一个训练批次查看指标…</div>
            <template v-else>
              <p v-if="detail.warning" class="form-error" style="margin-bottom: 10px">{{ detail.warning }}</p>
              <div class="grid-stats" style="grid-template-columns: repeat(3, minmax(0, 1fr))">
                <div class="stat">
                  <span class="stat__label">AUC</span>
                  <span class="stat__value">{{ detail.metrics.auc?.toFixed(4) ?? '—' }}</span>
                  <span class="stat__note">梯形积分 · 样本外</span>
                </div>
                <div class="stat">
                  <span class="stat__label">PR-AUC</span>
                  <span class="stat__value">{{ detail.metrics.pr_auc?.toFixed(4) ?? '—' }}</span>
                  <span class="stat__note">正例稀少时更敏感</span>
                </div>
                <div class="stat">
                  <span class="stat__label">训练 / 验证</span>
                  <span class="stat__value" style="font-size: 1.02rem">{{ detail.metrics.train_rows }} / {{ detail.metrics.validation_rows }}</span>
                  <span class="stat__note">前 4 月 / 第 5 月</span>
                </div>
                <div class="stat">
                  <span class="stat__label">正例率</span>
                  <span class="stat__value" style="font-size: 1.02rem">{{ (detail.metrics.train_positive_rate * 100).toFixed(1) }}%</span>
                  <span class="stat__note">验证 {{ (detail.metrics.validation_positive_rate * 100).toFixed(1) }}%</span>
                </div>
                <div class="stat">
                  <span class="stat__label">阈值 0.35 命中</span>
                  <span class="stat__value">{{ detail.metrics.high_risk_at_035 }}</span>
                  <span class="stat__note">家 · 待触达池</span>
                </div>
                <div class="stat">
                  <span class="stat__label">耗时</span>
                  <span class="stat__value" style="font-size: 1.02rem">{{ durationSeconds(detail.started_at, detail.finished_at) ?? '—' }}s</span>
                  <span class="stat__note">GD {{ detail.hyperparams.epochs }} 轮</span>
                </div>
              </div>
              <p class="small muted" style="margin-top: 10px">
                学习率 {{ detail.hyperparams.learning_rate }} · L2 {{ detail.hyperparams.l2 }} ·
                触发人 {{ detail.created_by }} · 输入 {{ detail.train_rows }} 行训练 / {{ detail.validation_rows }} 行验证
              </p>
            </template>
          </Plate>

          <Plate title="ROC 曲线" kicker="ROC" hint="横轴假阳率、纵轴真阳率，由验证月散点连线">
            <RocChart v-if="detail?.roc_points?.length" :points="detail.roc_points" :auc="detail.metrics.auc" />
            <div v-else class="loading">该批次没有 ROC 数据</div>
          </Plate>

          <Plate title="阈值 - 精确率 / 召回率" kicker="Threshold scan" hint="0.10 ~ 0.90 逐点扫描；虚线为当前策略阈值">
            <ThresholdChart v-if="detail?.threshold_scan?.length" :scan="detail.threshold_scan" :active="0.35" />
            <div v-else class="loading">该批次没有阈值扫描</div>
          </Plate>

          <Plate title="混淆矩阵（阈值 0.35）" kicker="Confusion" hint="验证月真实标签 vs 预测标签">
            <ConfusionMatrix v-if="confusion" :confusion="confusion" :threshold="0.35" />
            <div v-else class="loading">暂无混淆矩阵</div>
          </Plate>
        </div>
      </div>
    </div>
  </AppShell>
</template>
