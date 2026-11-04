# Technical decisions

## ADR-001: Explicit provider selection

**Decision:** the caller selects local or cloud for each request. The router does not infer a provider from ambient environment configuration.

**Reason:** make the data path visible and testable.

**Trade-off:** callers must make an explicit choice; this demo does not optimize cost or latency.

## ADR-002: Private requests stay local

**Decision:** requests classified `private` are rejected if cloud is selected.

**Reason:** fail before a backend can receive the prompt.

**Trade-off:** the classification is supplied by the caller and is not a production-grade information classifier.

## ADR-003: No implicit provider fallback

**Decision:** if the selected backend is unavailable, the router reports failure and calls no alternative provider.

**Reason:** automatic local-to-cloud fallback could change the data boundary during an outage.

**Trade-off:** availability is lower during backend failures. A future system would require an explicit, separately reviewed fallback policy.
