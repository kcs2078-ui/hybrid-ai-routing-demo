# Architecture

## Request flow

```mermaid
flowchart LR
  C[Caller] --> R[Explicit request router]
  R -->|classification check| P{Selected provider}
  P -->|local| L[Local model interface]
  P -->|cloud + public only| X[Cloud model interface]
  L --> O[Validated result]
  X --> O
  P -->|invalid, private-to-cloud, unavailable, backend timeout exception, empty result| F[Fail closed]
```

## Contracts

`InferenceRequest` contains a prompt, an explicit provider selection (`local` or `cloud`), and a data classification (`public` or `private`). The router rejects invalid combinations before calling a backend.

The model interface is a protocol with one operation, `infer(prompt) -> str`. Production-specific SDKs and network clients are intentionally absent. The demo backend implementations are deterministic, in-process fakes.

## Failure behavior

The router does not enforce a timeout or deadline. If the selected backend raises a timeout exception, the router treats it like any other backend exception and returns a generic routing failure; it does not retry on another provider. An unavailable backend, other exception, or blank output also fails closed without exposing the prompt or backend exception text. Private data cannot be sent to the cloud interface.

This is an educational example. It does not provide authentication, process isolation, a secrets manager, a production privacy classifier, or a hardened inference service.
