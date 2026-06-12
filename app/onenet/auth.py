import base64
import hashlib
from urllib.parse import unquote


def compute_signature(token: str, nonce: str, msg: str) -> str:
    """
    OneNet 签名校验算法：
    1. 拼接 token + nonce + msg
    2. MD5 加密
    3. Base64 编码
    4. URL Decode（兼容 signature 参数中的特殊字符）
    """
    raw = f"{token}{nonce}{msg}"
    digest = hashlib.md5(raw.encode("utf-8")).digest()
    b64 = base64.b64encode(digest).decode("utf-8")
    return unquote(b64)


def verify_signature(token: str, nonce: str, msg: str, signature: str) -> bool:
    expected = compute_signature(token, nonce, msg)
    return expected == signature
