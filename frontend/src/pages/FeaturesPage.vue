<script setup lang="ts">
import { computed, onMounted } from 'vue';
import AppShell from '@/components/common/AppShell.vue';
import Plate from '@/components/common/Plate.vue';
import StatusSeal from '@/components/common/StatusSeal.vue';
import CoefficientBars from '@/components/common/CoefficientBars.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorNotice from '@/components/common/ErrorNotice.vue';
import { useFeatureStore } from '@/stores/feature';
import { useModelStore } from '@/stores/model';

const featureStore = useFeatureStore();
const modelStore = useModelStore();

const catalog = computed(() => featureStore.catalog);
const statistics = computed(() => catalog.value?.statistics || null);
const latestModel = computed(() => modelStore.models.find((model) => model.status === 'succeeded') || null);

onMounted(async () => {
  await Promise.all([featureStore.load(), modelStore.load()]);
});
</script>

<template>
  <AppShell>
    <header class="page__head reveal">
      <div>
        <p class="eyebrow">Chart sheet 03 · Features</p>
        <h1 class="page__title">特征与权重</h1>
        <p class="page__kicker">
          12 个数值特征 + 3 组 one-hot 类别特征；相关系数是月度特征与流失标签的 Pearson 值，系数来自最新逻辑回归批次。
        </p>
      </div>
      <div class="page__meta">
        特征集：{{ catalog?.feature_set?.name || '—' }} v{{ catalog?.feature_set?.version || '—' }}<br />
        训练 {{ catalog?.feature_set?.train_months?.join(' / ') }} → 验证 {{ catalog?.feature_set?.validation_month }}
      </div>
    </header>

    <div class="page__body">
      <ErrorNotice v-if="featureStore.error" :message="featureStore.error" @retry="featureStore.load()" />
      <div v-if="!catalog" class="loading">读取特征目录…</div>
      <template v-else>
        <div class="grid-stats">
          <div class="stat">
            <span class="stat__label">客户数</span>
            <span class="stat__value">{{ catalog.counts.accounts }}</span>
            <span class="stat__note">240 家 SaaS 客户</span>
          </div>
          <div class="stat">
            <span class="stat__label">特征行</span>
            <span class="stat__value">{{ catalog.counts.rows }}</span>
            <span class="stat__note">5 个月 × 240 家</span>
          </div>
          <div class="stat">
            <span class="stat__label">验证月正例率</span>
            <span class="stat__value">{{ ((statistics?.positive_rate ?? 0) * 100).toFixed(1) }}%</span>
            <span class="stat__note">标签：未来 30 天流失</span>
          </div>
          <div class="stat">
            <span class="stat__label">最新批次 AUC</span>
            <span class="stat__value">{{ latestModel?.metrics?.auc?.toFixed(4) ?? '—' }}</span>
            <span class="stat__note">{{ latestModel ? `#${latestModel.run_no}` : '尚无模型' }}</span>
          </div>
        </div>

        <div class="split" style="grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)">
          <Plate title="回归系数（最新批次）" kicker="Coefficients" hint="标准化后系数；红=推高流失，绿=降低流失">
            <CoefficientBars v-if="latestModel?.coefficients?.length" :coefficients="latestModel.coefficients" :limit="16" />
            <EmptyState v-else title="还没有训练批次" text="去模型评估页发起一次训练，这里会出现系数。" />
          </Plate>

          <Plate title="数值特征统计" kicker="Feature statistics" hint="均值 / 标准差 / 与流失标签相关系数">
            <div class="ledger-wrap" style="max-height: 420px">
              <table class="ledger">
                <thead>
                  <tr>
                    <th>特征</th>
                    <th>均值</th>
                    <th>标准差</th>
                    <th>相关系数</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="feature in statistics?.features || []" :key="feature.key">
                    <td>
                      <div>{{ feature.label }}</div>
                      <div class="small muted">{{ feature.key }} · {{ feature.direction === 'higher_worse' ? '越高越危险' : '越低越危险' }}</div>
                    </td>
                    <td class="mono">{{ feature.mean }}</td>
                    <td class="mono">{{ feature.std }}</td>
                    <td class="mono" :style="{ color: feature.correlation > 0 ? 'var(--danger)' : 'var(--ok)' }">
                      {{ feature.correlation > 0 ? '+' : '' }}{{ feature.correlation }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Plate>
        </div>

        <Plate title="类别特征与流失率" kicker="Categorical lift" hint="每个取值的客户数与历史流失率">
          <div class="split" style="grid-template-columns: repeat(auto-fit, minmax(260px, 1fr))">
            <div v-for="group in statistics?.categoricals || []" :key="group.key">
              <p class="small"><strong>{{ group.label }}</strong></p>
              <div class="stack" style="gap: 6px; margin-top: 6px">
                <div v-for="item in group.values" :key="item.value">
                  <div class="spread small">
                    <span>{{ item.value }}</span>
                    <span class="mono">{{ item.count }} 家 · {{ (item.churn_rate * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="check-bar" style="margin-top: 3px">
                    <div class="check-bar__fill" :class="{ 'check-bar__fill--warn': item.churn_rate > (statistics?.positive_rate ?? 0.2) }" :style="{ width: `${Math.min(100, item.churn_rate * 260)}%` }" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Plate>

        <Plate title="特征集口径" kicker="Method" hint="时间切分与防泄漏">
          <div class="stack" style="gap: 8px">
            <p class="small">
              训练集 = {{ catalog.feature_set?.train_months?.join(' / ') }}（4 个月 × 240 家 = 960 行）；
              验证集 = {{ catalog.feature_set?.validation_month }}（240 行）。标准化参数（均值/标准差）只在训练集上估计，再应用到验证集。
            </p>
            <div class="chips">
              <span v-for="key in catalog.feature_set?.numeric_keys || []" :key="key" class="chip">{{ key }}</span>
              <span v-for="key in catalog.feature_set?.categorical_keys || []" :key="key" class="chip">{{ key }} (one-hot)</span>
            </div>
            <p class="small muted">缺失值按 0 处理；演示数据没有缺失，特征说明见 README。</p>
            <div class="row">
              <StatusSeal :label="catalog.feature_set?.status === 'active' ? '启用中' : '草稿'" :tone="catalog.feature_set?.status === 'active' ? 'seal--low' : 'seal--neutral'" />
              <span class="small muted">created by {{ catalog.feature_set?.created_by }}</span>
            </div>
          </div>
        </Plate>
      </template>
    </div>
  </AppShell>
</template>
