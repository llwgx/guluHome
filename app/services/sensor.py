import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OneNetMessage, SensorMetric
from app.services.sensor_map import DS_MAP

logger = logging.getLogger(__name__)


def parse_sensor_metric(msg: dict[str, Any]) -> SensorMetric | None:
    """从 OneNet 推送 msg 解析单条传感器指标。"""
    if msg.get("type") != 1:
        return None

    ds_id = msg.get("ds_id")
    if not ds_id or ds_id not in DS_MAP:
        return None

    value = msg.get("value")
    if value is None:
        return None

    sensor_no, metric_type = DS_MAP[ds_id]
    recorded_at_ms = msg.get("at")
    if recorded_at_ms is None:
        return None

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None

    return SensorMetric(
        device_name=str(msg.get("dev_name") or "unknown"),
        sensor_no=sensor_no,
        metric_type=metric_type,
        value=numeric_value,
        recorded_at=datetime.fromtimestamp(recorded_at_ms / 1000, tz=timezone.utc),
        source_message_id=None,
    )


async def save_sensor_metric(
    db: AsyncSession,
    msg: dict[str, Any],
    message_id: str | None,
) -> bool:
    """解析并写入 sensor_metrics，返回是否成功插入。"""
    metric = parse_sensor_metric(msg)
    if metric is None:
        return False

    metric.source_message_id = message_id
    stmt = (
        insert(SensorMetric)
        .values(
            device_name=metric.device_name,
            sensor_no=metric.sensor_no,
            metric_type=metric.metric_type,
            value=metric.value,
            recorded_at=metric.recorded_at,
            source_message_id=metric.source_message_id,
        )
        .on_conflict_do_nothing(index_elements=["source_message_id"])
    )
    result = await db.execute(stmt)
    inserted = result.rowcount > 0
    if inserted:
        logger.info(
            "传感器数据已入库: device=%s sensor=%s %s=%s",
            metric.device_name,
            metric.sensor_no,
            metric.metric_type,
            metric.value,
        )
    return inserted


async def backfill_from_messages(db: AsyncSession) -> int:
    """从已有 onenet_messages 回填 sensor_metrics。"""
    existing = await db.scalar(select(SensorMetric.id).limit(1))
    if existing is not None:
        return 0

    rows = await db.scalars(select(OneNetMessage).order_by(OneNetMessage.id))
    count = 0
    for row in rows:
        if not isinstance(row.msg, dict):
            continue
        if await save_sensor_metric(db, row.msg, row.message_id):
            count += 1
    await db.commit()
    if count:
        logger.info("历史数据回填完成: %d 条", count)
    return count
