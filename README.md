# QuietOps 🦥

**Turn noisy Docker / Linux logs into a short, evidence-linked handoff using local open-weight AI.**

> Created from scratch on 20 October 2026 for the Hacktoberfest Open-Source AI Challenge — Week 3, *Slow and Steady*.

### Why this exists

An operator often spends the start of a shift scrolling through nearly identical error lines: upstream failures, database authentication problems, timeouts, and retries. QuietOps handles the tedious first pass. It clusters recurring symptoms, strips common secrets, and asks a **local Gemma 3 model** to prepare a cautious, evidence-linked briefing. The operator still makes every decision.

**The demo is reproducible.** `examples/docker-incident.log` contains 240 synthetic lines. Deterministic parsing identifies 110 symptom lines across 5 distinct signatures. Reading one line per grouped signature instead of the raw stream is a **97.9% reduction in initial items**, not a claim of human time saved.

### Features

- **Offline first:** runs on your computer; no API keys, cloud backends, accounts, analytics or external scripts.
- **Open-weight AI is central:** Ollama + local `gemma3:1b` generates a plain-language incident overview, hypotheses and recommended read-only checks.
- **Evidence-bound:** model-suggested hypotheses and checks are rejected unless they refer to real event IDs from the supplied logs.
- **Safe by default:** does not run commands against servers, modify configuration, connect to Docker or execute any model-proposed action.
- **Privacy-minded:** common passwords, access tokens, key strings, credentials in URLs, IPs and emails are redacted *before* calling the model. Redaction is best-effort: review your own logs before use.
- **Three shareable reports:** Markdown, JSON and a self-contained HTML dashboard (no external CSS or JS).
- **Tiny dependency footprint:** Python standard library only; no Python package dependencies.

## Demo without a model

```bash
python3 examples/make_demo.py
python3 -m quietops preview examples/docker-incident.log --output-dir out/
# Open out/handoff.html in a browser
```

The preview is intentionally labeled **"Model not run"**. It is not an AI-generated diagnosis.

## Run with local Gemma

Install [Ollama](https://ollama.com/download) **0.6+** and pull the small [Gemma 3 1B](https://ollama.com/library/gemma3) model (about 806 MB):

```bash
ollama pull gemma3:1b
ollama serve                   # Only if the Ollama service is not already running
python3 -m quietops scan examples/docker-incident.log \
    --model gemma3:1b --output-dir out/ --replace
```

The default model endpoint is `http://127.0.0.1:11434`. QuietOps **rejects non-loopback endpoints**, so input logs cannot be sent by the program to a remote model host. It also disables HTTP proxy use for the model request. Gemma is an **open-weight model under Google's Gemma Terms**, not MIT-licensed; model weights are **not included** in this repository.

For logs from your own machine:

```bash
# No write operations: collect a narrow window of logs yourself first.
docker compose logs --no-color --tail=1000 > incident.log
python3 -m quietops scan incident.log --output-dir out/
```

Logs can contain secrets or identifiable information. **Inspect and sanitize them before using the tool.** These patterns cannot guarantee complete secret removal.

### Command summary

```text
python3 -m quietops {scan|preview} INPUT [--output-dir DIR] [--max-lines N]
  scan       Analyzes group signatures with local Gemma through Ollama
  preview    Deterministic grouping with NO AI (for demo and privacy review)
  INPUT      UTF-8 file or - for stdin; maximum input 2 MB
  --replace  Explicitly overwrite an existing report
```

The default scan examines a maximum of 8,000 lines and forwards only the top 12 grouped signatures (up to 2 redacted excerpts each) to the local model. Lower-ranked events are counted but not sent. This is a first-pass briefing, **not complete forensic analysis**.

## What it does *not* do

- It does **not** log into a server, restart containers, execute model output or automatically fix anything.
- It does **not** verify a root cause, guarantee that logs are fully redacted or assert that a change is safe for production.
- It does **not** replace monitoring, operational runbooks, security review or incident response processes.
- It does **not** claim a measured productivity gain without a user study.

## Automated real-model demo (after publishing)

The new repository also includes `.github/workflows/live-gemma.yml`. On the first push to `main`, GitHub Actions starts Ollama in a Docker container, downloads the actual `gemma3:1b` weights, calls QuietOps in `scan` mode, checks that every suggested evidence ID exists, and uploads the HTML/JSON/Markdown outputs as the `quietops-real-gemma-report` artifact. This is a **planned CI verification**, not proof that the model has run until the workflow succeeds. The model download requires access to the official Ollama registry.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The integration test starts a **simulated Ollama HTTP server** bound to `127.0.0.1` and verifies that the model receives redacted structured event data. It tests the request/response integration, **not actual Gemma inference quality**. A separate live run with downloaded Gemma weights is required to test that.

## Docker (optional)

```bash
docker build -t quietops:local .
# preview does not need an Ollama service
mkdir -p out
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" quietops:local \
  preview /work/examples/docker-incident.log --output-dir /work/out
# For local Ollama on Linux, replace 'preview' with 'scan' and add --network host.
```

## Architecture

```text
Synthetic or user-provided UTF-8 log
          |
          v
        2 MB cap + 8k line cap
          |
          v
 Best-effort redaction + severity filtering
          |
          v
  Repeated signature grouping and bounded excerpts
          |
          v
  Ollama HTTP 127.0.0.1 --> Gemma 3 1B
          |
          v
 Evidence-ID validation + cautious report
          |
          v
   HTML / Markdown / JSON (local files)
```

## Contest

Built for [DEV Hacktoberfest 2026 Week 3](https://dev.to/challenges/hacktoberfest-week3-2026-10-19). The category **Best Use of Gemma** applies when demonstrated with an actual Gemma model; the deterministic sample is not a model demonstration. A DEV submission is a separate step and should only describe real tests.

### License

MIT for this tool's original code. Gemma model weights and Ollama have their own licenses.
