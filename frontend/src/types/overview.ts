import type { FeatureCatalog, FeatureStat } from './feature';
import type { ModelRun } from './model';
import type { ScoreBatch } from './score';

export interface Overview {
  brand: string;
  accounts: number;
  feature_rows: number;
  model_count: number;
  score_count: number;
  churn_rate: number;
  churn_positive_rows: number;
  latest_model: ModelRun | null;
  latest_batch: ScoreBatch | null;
  owners: { name: string; accounts: number }[];
  top_features: FeatureStat[];
  months: string[];
  target: string;
  target_label: string;
  role_scope: string;
  feature_catalog: FeatureCatalog;
  models: ModelRun[];
  score_batches: ScoreBatch[];
}
