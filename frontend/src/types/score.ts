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

export interface ScoreBatch {
  id: number;
  batch_no: number;
  label: string;
  model_run_id: number;
  status: string;
  threshold: number;
  budget_total: number;
  cost_per_account: number;
  retention_lift: number;
  bands: { low_max: number; high_min: number };
  summary: ScoreSummary;
  selected_count: number;
  published: boolean;
  published_by: string;
  published_at: string | null;
  created_by: string;
  created_at: string | null;
  results?: unknown[];
}
