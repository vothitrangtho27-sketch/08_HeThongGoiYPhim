"""Đo thời gian thực thi 15 câu truy vấn Neo4j và hiệu quả cache Redis.
Chạy: python benchmark_neo4j.py [userId] [số lần lặp]"""
import csv
import statistics
import sys
import time

import neo4j_connection as nc
import redis_connection as rc
from services.query_service import load_queries, run_query_no
from services.recommendation_service import recommend


def main():
    uid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    queries = load_queries()
    results = []
    print(f"Benchmark {len(queries)} truy vấn | userId={uid} | {runs} lần/câu\n")
    print(f"{'Câu':<5}{'Số dòng':>9}{'TB (ms)':>11}{'Min':>10}{'Max':>10}  Tên")
    for n in sorted(queries):
        run_query_no(n, uid)  # chạy khởi động (warm-up), không tính
        times, rows = [], 0
        for _ in range(runs):
            r, ms = run_query_no(n, uid)
            times.append(ms)
            rows = len(r)
        results.append((n, queries[n]["title"], rows, statistics.mean(times), min(times), max(times)))
        print(f"{n:<5}{rows:>9}{statistics.mean(times):>11.1f}{min(times):>10.1f}{max(times):>10.1f}  {queries[n]['title']}")

    with open("benchmark_result.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["cau", "ten", "so_dong", "tb_ms", "min_ms", "max_ms"])
        w.writerows([(a, b, c, round(d, 2), round(e, 2), round(g, 2)) for a, b, c, d, e, g in results])
    print("\nĐã lưu benchmark_result.csv")

    print("\n--- So sánh gợi ý phim: Neo4j trực tiếp vs Redis cache ---")
    if not rc.is_available():
        print("Redis không chạy, bỏ qua phần so sánh cache.")
    else:
        rc.cache_delete_pattern(f"rec:{uid}:*")
        for method in ("similar", "friends", "genre", "hybrid"):
            t0 = time.perf_counter(); recommend(uid, method); miss = (time.perf_counter() - t0) * 1000
            t0 = time.perf_counter(); recommend(uid, method); hit = (time.perf_counter() - t0) * 1000
            print(f"{method:<9} Neo4j: {miss:8.1f} ms | Redis cache: {hit:6.2f} ms | nhanh gấp {miss / max(hit, 0.01):.0f} lần")
    nc.close_driver()


if __name__ == "__main__":
    main()
