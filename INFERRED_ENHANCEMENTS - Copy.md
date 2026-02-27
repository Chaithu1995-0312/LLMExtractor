# INFERRED_ENHANCEMENTS.md

## 1. Automated Schema Drift Detection
**Status**: 🧪 Concept
**Logic**: Implement a task that compares the current `Intent` descriptions against new `Brick` batches using clustering. If a significant new cluster appears that doesn't map to an existing Intent, an `EVOLUTION_CANDIDATE` pulse is emitted.

## 2. Multi-Model Consensus Synthesis
**Status**: 🔴 Missing
**Logic**: Instead of a single L3 call, trigger 3 concurrent calls to different providers (e.g., GPT-4o, Claude 3.5, Llama 3). Use the `ConfidenceEngine` to select the most stable synthesis or mark for human review if they diverge significantly.

## 3. Predictive Task Scaling
**Status**: 🔴 Missing
**Logic**: The `BudgetController` currently tracks historical usage. It could be enhanced to predict upcoming load based on `SyncDatabase` run frequency and dynamically scale `PGWorker` instances via Kubernetes or AWS Lambda.

## 4. Graph Versioning & "Time Travel"
**Status**: 🧪 Concept
**Logic**: Leverage the `SUPERSEDES` and `Pulse` history to allow the UI to render the "Wall" at any point in history. This is vital for auditing why a certain decision was made by an agent 3 months ago.

## 5. Self-Correction via Negative Constraints
**Status**: 🟡 Partial
**Logic**: In addition to standard prompts, maintain a list of "Negative Examples" (e.g., "Do not merge Intent A and B because..."). Feed these into the `L2Narrator` to prevent recurring cognitive errors.
