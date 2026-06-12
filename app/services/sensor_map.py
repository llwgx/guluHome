"""OneNet 数据流 -> 传感器编号与指标类型映射"""

DS_MAP: dict[str, tuple[int, str]] = {
    "tmp1": (1, "temperature"),
    "humdi1": (1, "humidity"),
    "tmp2": (2, "temperature"),
    "humdi2": (2, "humidity"),
}

SENSOR_LABELS = {1: "顶部", 2: "底部"}
