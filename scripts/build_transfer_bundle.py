import glob
import json
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def discover_entry_points() -> list[str]:
    pat = re.compile(r"if\s+__name__\s*==\s*['\"]__main__['\"]\s*:")
    out: list[str] = []
    for p in ROOT.rglob("*.py"):
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if pat.search(txt):
            out.append(p.relative_to(ROOT).as_posix())
    return sorted(set(out))


def extract_tables(sql_text: str) -> list[str]:
    pat = re.compile(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([a-zA-Z0-9_\.]+)|CREATE\s+TABLE\s+([a-zA-Z0-9_\.]+)",
        re.IGNORECASE,
    )
    tables: list[str] = []
    for m in pat.findall(sql_text):
        t = (m[0] or m[1] or "").strip()
        if t:
            tables.append(t)
    return sorted(set(tables))


def main() -> None:
    entry_points = discover_entry_points()

    explicit_components = [
        "src/nexus/index/conversation_index.py",
        "src/nexus/evolution/ai_advisory.py",
        "src/nexus/cognition/l2_3_linker.py",
        "services/cortex/compaction_worker.py",
        "src/nexus/sync/ingest_history.py",
        "ui/app.js",
        "ui/jarvis/index.html",
        "src/nexus/evolution/intent_governor.py",
        "src/nexus/graph/validation.py",
        "src/nexus/db/init_db.py",
        "src/nexus/scripts/migrate_to_intents.py",
        "src/nexus/scripts/apply_intent_schema.py",
        "src/nexus/graph/schema_postgres.sql",
        "scripts/migrations/001_vector_unification.sql",
        "scripts/migrations/002_decision_cache.sql",
        "scripts/migrations/003_goal_engine.sql",
        "scripts/migrations/20240625_status_columns.py",
        "scripts/migrations/20240628_audit_tables.py",
        "scripts/migrations/20240629_audit_triggers.sql",
        "docs/CANONICAL_DB_MIGRATION_RUNBOOK.md",
    ]
    for v in sorted(glob.glob(str(ROOT / "validation" / "checks" / "*_validator.py"))):
        explicit_components.append(Path(v).relative_to(ROOT).as_posix())

    explicit_components = [p for p in explicit_components if (ROOT / p).exists()]

    sql_sources = [
        "src/nexus/graph/schema_postgres.sql",
        "src/nexus/scripts/apply_intent_schema.py",
        "scripts/migrations/001_vector_unification.sql",
        "scripts/migrations/002_decision_cache.sql",
        "scripts/migrations/003_goal_engine.sql",
        "scripts/migrations/20240628_audit_tables.py",
        "scripts/migrations/20240629_audit_triggers.sql",
    ]

    source_map: dict[str, list[str]] = {}
    all_tables: set[str] = set()
    for src in sql_sources:
        p = ROOT / src
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        tables = extract_tables(txt)
        if tables:
            source_map[src] = tables
            all_tables.update(tables)

    report_lines: list[str] = []
    report_lines.append("# DB Entry Points and Table Inventory Report")
    report_lines.append("")
    report_lines.append("## Scope")
    report_lines.append("- Includes all discovered Python `__main__` entry points in repository.")
    report_lines.append("- Includes explicitly mentioned architectural component files from user snippets.")
    report_lines.append("- Maps database initialization/migration entry points and extracted table definitions.")
    report_lines.append("")
    report_lines.append("## Discovered Entry Points (Python __main__)")
    report_lines.append(f"- Total discovered: **{len(entry_points)}**")
    for ep in entry_points:
        report_lines.append(f"  - `{ep}`")
    report_lines.append("")
    report_lines.append("## Database Entry Points")
    report_lines.append("- `src/nexus/db/init_db.py` → initializes PostgreSQL baseline schema via `src/nexus/graph/schema_postgres.sql`.")
    report_lines.append("- `src/nexus/scripts/apply_intent_schema.py` → creates `graph.intent_metrics`, JSONB index.")
    report_lines.append("- `src/nexus/scripts/migrate_to_intents.py` → data migration from topics to intents and edge updates.")
    report_lines.append("- `scripts/migrations/001_vector_unification.sql` → alters `graph.vector_meta` columns/indexes.")
    report_lines.append("- `scripts/migrations/002_decision_cache.sql` → creates `graph.decision_cache`.")
    report_lines.append("- `scripts/migrations/003_goal_engine.sql` → creates `graph.goals`.")
    report_lines.append("- `scripts/migrations/20240625_status_columns.py` → legacy status/timestamp column additions.")
    report_lines.append("- `scripts/migrations/20240628_audit_tables.py` → creates `audit.processing_trail`, `audit.alerts`.")
    report_lines.append("- `scripts/migrations/20240629_audit_triggers.sql` → creates `audit.alert_anomaly()` trigger function + trigger.")
    report_lines.append("")
    report_lines.append("## Extracted Table Definitions (from SQL/Python DDL)")
    for t in sorted(all_tables):
        report_lines.append(f"- `{t}`")
    report_lines.append("")
    report_lines.append("## Table Definition Sources")
    for src, tables in source_map.items():
        report_lines.append(f"- `{src}`")
        for t in tables:
            report_lines.append(f"  - `{t}`")
    report_lines.append("")
    report_lines.append("## Additional DB Objects (non-table)")
    report_lines.append("- Function: `audit.alert_anomaly()` from `scripts/migrations/20240629_audit_triggers.sql`")
    report_lines.append("- Trigger: `anomaly_detection` on `audit.processing_trail`")
    report_lines.append("- View: `governance.active_alerts` from `src/nexus/graph/schema_postgres.sql`")
    report_lines.append("")
    report_lines.append("## Packaging Verification Inputs")
    report_lines.append(f"- Entry points included: **{len(entry_points)}**")
    report_lines.append(f"- Explicit component files included: **{len(explicit_components)}**")

    report_path = ROOT / "DB_ENTRYPOINTS_AND_TABLES_REPORT.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    files = set(entry_points)
    files.update(explicit_components)
    files.add(report_path.relative_to(ROOT).as_posix())
    manifest = sorted(f for f in files if (ROOT / f).exists())

    manifest_path = ROOT / "TRANSFER_FILE_MANIFEST.txt"
    manifest_path.write_text("\n".join(manifest) + "\n", encoding="utf-8")

    zip_name = ROOT / "nexus_transfer_bundle.zip"
    with zipfile.ZipFile(zip_name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in manifest:
            zf.write(ROOT / f, arcname=f)

    with zipfile.ZipFile(zip_name, "r") as zf:
        zip_files = sorted(zf.namelist())

    missing = [f for f in manifest if f not in zip_files]
    extra = [f for f in zip_files if f not in manifest]
    summary = {
        "entry_points": len(entry_points),
        "explicit_components": len(explicit_components),
        "manifest_files": len(manifest),
        "zip_files": len(zip_files),
        "missing_in_zip": len(missing),
        "extra_in_zip": len(extra),
    }
    verification = {
        "summary": summary,
        "missing": missing,
        "extra": extra,
    }
    (ROOT / "ZIP_VERIFICATION.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
