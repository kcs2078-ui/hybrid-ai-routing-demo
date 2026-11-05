# Technical decisions

## ADR-001: Explicit provider selection

**Decision:** the caller selects local or cloud for each request. The router does not infer a provider from ambient environment configuration.

**Reason:** make the data path visible and testable.

**Trade-off:** callers must make an explicit choice; this demo does not optimize cost or latency.

## ADR-002: Private requests stay local

**Decision:** requests classified `private` are rejected if cloud is selected.

**Reason:** fail before a backend can receive the prompt.

**Trade-off:** the classification is supplied by the caller and is not a production-grade information classifier.

## ADR-003: Fallback is explicit and request-scoped

**Decision:** the default is no fallback. A request may explicitly choose `local_to_cloud` only for public data with Local as the primary provider.

**Reason:** automatic local-to-cloud fallback could change the data boundary during an outage. Private requests are rejected before either backend is called when fallback is requested.

**Trade-off:** availability is lower under the default policy. The opt-in demonstration is not an automatic classifier or production approval mechanism.

## ADR-004: Local SQLite memory example

**Decision:** use standard-library SQLite with in-memory storage by default, parameterized bounded search, and explicit scopes for same-session reads versus cross-session search.

**Reason:** make persistence and retrieval behavior runnable without adding a service or third-party dependency.

**Trade-off:** the example does not encrypt records, provide retention automation, or serve as a production memory store.

## ADR-005: Safe request audit records

**Decision:** generate request IDs in the application and log only route, outcome, and static failure categories.

**Reason:** make the selected path and failure result inspectable without copying user prompts, credentials, session IDs, backend exception text, or model output into logs.

**Trade-off:** logs intentionally do not contain enough detail to reproduce user content or backend internals.
