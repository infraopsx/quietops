# QuietOps: real Gemma 3 1B output and audit notes

Source: [GitHub Actions run 39359492617](https://github.com/infraopsx/quietops/actions/runs/39359492617), successful on 20 October 2026.

The runner downloaded real gemma3:1b weights and used Ollama to produce the quietops-real-gemma-report artifact from the synthetic 240-line sample. The full unedited Markdown, HTML and JSON files are available in that workflow artifact. This page quotes actual model output and explains its limitations. The tracked demo/handoff.md is a DIFFERENT deterministic, no-AI preview.

## Actual local model output (verbatim excerpts)

**Overview:**

> Docker container 'demo' is experiencing database connectivity issues. Database URL is being reported as a critical error. The application is attempting to connect to the database via a configured URL. A connection timeout is occurring during database queries. The application is also encountering a connection refused error while attempting to connect to the upstream database.

**Model-proposed hypotheses:**

- The database URL is incorrect or invalid. — E01
- The database server is unavailable or experiencing a network issue. — E02
- The database user has insufficient permissions to connect. — E03

**Model-proposed missing information:**

- Database server is running, but the URL is not configured correctly.

## Audit: real IDs do NOT prove causal correctness

QuietOps verified that E01, E02 and E03 exist in the grouped evidence. It did NOT prove that the generated explanations follow from those events.

- E01 is the redacted database URL error, but that alone does not prove the URL is incorrect.
- E02 contains worker queue retry timeouts. These do not establish that the database server is unavailable.
- E03 contains database query timeouts. These do not establish insufficient database permissions.
- The claimed fact that the database server 'is running' was not established by the fixture; the model placed that statement in its unknowns section.

This is the actual result of a successful inference integration test, not a verified diagnosis.

## Verified technical facts

- Local model: gemma3:1b, served by Ollama on GitHub's ephemeral runner
- Inputs: synthetic logs only, with best-effort redaction before the model call
- Deterministic grouping: 240 lines, 110 symptom lines, 5 signatures
- Inference result: structured JSON parsed and checked for existing evidence IDs
- NOT verified: semantic entailment, root cause, actual human time savings

**Operational rule:** Treat generated suggestions as unverified hypotheses. QuietOps executes no remediation commands. An operator must verify each claim against the original logs and infrastructure.
