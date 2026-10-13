"""Kết nối Python - Redis, hỗ trợ lưu / đọc / xóa cache.
Nếu Redis không chạy, mọi hàm vẫn hoạt động (bỏ qua cache) để ứng dụng không bị lỗi."""
import json

import redis

import config

_client = None
_failed = False


def get_client():
    global _client, _failed
    if _client is not None:
        return _client
    if _failed:
        return None
    try:
        c = redis.Redis(
            host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB,
            password=config.REDIS_PASSWORD, decode_responses=True,
            socket_connect_timeout=1, socket_timeout=1,
        )
        c.ping()
        _client = c
    except Exception:
        _failed = True
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
        return None


def cache_set(key, value, ttl=None):
    c = get_client()
    if c is None:
        return False
    try:
        c.set(key, json.dumps(value, default=str), ex=ttl or config.CACHE_TTL)
        return True
    except Exception:
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
            for k in c.scan_iter(match=pattern):
                c.delete(k)
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
