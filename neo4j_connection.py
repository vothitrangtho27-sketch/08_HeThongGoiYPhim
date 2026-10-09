"""Kết nối Python - Neo4j, thực thi Cypher và trả kết quả."""
import time

from neo4j import GraphDatabase

import config

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )
    return _driver


def run_query(cypher, params=None):
    """Chạy một câu Cypher, trả về list[dict]."""
    with get_driver().session(database=config.NEO4J_DATABASE) as session:
        return [r.data() for r in session.run(cypher, params or {})]


def run_timed(cypher, params=None):
    """Chạy Cypher và đo thời gian. Trả về (rows, elapsed_ms)."""
    t0 = time.perf_counter()
    rows = run_query(cypher, params)
    return rows, (time.perf_counter() - t0) * 1000


def ping():
    try:
        get_driver().verify_connectivity()
        return True
    except Exception:
        return False


def close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
