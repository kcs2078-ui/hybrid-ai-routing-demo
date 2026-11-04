# Failure scenario: selected backend unavailable

**Scenario:** a request explicitly selects the local backend, which becomes unavailable.

**Expected behavior:** return a generic unavailable error; do not send the prompt to the cloud mock; do not include prompt text in the error.

**Evidence in this MVP:** the unit test uses a synthetic prompt and a call-counting fake backend to prove that the alternative backend receives zero calls. This is an automated demo test, not an incident report or proof about an operational service.
