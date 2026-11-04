# Hybrid AI Portfolio MVP

A small, clean-room demonstration of request routing between local and cloud model interfaces. It uses only Python's standard library, deterministic mock backends, and synthetic input. It makes no network calls and contains no production configuration.

## What it demonstrates

- A caller explicitly selects `local` or `cloud` for each request.
- Private-classified requests are accepted only by the local backend.
- Backend failure, empty output, invalid selection, and policy rejection fail closed. The router never silently switches providers.
- Automated tests use fake backends and synthetic prompts only.

This repository is a portfolio demo, not a deployable assistant or production security boundary. The mock cloud backend does not contact a provider.

## Requirements

Python 3.11 or newer. There are no third-party runtime or test dependencies.

## Run the local example

```sh
python3 -m venv .venv
. .venv/bin/activate
PYTHONPATH=src python -m hybrid_ai_portfolio --provider local
PYTHONPATH=src python -m hybrid_ai_portfolio --provider cloud
```

The demo uses a fixed synthetic prompt; arbitrary prompt text is not accepted by its command line. Cloud selection is permitted only for a request marked public. To see fail-closed behavior, run:

```sh
PYTHONPATH=src python -m hybrid_ai_portfolio --provider cloud --classification private
```

That command exits with an error before a backend is called. All backends in this demo are in-process mocks.

## Run local CI

```sh
./scripts/ci.sh
```

CI runs unit tests, bytecode compilation, and the public-safety pattern scan. It does not access the network, model services, Telegram, cloud resources, private documents, or local databases.

## Repository map

- `src/hybrid_ai_portfolio/routing.py`: provider-selection contract and fail-closed router.
- `src/hybrid_ai_portfolio/demo.py`: local-only mock example.
- `tests/`: synthetic unit tests.
- `docs/`: architecture, ownership boundary, decisions, and a sanitized failure scenario.

## Ownership and data boundary

This MVP was authored separately from the operational repositories. It contains no copied production implementation, credentials, private source records, employer documents, operational IPs, or deployment files. See [OWNERSHIP.md](OWNERSHIP.md). The project intentionally has no license file: public redistribution requires an owner-approved license and confirmation that the portfolio material is publishable.
