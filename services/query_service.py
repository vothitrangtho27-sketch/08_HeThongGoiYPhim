"""Lưu và thực thi 15 câu truy vấn Cypher (đọc từ queries_15.cypher)."""
import re

import config
from neo4j_connection import run_timed

_cache = None
_HEADER = re.compile(r"^// Câu (\d+)\. (.+)$", re.M)


def load_queries():
    """Trả dict {số câu: {id, title, cypher}}. userId cố định = 1 được thay bằng tham số $userId."""
    global _cache
    if _cache is not None:
        return _cache
    with open(config.QUERY_FILE, encoding="utf-8") as f:
        text = f.read()
    matches = list(_HEADER.finditer(text))
    out = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end]
        body = re.sub(r"^// =+.*$", "", body, flags=re.M)  # bỏ dòng tiêu đề nhóm
        cypher = body.strip().rstrip(";").strip().replace("{userId: 1}", "{userId: $userId}")
        out[int(m.group(1))] = {"id": int(m.group(1)), "title": m.group(2).strip(), "cypher": cypher}
    _cache = out
    return out


def run_query_no(n, user_id=1):
    """Chạy câu số n. Trả (rows, elapsed_ms)."""
    q = load_queries()[n]
    return run_timed(q["cypher"], {"userId": int(user_id)})
