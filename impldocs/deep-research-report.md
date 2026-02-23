# Core Architecture & Philosophy  
Nexus Sync treats ingestion as a **pure function**: given the same conversation JSON, it must always produce the identical set of Bricks with no hidden state or randomness【9†L133-L140】.  This means **determinism** is paramount (no paraphrasing, no side-effects).  In practice, Sync enforces an *append-only* model – once a Brick (or run) is recorded, it is never modified or deleted.  Any update is a new insertion.  This mirrors “ledger” tables: only INSERTs are allowed, with no UPDATE/DELETE, ensuring immutable history【7†L50-L58】.  

- The system assumes **byte-for-byte content fidelity**.  For example, if the source says “it’s”, the output must contain exactly “it’s”, not “it is”.  Any normalization (e.g. stripping whitespace) is explicitly defined (e.g. fingerprint uses `content.strip()`).  All string comparisons or hashes must operate on the exact token sequence.  
- **Namespace isolation:** Each Topic defines an independent namespace.  Bricks from one Topic cannot override or shadow Bricks from another.  This scoping ensures that extraction and deduplication operate only within the same Topic boundary.  
- **Lifecycle over mutation:** Bricks carry a lifecycle state (`IMPROVISE`, `FORMING`, `FINAL`) to track trust, but changing state does not alter the Brick’s content.  State transitions are metadata-only; the content remains identical.  In short, the *substance* of a Brick is immutable, while its *status* can evolve.  

These principles ensure that **“Server sync is a PURE function of JSON → Bricks.”**  Re-running the sync on identical input (even with a different LLM or host) will yield the same set of Bricks, in the same states, with the same IDs and content【9†L133-L140】【7†L50-L58】.  

## Phase 1: Topic Discovery & Definition (Bootstrap)  
1. **Topic Scanning:** The system examines new conversation JSON (or recent runs) and suggests Topics based on keywords or patterns.  This is a deterministic scan: given the same JSON and rules, the same Topics are found.  
2. **Extraction Policy:** For each Topic, an extraction policy is defined (e.g. scope, keywords, exclusions).  This policy is stored as static configuration.  During compilation, the policy acts as a *filter function*: it deterministically decides which messages belong to the Topic.  
3. **Namespace Creation:** Once a Topic is finalized, it is locked into the `sync.topics` table.  All future sync runs use these Topic definitions.  Because Topics are fixed, the mapping from JSON to Bricks never changes arbitrarily.  

*Key Points:* Topics partition the data.  No content from outside the Topic’s scope can slip in, and the same Topic rules apply each run.  All Topic-related decisions are pure functions of (Policy, Message Content).  

## Phase 2: Source Run Registration (The “Tape”)  
1. **JSON Intake:** The raw conversation JSON (e.g. chat messages) is loaded.  Each load is tagged with a `run_id`.  If this `run_id` is new, it’s inserted.  If it already exists, strict validation is applied.  
2. **Append-Only Validation:** If a run with the same `run_id` already exists, the system compares the *new* JSON to the *old* JSON **by message IDs**.  It requires that the new run is a **strict superset** of the old: every message ID in the old run must appear in the new run.  If any original message is missing or altered, the sync **aborts** (this would imply the “tape” was rewritten, violating immutability).  In pseudocode:
   ```python
   old_ids = {msg.id for msg in old_run.messages}
   new_ids = {msg.id for msg in new_run.messages}
   if not old_ids ⊆ new_ids:
       abort_sync("History Divergence detected")
   ```
   This guard enforces an append-only “transaction log”: old data cannot be removed.  (This is analogous to database ledger tables that only allow INSERT and disallow UPDATE/DELETE【7†L50-L58】.)  
3. **Last-Processed Index:** The system tracks the highest-indexed message that was already processed.  On each sync run, it processes only the *new* messages (those with index > last_processed).  This ensures incremental sync and prevents re-processing.  It is purely index-based and deterministic: given the same run and index, the same set of new messages is chosen.  

*Key Points:* The **Tape** model guarantees immutability.  Every run is validated against history so that only new data is added.  If the source JSON had replayed or changed history, the system would detect it and refuse.  This prevents hidden nondeterminism from upstream edits.  

## Phase 3: Materialization (Compiler Loop)  
1. **Selection Gate:** For each message in the run (in JSON order), the compiler checks the Topic policies.  If a message matches an active Topic, it is sent to that Topic’s Brick stream.  This matching is a pure function of message content and policy (no randomness or external state).  
2. **Brick Creation:** Each selected message yields a new Brick (unless deduped later).  The Brick’s identity is computed deterministically:  
   - `brick_id = SHA256(run_id + message_id)`.  Since `run_id` and `message_id` are stable identifiers, the same message always produces the same `brick_id`.  
   - `fingerprint = SHA256(message_content.strip())`.  This represents the unique content hash of the message.  If the content is identical (byte-for-byte, modulo defined normalization), the fingerprint is identical.  
   The use of SHA-256 (a cryptographic hash) means collisions are astronomically unlikely, so we can treat each (run_id,message_id) tuple and each content string as having a unique hash【11†L13-L20】.  
3. **Authority Tags:** Bricks also carry an **authority label** based on message role: e.g. `system` messages are ROOT, `user` messages are PRIMARY, `assistant` are DERIVED.  This tagging is static and determined by the JSON’s role field, so it’s deterministic (e.g. always treat an “assistant” message with the same authority, never probabilistic).  

*Key Points:* The core transformation (JSON → Brick) is 1:1 and order-preserving.  All identifiers and hashes are computed by fixed formulas, ensuring two runs on identical data yield identical Brick IDs, fingerprints, and tags.  No external services (like LLMs) are invoked during this step, so it has no side-effects or nondeterminism.  

## Phase 4: Resolution & Deduplication  
1. **Fingerprint Check:** When a new Brick is to be created, the system checks if its `fingerprint` already exists *in that Topic*.  If an existing Brick has the same fingerprint (i.e. **exact same text content**), the new message is considered an identical duplicate.  In that case, no new Brick is inserted; instead, the existing Brick’s metadata is simply linked to note the additional source address.  
2. **Subsumption (Supersede) Rule:** If the new message’s text **fully contains** an existing Brick’s text (and strictly more), the old Brick is considered “superseded.”  For example, if Brick A’s content is `"Hello world"` and the new message is `"Hello brave new world"`, then the new Brick subsumes A.  In this case:
   - Mark the old Brick as `SUPERSEDED` (it becomes shadowed).
   - Create the new Brick (in `IMPROVISE` state if it’s brand new).
   This containment check must be **precise**: it typically involves checking if one string is a substring of the other. Any text normalization (e.g. trimming whitespace, case sensitivity rules) must be clearly defined, or else subsumption may fail or spuriously trigger.  
3. **Additive Case:** If the message is neither identical nor subsuming an existing Brick, it is considered a new independent statement.  A fresh Brick is created with state `IMPROVISE`.  

*Key Points:* Deduplication is rule-based and deterministic: it depends only on exact string comparison.  However, it is crucial that the string-matching logic be strictly defined.  For example, if the system ignores punctuation or case when comparing, that could introduce nondeterminism (two runs might differ on how punctuation is handled).  In practice, to be deterministic one should either normalize text consistently (e.g. `content.strip()` already shows normalization at edges) or compare hashes directly.  Any heuristic (like “contains 100% plus more”) should be applied in a fixed way so that repeated runs make the same decision.  

## Phase 5: Traceability & Audit (Source Path Mapping)  
1. **Source Address:** Every Brick records exactly *where* it came from in the JSON.  This is stored as a `source_address`, combining:
   - The `run_id`,
   - A JSON path expression (like `$.messages[12].content`),
   - Any selection indices if the message was split.  
   This is essentially a JSON Pointer【13†L10-L17】 that deterministically points to the text node.  Using a standard (e.g. RFC 6901) pointer syntax means that, given the same input JSON, the same pointer string will be generated each time【13†L10-L17】.  
2. **Node Checksum:** Alongside content, a checksum (e.g. `SHA256` of the JSON sub-node) is saved.  This allows the system to later detect if the original JSON has changed.  If the JSON node is modified in the source, the stored checksum will mismatch; the system can flag the Brick as **STALE/UNVERIFIED**.  The key is that even this verification is deterministic: it’s just a comparison of fixed hashes, with no ambiguity.  

*Key Points:* Every piece of provenance (path, checksum) is computed algorithmically and stored.  There are no side-channels – if the JSON shifts (say a message is edited), the checksum catch-and-flag is repeatable and reliable.  This audit layer ensures accountability: you can always trace a Brick back to the exact text snippet in the raw JSON.  

## Integration with “Jarvis” (Cognition Layer)  
Once the data is in the graph as Bricks, a separate **Jarvis** layer operates on it.  This is entirely downstream and does **not** affect the Sync pipeline’s determinism.  For completeness:  
- **L1 Interpreter:** A local module that simply announces graph events (e.g. “3 bricks moved to FORMING”).  This is just a presentation layer with no influence on stored data.  
- **L2 Narrator:** A cloud LLM (e.g. Claude) that analyzes the graph and explains reasoning (conflicts, rationale) for human consumption.  This might influence user decisions but does not mutate the graph (only suggests).  
- **L3 Sage:** A frontier LLM for deep audits and strategy.  Again, it reads the graph but does not write back.  

*Key Points:* The entire Jarvis layer is **read-only** with respect to the Sync output.  It does not feed back into the data compiler.  Thus, any nondeterminism in Jarvis (due to LLM variability) cannot corrupt the underlying bricks or break the “pure function” guarantee of Sync.  

## Determinism & Remediation Checklist  
Overall, Nexus Sync is designed for maximal determinism, but it’s important to verify and guard against hidden nondeterminism.  Below are key items to **audit and remediate**:

- **Stable JSON Parsing:** Ensure the JSON parser preserves order of arrays and keys. In modern Python, insertion order of dicts is stable, but relying on explicit message IDs (not list position) is safer. Always address nodes by explicit indices or keys rather than assume any internal ordering.  
- **Hash/ID Consistency:** Verify `brick_id = sha256(run_id + message_id)` truly concatenates strings in a fixed encoding (e.g. UTF-8) and applies SHA-256. Any variation in how bytes are generated (e.g. different charsets, line endings) will break determinism. Add tests: given the same run data on different machines, the `brick_id` must match.  
- **Whitespace & Normalization:** The fingerprint uses `content.strip()`, which removes leading/trailing whitespace. Ensure this is consistently applied in all sync runs. Any difference in newline normalization (e.g. `\r\n` vs `\n`) must be resolved (e.g. normalize newlines before stripping). Otherwise two runs of “identical” JSON might differ in trailing spaces.  
- **Run Superset Logic:** The superset check must catch any change. It should not rely on sorted order or numeric comparison only. For example, if the JSON message array was re-ordered without altering IDs, the check by ID set would pass but the content did not physically append. If order matters, consider also verifying that the highest index progressed. In short, ensure **both** ID-inclusion and monotonic index increase.  
- **Content Comparison:** The subsumption test (“contains 100% of old + more”) should be implemented deterministically. Be cautious: substring search is case-sensitive and punctuation-sensitive. If the source content could have synonyms or paraphrases, these rules could fail. One remedy is to compare normalized hashes instead of raw substring: for instance, require the old text’s hash to equal the hash of some contiguous substring of the new text, computed the same way as when originally fingerprinted. This avoids any random choices.  
- **ON CONFLICT Handling:** The database should use `INSERT ... ON CONFLICT DO NOTHING` (as described) for Bricks, ensuring that re-running the same run ID/message does not duplicate. Verify that there are appropriate UNIQUE indexes (e.g. on `brick_id` or fingerprint) so that concurrent runs or retries cannot create duplicates. This ensures idempotence.  
- **Immutable State Updates:** Changing a Brick’s state (`IMPROVISE`→`FORMING`→`FINAL`) or marking `SUPERSEDED` should also be done via explicit transaction logs or audit events. The content field should never change except in subsumption (where the old Brick is shadowed). Any state transition should be re-playable and have a clear `bricks` table history or audit trail so we can prove the pipeline’s purity.  
- **End-to-End Testing:** Finally, regularly re-run the entire sync on known datasets (using different code versions, machines, or even after refactoring) and compare the full dump of `brick_id`, `fingerprint`, and content. The outputs should be byte-identical. Automating such a regression check will catch any subtle nondeterminism.  

By following these practices, the Nexus Sync pipeline will behave as intended: a strictly deterministic, append-only compiler that guarantees the knowledge graph is always a consistent, reproducible reflection of the conversation data.

**Sources:** We have applied principles of pure functions and immutable ledgers to this design【9†L133-L140】【7†L50-L58】, and rely on standard JSON Pointer notation for traceability【13†L10-L17】. These ensure the pipeline’s mathematical and operational determinism.