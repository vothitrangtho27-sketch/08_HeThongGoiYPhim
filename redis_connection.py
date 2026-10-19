"""Kết nối Python - Redis, hỗ trợ lưu / đọc / xóa cache.
Nếu Redis không chạy, mọi hàm vẫn hoạt động (bỏ qua cache) để ứng dụng không bị lỗi."""
import json
import time

import redis

import config

RETRY_AFTER = 30      # giây: sau khi kết nối lỗi, đợi chừng này rồi mới thử lại (không phải khởi động lại ứng dụng)
CHECK_EVERY = 1       # giây: kiểm tra lại (PING) kết nối đang dùng, để biết khi Redis bị tắt giữa chừng

_client = None
_failed_at = None     # thời điểm kết nối lỗi gần nhất
_checked_at = 0.0     # thời điểm PING thành công gần nhất


def _mark_failed():
    global _client, _failed_at
    _client = None
    _failed_at = time.time()


def get_client():
    """Trả kết nối Redis, hoặc None nếu Redis không chạy."""
    global _client, _failed_at, _checked_at
    now = time.time()
    if _client is not None:
        if now - _checked_at < CHECK_EVERY:
            return _client
        try:
            _client.ping()                 # kết nối cũ còn dùng được không?
            _checked_at = now
            return _client
        except Exception:
            _mark_failed()                 # Redis đã tắt: quay về dùng Neo4j
            return None
    if _failed_at is not None and now - _failed_at < RETRY_AFTER:
        return None
    try:
        c = redis.Redis(
            host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB,
            password=config.REDIS_PASSWORD, decode_responses=True,
            socket_connect_timeout=1, socket_timeout=1,
        )
        c.ping()
        _client, _failed_at, _checked_at = c, None, now
    except Exception:
        _failed_at = now
    return _client


def is_available():
    return get_client() is not None


def cache_get(key):
    c = get_client()
    if c is None:
        return None
    try:
        v = c.get(key)
        return json.loads(v) if v is not None else None
    except Exception:
        _mark_failed()
        return None


def cache_set(key, value, ttl=None):
    c = get_client()
    if c is None:
        return False
    try:
        c.set(key, json.dumps(value, default=str), ex=ttl or config.CACHE_TTL)
        return True
    except Exception:
        _mark_failed()
        return False


def cache_delete(key):
    c = get_client()
    if c is not None:
        try:
            c.delete(key)
        except Exception:
            pass


def cache_delete_pattern(pattern):
    c = get_client()
    if c is not None:
        try:
            keys = list(c.scan_iter(match=pattern))
            if keys:
                c.delete(*keys)          # xóa một lần thay vì từng khóa
        except Exception:
            pass


def get_or_set(key, fn, ttl=None):
    """Trả (giá trị, from_cache). Nếu chưa có cache thì gọi fn() rồi lưu lại."""
    v = cache_get(key)
    if v is not None:
        return v, True
    v = fn()
    cache_set(key, v, ttl)
    return v, False
