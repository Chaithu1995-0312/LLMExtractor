# Appendix — Nexus

## Artifact Trace Schema
{
  "trace_id": "uuid",
  "topic": "string",
  "inputs": ["brick_ids"],
  "outputs": ["artifact_id"],
  "coverage_status": "FULL | PARTIAL | NONE",
  "tests_run": []
}

## Required Tests
- Duplicate upload does not re-index
- New upload appends only
- Topic with zero recall still creates artifact
- Mixed old + new data ingestion
