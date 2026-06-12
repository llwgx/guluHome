import hashlib
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import OneNetMessage
from app.onenet.auth import verify_signature
from app.services.sensor import save_sensor_metric

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onenet", tags=["OneNet"])


def _extract_msg_for_verify(payload: dict[str, Any]) -> str:
    """从 POST body 中提取用于签名校验的 msg 字符串。"""
    msg = payload.get("msg")
    if msg is None:
        return ""
    if isinstance(msg, str):
        return msg
    return json.dumps(msg, ensure_ascii=False, separators=(",", ":"))


def _derive_message_id(payload: dict[str, Any]) -> str | None:
    """提取或生成消息唯一 ID，用于去重。"""
    if message_id := payload.get("id"):
        return str(message_id)

    msg_sig = payload.get("msg_signature") or payload.get("signature")
    nonce = payload.get("nonce")
    if msg_sig and nonce:
        return f"{nonce}:{msg_sig}"

    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _parse_msg_content(payload: dict[str, Any]) -> dict | list | str | None:
    msg = payload.get("msg")
    if msg is None:
        return None
    if isinstance(msg, str):
        try:
            return json.loads(msg)
        except json.JSONDecodeError:
            return msg
    return msg


@router.get("/push")
async def verify_url(
    msg: str = Query(..., description="OneNet 验证消息"),
    nonce: str = Query(..., description="随机字符串"),
    signature: str = Query(..., description="签名"),
) -> Response:
    """
    OneNet URL 验证接口（GET）。
    平台配置推送地址时会发送 GET 请求，验证通过后需原样返回 msg。
    """
    if not settings.onenet_skip_verify:
        if not verify_signature(settings.onenet_token, nonce, msg, signature):
            logger.warning("OneNet URL 验证失败: signature 不匹配")
            raise HTTPException(status_code=403, detail="invalid signature")

    return Response(content=msg, media_type="text/plain")


@router.post("/push")
async def receive_push(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    OneNet 数据推送接收接口（POST）。
    需在 5 秒内返回 HTTP 200，否则平台会重试推送。
    """
    try:
        payload: dict[str, Any] = await request.json()
    except Exception as exc:
        logger.error("无法解析 OneNet 推送 JSON: %s", exc)
        raise HTTPException(status_code=400, detail="invalid json body") from exc

    nonce = payload.get("nonce", "")
    signature = payload.get("signature") or payload.get("msg_signature", "")
    msg_str = _extract_msg_for_verify(payload)

    if not settings.onenet_skip_verify and signature:
        if not verify_signature(settings.onenet_token, nonce, msg_str, signature):
            logger.warning("OneNet 推送签名校验失败")
            raise HTTPException(status_code=403, detail="invalid signature")

    message_id = _derive_message_id(payload)
    if message_id:
        existing = await db.scalar(
            select(OneNetMessage.id).where(OneNetMessage.message_id == message_id)
        )
        if existing:
            logger.info("重复消息已忽略: message_id=%s", message_id)
            return {"status": "ok", "detail": "duplicate ignored"}

    record = OneNetMessage(
        message_id=message_id,
        push_time=payload.get("time") or payload.get("at"),
        nonce=nonce or None,
        signature=signature or None,
        msg=_parse_msg_content(payload),
        raw_payload=payload,
    )

    try:
        db.add(record)
        await db.flush()
        if isinstance(record.msg, dict):
            await save_sensor_metric(db, record.msg, message_id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.info("并发重复消息已忽略: message_id=%s", message_id)
        return {"status": "ok", "detail": "duplicate ignored"}

    logger.info("已保存 OneNet 推送消息: message_id=%s", message_id)
    return {"status": "ok"}


@router.get("/messages")
async def list_messages(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询已保存的推送消息（便于调试）。"""
    result = await db.scalars(
        select(OneNetMessage)
        .order_by(OneNetMessage.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()
    return {
        "total_returned": len(rows),
        "items": [
            {
                "id": row.id,
                "message_id": row.message_id,
                "push_time": row.push_time,
                "msg": row.msg,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }
