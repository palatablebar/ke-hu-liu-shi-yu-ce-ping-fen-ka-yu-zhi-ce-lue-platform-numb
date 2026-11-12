import type { Role } from '@/types/api';

export const ROLE_LABELS: Record<Role, string> = {
  admin: '客户成功负责人',
  analyst: '数据分析师',
  csm: '客户成功经理',
};

export const ROLE_SCOPE: Record<Role, string> = {
  admin: '特征 / 参数 / 阈值发布',
  analyst: '训练 / 评估 / 调参',
  csm: '只读自己客户名单与原因',
};
