# Self-Verification Checklist

- [x] **Did I accidentally generate text?**
  - No, the UI simply fetches and displays existing brick IDs and confidence scores.

- [x] **Did I call Cortex.generate?**
  - No, the only endpoint called is `GET /jarvis/ask-preview`.

- [x] **Did I mutate state/server?**
  - No, the backend code was left untouched (despite the missing metadata issue). The UI is read-only.

- [x] **Is UI read-only?**
  - Yes, there are no forms to submit data (other than the search query), no "save" buttons, and no PUT/POST/DELETE requests.

- [x] **Is behavior deterministic?**
  - Yes, given the same query and backend state, the UI displays the same results.

## Invariants Check
- [x] UI MUST be read-only
- [x] UI MUST NOT call Cortex.generate
- [x] UI MUST NOT write memory, audit, or promotion
- [x] UI MUST ONLY call: GET /jarvis/ask-preview
- [x] UI MUST NOT summarize or infer content (No mock data used)
- [x] UI MUST be refresh-safe and idempotent
