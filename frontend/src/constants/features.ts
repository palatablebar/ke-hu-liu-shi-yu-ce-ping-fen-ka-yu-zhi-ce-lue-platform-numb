export const FEATURE_LABELS: Record<string, string> = {
  usage_days: '近30天活跃天数',
  active_user_ratio: '活跃席位占比',
  api_calls_k: 'API 调用量',
  storage_gb: '存储用量',
  tickets_open: '未结工单数',
  tickets_p1: 'P1 工单数',
  nps: 'NPS 分数',
  invoice_overdue_days: '账单逾期天数',
  seat_utilization: '席位使用率',
  executive_sponsor: '有高层赞助人',
  integration_count: '集成系统数',
  training_sessions: '培训场次',
};

export const FEATURE_ORDER = Object.keys(FEATURE_LABELS);
