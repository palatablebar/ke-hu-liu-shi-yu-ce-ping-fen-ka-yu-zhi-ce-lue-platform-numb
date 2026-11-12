export interface Coefficient {
  name: string;
  coefficient: number;
  group: 'numeric' | 'one_hot' | 'intercept';
}

export interface RocPoint {
  fpr: number;
  tpr: number;
}

export interface PrPoint {
  recall: number;
  precision: number;
}

export interface ThresholdPoint {
  threshold: number;
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  precision: number;
  recall: number;
  f1: number;
  accuracy: number;
  flagged: number;
}

export interface Confusion {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  precision: number;
  recall: number;
  f1: number;
  accuracy: number;
  flagged: number;
}

export interface ModelMetrics {
  auc: number;
  pr_auc: number;
  train_rows: number;
  validation_rows: number;
  train_positives: number;
  validation_positives: number;
  train_positive_rate: number;
  validation_positive_rate: number;
  loss_curve: number[];
  confusion_035: Confusion;
  mean_validation_score: number;
  high_risk_at_035: number;
}

export interface ModelRun {
  id: number;
  run_no: number;
  label: string;
  feature_set_id: number;
  status: 'pending' | 'running' | 'succeeded' | 'failed';
  hyperparams: { learning_rate?: number; l2?: number; epochs?: number };
  coefficients: Coefficient[];
  metrics: ModelMetrics;
  roc_points: RocPoint[];
  pr_points: PrPoint[];
  threshold_scan: ThresholdPoint[];
  standardization: { names: string[]; mean: number[]; std: number[]; bias: number };
  train_rows: number;
  validation_rows: number;
  train_positives: number;
  warning: string;
  error_message: string;
  started_at: string | null;
  finished_at: string | null;
  created_by: string;
  created_at: string | null;
}
