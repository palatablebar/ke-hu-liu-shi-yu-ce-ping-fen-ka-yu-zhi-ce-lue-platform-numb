// 与后端 src/constants/score_lifecycle.py 保持一致的策略生命周期三态。
import type { ScoreBatch } from '@/types/score';

export const SCORE_LIFECYCLE = {
  DRAFT: 'draft',
  ACTIVE: 'active',
  ARCHIVED: 'archived',
} as const;

export type ScoreLifecycle = (typeof SCORE_LIFECYCLE)[keyof typeof SCORE_LIFECYCLE];

export const SCORE_LIFECYCLE_LABELS: Record<string, string> = {
  draft: '草稿',
  active: '现行策略',
  archived: '历史版本',
};

// StatusSeal 的印鉴色调，与页面航海勘测风格对齐。
export const SCORE_LIFECYCLE_TONES: Record<string, string> = {
  draft: 'seal--neutral',
  active: 'seal--low',
  archived: 'seal--medium',
};

export interface PolicyParamChange {
  field: string;
  current: number | null;
  candidate: number;
  changed: boolean;
}

export interface RosterDeltaRow {
  account_code: string;
  company_name: string;
  score: number;
  rank?: number;
  expected_save: number;
}

export interface ScoreMoveRow {
  account_code: string;
  company_name: string;
  current_score: number;
  candidate_score: number;
  delta: number;
}

export interface PolicyDiffSummary {
  current_high_risk: number;
  candidate_high_risk: number;
  high_risk_added: number;
  high_risk_removed: number;
  current_selected: number;
  candidate_selected: number;
  selected_added: number;
  selected_removed: number;
  score_moves: number;
}

export interface PolicyDiff {
  candidate: ScoreBatch;
  current: ScoreBatch | null;
  param_changes: PolicyParamChange[];
  summary: PolicyDiffSummary;
  selected_added: RosterDeltaRow[];
  selected_removed: RosterDeltaRow[];
  score_moves: ScoreMoveRow[];
}

export interface PolicySwitchResult {
  switched: boolean;
  reason: 'switched' | 'already_active' | string;
  active: ScoreBatch;
  previous: ScoreBatch | null;
  active_count: number;
}
