export interface ScoreSummary {
  scored: number;
  high_risk: number;
  high_band: number;
  medium_band: number;
  low_band: number;
  threshold: number;
  budget_total: number;
  cost_per_account: number;
  k: number;
  selected_count: number;
  total_expected_save: number;
  avg_expected_save: number;
  overall_mean_score: number;
  band_lift: Record<string, number>;
  band_cuts: { low_max: number; high_min: number };
  band_sizes: Record<string, number>;
  account_rows: number;
  model_auc: number;
  expected_save_formula: string;
  retention_lift: number;
}

export type ScoreLifecycleValue = 'draft' | 'active' | 'archived';

export interface ScoreBatch {
  id: number;
  batch_no: number;
  label: string;
  model_run_id: number;
  status: string;
  // 草稿 / 现行策略 / 历史版本三态。
  lifecycle: ScoreLifecycleValue;
  // 发布后的单调策略版本号；草稿为 null。
  policy_version: number | null;
  // 把该版本切换下来的新批次 id（仅历史版本）。
  superseded_by: number | null;
  policy_fingerprint: string;
  threshold: number;
  budget_total: number;
  cost_per_account: number;
  retention_lift: number;
  bands: { low_max: number; high_min: number };
  summary: ScoreSummary;
  selected_count: number;
  // 兼容字段：lifecycle 为 active/archived 时为 true。
  published: boolean;
  is_active: boolean;
  reused?: boolean;
  published_by: string;
  published_at: string | null;
  created_by: string;
  created_at: string | null;
  results?: unknown[];
}
