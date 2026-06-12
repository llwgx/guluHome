from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import SensorMetric
from app.services.sensor_map import SENSOR_LABELS

router = APIRouter(prefix="/api", tags=["Dashboard"])


async def _latest_metric(
    db: AsyncSession,
    sensor_no: int,
    metric_type: str,
) -> SensorMetric | None:
    return await db.scalar(
        select(SensorMetric)
        .where(
            SensorMetric.sensor_no == sensor_no,
            SensorMetric.metric_type == metric_type,
        )
        .order_by(SensorMetric.recorded_at.desc())
        .limit(1)
    )


@router.get("/latest")
async def get_latest(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """各传感器最新温湿度。"""
    sensors = []
    for sensor_no in (1, 2):
        temp = await _latest_metric(db, sensor_no, "temperature")
        hum = await _latest_metric(db, sensor_no, "humidity")
        times = [
            t
            for t in [temp.recorded_at if temp else None, hum.recorded_at if hum else None]
            if t is not None
        ]
        sensors.append(
            {
                "sensor_no": sensor_no,
                "label": SENSOR_LABELS[sensor_no],
                "device_name": temp.device_name if temp else (hum.device_name if hum else None),
                "temperature": temp.value if temp else None,
                "humidity": hum.value if hum else None,
                "recorded_at": max(times).isoformat() if times else None,
            }
        )
    return {"sensors": sensors}


@router.get("/chart")
async def get_chart(
    sensor: int = Query(1, ge=1, le=2),
    hours: int | None = Query(None, ge=1, le=168),
    today: bool = Query(False, description="仅返回当天数据（北京时间）"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """指定传感器的历史温湿度，供图表使用。"""
    if today:
        tz = ZoneInfo("Asia/Shanghai")
        now = datetime.now(tz)
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = "today"
    else:
        since = datetime.now(timezone.utc) - timedelta(hours=hours or 24)
        period_label = f"{hours}h"

    rows = await db.scalars(
        select(SensorMetric)
        .where(
            and_(
                SensorMetric.sensor_no == sensor,
                SensorMetric.recorded_at >= since,
            )
        )
        .order_by(SensorMetric.recorded_at.asc())
    )
    metrics = rows.all()

    timestamps: dict[str, dict[str, float | None]] = {}
    for row in metrics:
        key = row.recorded_at.isoformat()
        if key not in timestamps:
            timestamps[key] = {"temperature": None, "humidity": None}
        timestamps[key][row.metric_type] = row.value

    labels = sorted(timestamps.keys())
    return {
        "sensor_no": sensor,
        "label": SENSOR_LABELS[sensor],
        "period": period_label,
        "labels": labels,
        "temperature": [timestamps[k]["temperature"] for k in labels],
        "humidity": [timestamps[k]["humidity"] for k in labels],
    }
