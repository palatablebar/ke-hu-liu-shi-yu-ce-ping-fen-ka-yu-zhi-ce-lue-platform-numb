"""Feature catalogue for the churn model (shared with frontend/src/constants/features.ts)."""

NUMERIC_FEATURES: list[dict] = [
    {"key": "usage_days", "label": "近30天活跃天数", "unit": "天", "direction": "lower_worse",
     "description": "登录且有实际调用的天数，连续下滑是最早的流失信号"},
    {"key": "active_user_ratio", "label": "活跃席位占比", "unit": "比例", "direction": "lower_worse",
     "description": "月活跃账号数 / 已购席位数"},
    {"key": "api_calls_k", "label": "API 调用量", "unit": "千次", "direction": "lower_worse",
     "description": "业务系统调用量，反映产品是否嵌进客户流程"},
    {"key": "storage_gb", "label": "存储用量", "unit": "GB", "direction": "lower_worse",
     "description": "数据沉淀规模"},
    {"key": "tickets_open", "label": "未结工单数", "unit": "个", "direction": "higher_worse",
     "description": "月末仍未关闭的工单"},
    {"key": "tickets_p1", "label": "P1 工单数", "unit": "个", "direction": "higher_worse",
     "description": "当月最高优先级事故工单"},
    {"key": "nps", "label": "NPS 分数", "unit": "分", "direction": "lower_worse",
     "description": "季度问卷净推荐值，-100 ~ 100"},
    {"key": "invoice_overdue_days", "label": "账单逾期天数", "unit": "天", "direction": "higher_worse",
     "description": "最大一笔账单的逾期天数，付款意愿先行指标"},
    {"key": "seat_utilization", "label": "席位使用率", "unit": "比例", "direction": "lower_worse",
     "description": "已激活席位 / 合同席位"},
    {"key": "executive_sponsor", "label": "有高层赞助人", "unit": "0/1", "direction": "lower_worse",
     "description": "是否登记了客户方高层对接人"},
    {"key": "integration_count", "label": "集成系统数", "unit": "个", "direction": "lower_worse",
     "description": "与客户内部系统打通的集成数量"},
    {"key": "training_sessions", "label": "培训场次", "unit": "场", "direction": "lower_worse",
     "description": "近 90 天为客户提供的培训场次"},
]

CATEGORICAL_FEATURES: list[dict] = [
    {"key": "industry", "label": "所属行业", "values": ["电商", "金融", "制造", "教育", "医疗"]},
    {"key": "plan", "label": "合同版本", "values": ["标准版", "专业版", "旗舰版"]},
    {"key": "region", "label": "区域", "values": ["华北", "华东", "华南", "西南"]},
]

TARGET_COLUMN = "churn_next_30d"
TARGET_LABEL = "未来 30 天是否流失"

NUMERIC_KEYS = tuple(feature["key"] for feature in NUMERIC_FEATURES)
CATEGORICAL_KEYS = tuple(feature["key"] for feature in CATEGORICAL_FEATURES)
FEATURE_LABELS: dict[str, str] = {feature["key"]: feature["label"] for feature in NUMERIC_FEATURES}
FEATURE_LABELS.update({feature["key"]: feature["label"] for feature in CATEGORICAL_FEATURES})
