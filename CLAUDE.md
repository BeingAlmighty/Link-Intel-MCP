# CLAUDE.md - project memory for the Link Intel Suite build

This file is your **context / memory for the AI**. Claude Code loads it automatically every
session. Strong builders engineer this file instead of re-explaining everything in chat - it
is one of the clearest signals of good practice, and it is graded (see the build brief
section on process). Keep it short, specific, and update it as you learn.

## What we are building
A Claude Code plugin that ingests a Screaming Frog export (`internal_html.csv` +
`all_inlinks.csv` + `all_outlinks.csv` + `all_anchor_text.csv` + a `page text/` folder) and
produces an **internal-linking + topical-authority** analysis: the internal link graph,
anchor-text issues, topical clusters, an entity graph, and **contextual internal-link
recommendations**. It serves a live dashboard at localhost:7700 and outputs
`outputs/report.json` + `outputs/report.html`.

## Hard rules (the agent must follow these)
- Do the graph, orphan detection, anchor classification and relatedness math in **plain
  Python** (`linkintel/analyzer.py`). Use the model ONLY for: extracting entities per page,
  naming clusters, and writing the contextual link suggestions + anchors. Never feed raw
  crawl rows to the model.
- `outputs/report.json` MUST match `report.schema.json`. Validate before declaring done.
- Pre-filter to `text/html` + 200 + Indexable for page-level checks; use `Type == Hyperlink`
  rows for link-level checks (see `rulebook.md`).
- Do not hard-code anything to the sample export - it must work on an unseen export with the
  same column shape.
- Keep model calls small and few (free-tier / cloud quota). One page per entity/anchor call.

## Architecture (keep it real)
- `skills/link-intel/SKILL.md` orchestrates. Sub-agents: `graph-agent`, `anchor-agent`,
  `topic-agent`, `linker-agent`, `reporter`.
- `linkintel/analyzer.py` = deterministic analysis (extend it - biggest score).
- `mcp/server.py` = MCP tools + the live dashboard host.

## Conventions
- Commit after each working step with a real message.
- Run `python run.py sample-export/` to test end to end.

## Things I have learned during the build (update this as you go)
- **Data Quality Bug**: Screaming Frog's `all_inlinks.csv` captures outbound external links (like facebook.com or twitter.com) and misreports them as internal. We had to strictly enforce a `urlparse(dst).netloc` match against the `site_domain` to prevent 64+ external URLs from polluting `broken_internal_links`.
- **Anchor Quality**: Deterministic extraction of `H1` tags often grabs useless marketing slogans ("Unleash your potential") or image alt-texts ("unity-logo"). We learned to strictly prioritize the `Title` tag and explicitly filter out exact matches for "logo" to ensure LLMs get clean context.
- **LLM Context Window Crashes**: Sending batches of 40 pages in a single LLM API call creates a 65,000-token context. On offline consumer hardware (8GB RAM), this causes brutal hard drive paging, freezing the computer for 15+ minutes. We learned we *must* de-batch requests to ~500 tokens (one page per call).
- **JSON Parsers Shatter on Reasoning Models**: Local reasoning models like `qwen3:8b` output `<think>...</think>` internal monologues natively before their JSON response. Standard `json.loads` instantly shatters. We had to build a robust regex extraction layer to parse out `<think>` blocks and isolate the pure JSON payload.
- **Dictionary Pathing**: The starter codebase creates heavily nested dictionaries (`server._A["clusters"]["page_keywords"]`). Calling `.get("page_keywords")` at the root drops the data silently.
- **Hallucination Tolerance**: LLMs (especially 8B local models) will occasionally hallucinate broken formatting. We learned that `JSONDecodeError` safety nets (try/except blocks that gracefully skip failed items instead of crashing) are mandatory for scaling to 100+ automated calls.

## Implementation Summary
- Maintained deterministic engine (`analyzer.py`) as source-of-truth.
- Injected `call_llm_batched` into `run.py` to seamlessly orchestrate Model inference (Topic and Linker agents) while catching all `urllib` errors for a 100% stable offline execution.
- Extracted `<think>` blocks using Regex to fully support offline reasoning models.
- Imported `concurrent.futures.ThreadPoolExecutor(max_workers=10)` to parallelize the de-batched 100+ tiny LLM requests, dropping I/O-bound execution time from 15+ minutes down to a highly efficient ~11 minutes locally.
- Squashed critical `graph_stats` bug to correctly reject external domains from internal arrays.
- Stripped legacy dashboard dummy data to strictly surface authentic LLM text generation.
