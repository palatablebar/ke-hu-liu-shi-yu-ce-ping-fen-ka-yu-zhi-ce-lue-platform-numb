"""Role enum — shared with frontend/src/constants/roles.ts."""
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"      # 客户成功负责人：特征/参数/阈值发布
    ANALYST = "analyst"  # 数据分析师：训练/评估/调参
    CSM = "csm"          # 客户成功经理：只读自己客户名单与原因


ROLE_LABELS: dict[str, str] = {
    Role.ADMIN: "客户成功负责人",
    Role.ANALYST: "数据分析师",
    Role.CSM: "客户成功经理",
}

ALL_ROLES = tuple(role.value for role in Role)
