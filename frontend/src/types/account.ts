import type { Paged } from './api';
import type { ScoreBatch } from './score';

export interface Reason {
  feature: string;
  label: string;
  raw_value: number | string;
  z_value: number;
  contribution: number;
}

export interface RiskRow {
  account_code: string;
  company_name: string;
  industry: string;
  plan: string;
  region: string;
  csm_owner_email: string;
  csm_owner_name: string;
  seats: number;
  monthly_fee: number;
  score: number;
  actual_churn: number;
  band: 'high' | 'medium' | 'low';
  band_label: string;
  lift: number;
  expected_save: number;
  selected: boolean;
  rank?: number;
  reasons: Reason[];
}

export interface AccountPage extends Paged<RiskRow> {
  batch: ScoreBatch | null;
  bands: Record<string, string>;
  scope_owner: string | null;
}

export interface AccountDetail {
  account: {
    code: string;
    company_name: string;
    industry: string;
    plan: string;
    region: string;
    seats: number;
    monthly_fee: number;
    csm_owner_email: string;
    csm_owner_name: string;
    contract_end: string;
    status: string;
    churn_date: string | null;
  };
  months: { month: string; features: Record<string, number | string>; churn_next_30d: number }[];
  score: RiskRow | null;
  batch: ScoreBatch | null;
}
