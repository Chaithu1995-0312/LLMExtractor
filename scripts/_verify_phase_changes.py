"""
Syntax verification for Phase 1-3 implementation changes.
Run from repo root: python scripts/_verify_phase_changes.py
"""
import ast
import sys
import os

files = [
    "src/nexus/cognition/confidence_engine.py",
    "src/nexus/memory/memory_service.py",
    "src/nexus/memory/health.py",
    "src/nexus/memory/api_routes.py",
    "src/nexus/cognition/l3_sage.py",
]

errors = []
for f in files:
    full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), f)
    try:
        with open(full_path, "r", encoding="utf-8") as fh:
            source = fh.read()
        ast.parse(source)
        print(f"  OK  {f}")
    except SyntaxError as e:
        errors.append((f, e))
        print(f"  ERR {f}: line {e.lineno}: {e.msg}")
    except FileNotFoundError:
        errors.append((f, "FILE NOT FOUND"))
        print(f"  MISSING  {f}")

print()
if errors:
    print(f"FAILED: {len(errors)} file(s) have errors.")
    sys.exit(1)
else:
    print(f"ALL {len(files)} FILES PASS — no syntax errors detected.")
