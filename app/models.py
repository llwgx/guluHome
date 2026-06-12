from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Index, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class OneNetMessage(Base):
    """OneNet 推送消息存储表"""

    __tablename__ = "onenet_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    push_time: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    nonce: Mapped[str | None] = mapped_column(String(128), nullable=True)
    signature: Mapped[str | None] = mapped_column(String(256), nullable=True)
    msg: Mapped[dict | list | str | None] = mapped_column(JSONB, nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_onenet_messages_push_time", "push_time"),
        Index("ix_onenet_messages_created_at", "created_at"),
    )


class SensorMetric(Base):
    """传感器温湿度业务表（每个数据流一条记录）"""

    __tablename__ = "sensor_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_name: Mapped[str] = mapped_column(String(64), nullable=False)
    sensor_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    metric_type: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("source_message_id", name="uq_sensor_metrics_source_message_id"),
        Index("ix_sensor_metrics_sensor_recorded", "sensor_no", "recorded_at"),
        Index("ix_sensor_metrics_device_sensor_type", "device_name", "sensor_no", "metric_type"),
    )
