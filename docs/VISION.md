# VISION

## Problem
FreeLLMAPI aggregates dozens of free LLM providers behind one OpenAI-compatible
endpoint, but using it from the terminal still requires exporting environment
variables, remembering the base URL, and knowing which model ids exist. There
is no dedicated plugin for the `llm` CLI, so every user rebuilds the same setup.

## Solution
`llm-freellmapi` is a plugin for [LLM](https://llm.datasette.io/) that registers
a single `freellmapi` model pointing at a FreeLLMAPI server. Configuration is
one interactive command; usage is the same as any other `llm` model.

```bash
llm install llm-freellmapi
llm freellmapi configure
llm -m freellmapi "Hello"
```

## Value Proposition
- One install and one configure step — no environment variables to remember
- `auto` model routing: FreeLLMAPI picks an available free model and fails over
  when a provider is rate-limited
- Works from any directory; no adapter server, Docker container or extra runtime
- Streaming, `llm chat`, piped input and `llm logs` behave like any other model
- Dedicated commands to inspect the live model catalog and server status
- Works with a local server (`localhost:3001`) or a remote instance

## Target Audience
- Developers and power users who already use the `llm` CLI
- FreeLLMAPI users who want a first-class terminal interface
- People who want access to many free models without managing each provider key

## Non-Goals
- Running or packaging the FreeLLMAPI server itself
- Local model inference
- Managing provider keys or quotas (the FreeLLMAPI dashboard does that)
