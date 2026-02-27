# APPENDIX.md

## Class → Method Map

### `GraphManager` (src/nexus/graph/manager.py)
| Method Name | Responsibility | Risk Profile | Inputs/Outputs | Idempotency | State Impact | Validation/Invariants |
|-------------|----------------|--------------|----------------|-------------|--------------|-----------------------|
| `register_node` | Creates or updates a node in the graph. | HIGH | `(node_type, node_id, attrs)` -> `None` | ✅ Yes | `nodes` table | Type must be in schema. |
| `register_edge` | Creates a relationship between nodes. | HIGH | `(src, dst, type, attrs)` -> `None` | ✅ Yes | `edges` table | Cycle detection if type is hierarchical. |
| `promote_node_to_frozen` | Sets node lifecycle to FROZEN. | MED | `(node_id, actor)` -> `None` | ✅ Yes | `lifecycle` field | Node must exist. |
| `supersede_node` | Replaces an old node with a new one and relinks edges. | HIGH | `(old_id, new_id, reason)` -> `None` | ❌ No | `nodes`, `edges` | Transactional; old node must exist. |
| `_emit_pulse` | Internal helper to log audit events. | MED | `(event_type, node_id, payload)` -> `None` | ✅ Yes | `audit_logs` | Payload must be JSON serializable. |

### `SyncDatabase` (src/nexus/sync/db.py)
| Method Name | Responsibility | Risk Profile | Inputs/Outputs | Idempotency | State Impact | Validation/Invariants |
|-------------|----------------|--------------|----------------|-------------|--------------|-----------------------|
| `save_brick_atomic` | Atomic write of a materialized brick. | HIGH | `(brick_dict)` -> `None` | ✅ Yes | `bricks` table | Brick ID must be unique. |
| `register_run_safe` | Records a new ingestion run. | MED | `(run_id, content)` -> `None` | ✅ Yes | `runs` table | Run ID must not exist or match content. |
| `supersede_brick` | Marks a brick as superseded by another. | MED | `(old_id, new_id)` -> `None` | ✅ Yes | `superseded_by` field | Both bricks must exist. |

### `CortexAPI` (services/cortex/api.py)
| Method Name | Responsibility | Risk Profile | Inputs/Outputs | Idempotency | State Impact | Validation/Invariants |
|-------------|----------------|--------------|----------------|-------------|--------------|-----------------------|
| `generate` | Orchestrates LLM response generation. | MED | `(query, brick_ids)` -> `Dict` | ✅ Yes | Audit logs | Input tokens must be within limit. |
| `route` | Maps a query to a specific agent/topic. | MED | `(query)` -> `Dict` | ✅ Yes | None | None. |
| `acknowledge_alert` | Marks a topic alert as acknowledged. | MED | `(alert_id, actor)` -> `Dict` | ✅ Yes | `alerts` table | Alert must exist. |

## Method Usage Graph
| Method | Layer | Type | Called By |
|--------|-------|------|-----------|
| `GraphManager.register_node` | Graph | Write-authoritative | `CortexAPI`, `NexusCompiler` |
| `CortexAPI.generate` | Service | Read-only / Stateful (Audit) | UI (GlobalSearch) |
| `TopicRouter.route_run` | Ingestion | Pure (Logic) | `SyncRunner` |
| `ConfidenceEngine.compute_l2_confidence` | Cognition | Pure | `L2Narrator`, `EscalationRouter` |

## Cross-Class Interaction Boundaries
- **Lifecycle Gatekeeper**: `GraphManager.promote_node_to_frozen` ensures nodes are only frozen after manual audit.
- **Write Boundary**: `GraphManager` is the ONLY class allowed to modify the graph database.
- **Safety Rail**: `validation.run_full_validation` is a mandatory check before any bulk promotion.
