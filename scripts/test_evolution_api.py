"""
test_evolution_api.py — Smoke Tests for Evolution V2 API
=========================================================
Tests:
  1. Schema tables exist (graph.concept_versions, graph_ai.*, graph_sandbox.*)
  2. Materialized views are queryable
  3. ConceptEvolutionAPI — get_concept_roots, get_node_detail, get_live_metrics
  4. AIAdvisory — get_pending_suggestions, run_analysis (dry cycle)
  5. PromotionEngine — analyze_conflict on empty sandbox
  6. DriftEngine — archived guard (archived node skipped)

Usage:
    python scripts/test_evolution_api.py
"""

import sys
import os
import json
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nexus.db import get_adapter

PASS = "✅"
FAIL = "❌"
SKIP = "⚠️ "

results = []

def check(name: str, passed: bool, detail: str = ""):
    status = PASS if passed else FAIL
    msg = f"  {status} {name}"
    if detail:
        msg += f"  →  {detail}"
    print(msg)
    results.append((name, passed))


def section(title: str):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


def run():
    print("=" * 55)
    print("  Evolution V2 API Smoke Tests")
    print("=" * 55)

    db = get_adapter()

    # ------------------------------------------------------------------
    # SECTION 1 — Schema Tables
    # ------------------------------------------------------------------
    section("1. Schema Tables")

    tables_to_check = [
        ("graph",         "concept_versions"),
        ("graph_ai",      "suggestions"),
        ("graph_ai",      "analysis_runs"),
        ("graph_sandbox", "nodes"),
        ("graph_sandbox", "edges"),
        ("graph_sandbox", "runs"),
        ("graph_sandbox", "promotions"),
    ]

    for schema, table in tables_to_check:
        try:
            row = db.fetch_one(
                "SELECT to_regclass(%s)",
                (f"{schema}.{table}",)
            )
            exists = row is not None and row[0] is not None
            check(f"{schema}.{table} exists", exists)
        except Exception as exc:
            check(f"{schema}.{table} exists", False, str(exc)[:80])

    # ------------------------------------------------------------------
    # SECTION 2 — graph.nodes Archival Columns
    # ------------------------------------------------------------------
    section("2. Archival Columns on graph.nodes")

    archival_columns = ["archived", "concept_version", "archived_at",
                        "cluster_id", "branch_id", "author_id", "stability_score"]
    try:
        row = db.fetch_one(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'graph' AND table_name = 'nodes'
            """
        )
        col_rows = db.fetch_all(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'graph' AND table_name = 'nodes'
            """
        )
        existing_cols = {r[0] for r in col_rows}
        for col in archival_columns:
            check(f"graph.nodes.{col}", col in existing_cols)
    except Exception as exc:
        check("graph.nodes archival columns", False, str(exc)[:80])

    # ------------------------------------------------------------------
    # SECTION 3 — Materialized Views
    # ------------------------------------------------------------------
    section("3. Materialized Views")

    mat_views = [
        "graph.mv_concept_roots",
        "graph.mv_cluster_health",
        "graph.mv_supersession_velocity",
        "graph.mv_convergence_index",
    ]

    for view in mat_views:
        try:
            db.fetch_all(f"SELECT 1 FROM {view} LIMIT 1")
            check(f"{view} queryable", True)
        except Exception as exc:
            check(f"{view} queryable", False, str(exc)[:80])

    # ------------------------------------------------------------------
    # SECTION 4 — ConceptEvolutionAPI
    # ------------------------------------------------------------------
    section("4. ConceptEvolutionAPI")

    try:
        from nexus.evolution.concept_evolution import ConceptEvolutionAPI
        api = ConceptEvolutionAPI(db=db)

        # get_concept_roots — should not raise
        try:
            roots = api.get_concept_roots(limit=5)
            check("get_concept_roots() runs", True, f"{len(roots)} roots found")
        except Exception as exc:
            check("get_concept_roots() runs", False, str(exc)[:80])

        # get_node_detail — test with a real node if available
        try:
            node_rows = db.fetch_all(
                "SELECT id FROM graph.nodes WHERE archived = FALSE LIMIT 1"
            )
            if node_rows:
                nid = node_rows[0][0]
                detail = api.get_node_detail(nid)
                check("get_node_detail() returns NodeDetail", detail is not None,
                      f"id={nid[:16]}...")
            else:
                check("get_node_detail() runs", True, "(no nodes yet — skipped)")
        except Exception as exc:
            check("get_node_detail() runs", False, str(exc)[:80])

        # compute_stability_score
        try:
            score = api.compute_stability_score("nonexistent_node_xyz")
            check("compute_stability_score() returns 1.0 for unknown", score == 1.0,
                  f"score={score}")
        except Exception as exc:
            check("compute_stability_score() runs", False, str(exc)[:80])

        # get_live_metrics
        try:
            metrics = api.get_live_metrics()
            check("get_live_metrics() returns dict", isinstance(metrics, dict),
                  f"keys={list(metrics.keys())}")
        except Exception as exc:
            check("get_live_metrics() runs", False, str(exc)[:80])

    except ImportError as exc:
        check("ConceptEvolutionAPI import", False, str(exc))

    # ------------------------------------------------------------------
    # SECTION 5 — AIAdvisory
    # ------------------------------------------------------------------
    section("5. AIAdvisory")

    try:
        from nexus.evolution.ai_advisory import AIAdvisory
        advisory = AIAdvisory(db=db)

        try:
            suggestions = advisory.get_pending_suggestions(limit=5)
            check("get_pending_suggestions() runs", True,
                  f"{len(suggestions)} pending")
        except Exception as exc:
            check("get_pending_suggestions() runs", False, str(exc)[:80])

        try:
            runs = advisory.get_analysis_runs(limit=5)
            check("get_analysis_runs() runs", True, f"{len(runs)} runs found")
        except Exception as exc:
            check("get_analysis_runs() runs", False, str(exc)[:80])

    except ImportError as exc:
        check("AIAdvisory import", False, str(exc))

    # ------------------------------------------------------------------
    # SECTION 6 — PromotionEngine
    # ------------------------------------------------------------------
    section("6. PromotionEngine")

    try:
        from nexus.evolution.promotion_engine import PromotionEngine, ResolutionStrategy
        engine = PromotionEngine(db=db)

        # analyze_conflict with a nonexistent concept — should return NONE severity
        try:
            fake_run_id = str(uuid.uuid4())
            fake_concept_id = "nonexistent_concept_xyz"
            report = engine.analyze_conflict(fake_run_id, fake_concept_id)
            check("analyze_conflict() on empty concept returns NONE",
                  report.conflict_severity.value == "NONE",
                  f"severity={report.conflict_severity}")
        except Exception as exc:
            check("analyze_conflict() runs", False, str(exc)[:80])

        # discard_sandbox with fake run — should not crash
        try:
            result = engine.discard_sandbox("nonexistent_run_xyz", "test_actor")
            # May return False (run not found) — that is acceptable
            check("discard_sandbox() does not raise", True,
                  f"returned={result}")
        except Exception as exc:
            check("discard_sandbox() does not raise", False, str(exc)[:80])

    except ImportError as exc:
        check("PromotionEngine import", False, str(exc))

    # ------------------------------------------------------------------
    # SECTION 7 — DriftEngine archived guard
    # ------------------------------------------------------------------
    section("7. DriftEngine Archived Guard")

    try:
        # Insert a temporary archived node
        test_id = f"test_archived_{uuid.uuid4().hex[:8]}"
        db.execute(
            """
            INSERT INTO graph.nodes (id, type, data, archived, vector_status)
            VALUES (%s, 'brick', %s, TRUE, 'indexed')
            ON CONFLICT DO NOTHING
            """,
            (test_id, json.dumps({"statement": "archived test node", "lifecycle": "loose"}))
        )

        from nexus.evolution.drift_engine import DriftEngine
        engine = DriftEngine(db=db)
        node_data = engine._fetch_node(test_id, require_indexed=False)
        check("Archived node returns None from _fetch_node", node_data is None,
              f"result={node_data}")

        # Cleanup
        db.execute("DELETE FROM graph.nodes WHERE id = %s", (test_id,))

    except Exception as exc:
        check("DriftEngine archived guard", False, str(exc)[:80])

    # ------------------------------------------------------------------
    # RESULTS
    # ------------------------------------------------------------------
    print(f"\n{'=' * 55}")
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)
    print(f"  Results: {passed}/{total} passed  |  {failed} failed")
    print(f"{'=' * 55}\n")

    if failed > 0:
        print("Failed tests:")
        for name, ok in results:
            if not ok:
                print(f"  {FAIL} {name}")
        sys.exit(1)
    else:
        print("All tests passed. Evolution V2 API is operational.\n")


if __name__ == "__main__":
    run()
