export interface FeatureStat {
  key: string;
  label: string;
  unit: string;
  direction: string;
  description: string;
  mean: number;
  std: number;
  min: number;
  max: number;
  missing: number;
  correlation: number;
}

export interface CategoricalStat {
  key: string;
  label: string;
  values: { value: string; count: number; churn_rate: number }[];
}

export interface FeatureStatistics {
  rows: number;
  target: string;
  target_label: string;
  positive_count: number;
  positive_rate: number;
  features: FeatureStat[];
  categoricals: CategoricalStat[];
  labels: Record<string, string>;
  months: string[];
}

export interface FeatureSet {
  id: number;
  name: string;
  version: number;
  description: string;
  target: string;
  train_months: string[];
  validation_month: string;
  numeric_keys: string[];
  categorical_keys: string[];
  status: string;
  created_by: string;
  created_at: string | null;
}

export interface FeatureCatalog {
  feature_set: FeatureSet | null;
  statistics: FeatureStatistics;
  catalog: { numeric: unknown[]; categorical: unknown[] };
  counts: { accounts: number; rows: number };
}
