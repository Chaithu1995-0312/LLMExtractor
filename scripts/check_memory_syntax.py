"""Quick AST syntax check for all Memory Layer files."""
import ast
import sys

files = [
    "src/nexus/memory/__init__.py",
    "src/nexus/memory/_db.py",
    "src/nexus/memory/chunker.py",
    "src/nexus/memory/embedder.py",
    "src/nexus/memory/vector_store.py",
    "src/nexus/memory/metadata_store.py",
    "src/nexus/memory/dataset_manager.py",
    "src/nexus/memory/retriever.py",
    "src/nexus/memory/memory_service.py",
    "src/nexus/memory/api_routes.py",
    "tests/unit/test_memory_layer.py",
]

errors = []
for f in files:
    try:
        with open(f, encoding="utf-8") as fh:
            src = fh.read()
        ast.parse(src, filename=f)
        print(f"  OK  {f}")
    except SyntaxError as e:
        print(f"  ERR {f}: line {e.lineno}: {e.msg}")
        errors.append(f)
    except FileNotFoundError:
        print(f"  MISSING {f}")
        errors.append(f)

print()
if errors:
    print(f"FAILED: {len(errors)} file(s) have errors.")
    sys.exit(1)
else:
    print(f"All {len(files)} files passed syntax check.")
