# PROMPTS.md - my key prompts log

Keep the handful of prompts that actually moved the build. Not every message - the ones that mattered: the system/sub-agent prompts, the ones you iterated on, the "this finally worked" moment.

---

## 1. Initial Project Audit
- **Prompt:** "First perform a complete project audit. Read and analyze rulebook.md, report.schema.json, README.md, run.py, linkintel/analyzer.py... Then create a completion report mapping every finding back to the challenge specification."
- **For:** Understanding the baseline deterministic codebase and establishing exactly what requirements were already fulfilled by the starter code vs what was missing.
- **Revised?** N/A. Led to a detailed gap analysis.

## 2. Strategic Pivot: Deterministic vs Model
- **Prompt:** "Before implementing anything, re-evaluate each missing requirement... Do not assume that model-based solutions are required if a deterministic solution satisfies the rulebook. Can it be solved deterministically? Will it produce reproducible results?"
- **For:** Deciding how to maximize challenge score while minimizing risk.
- **Revised?** Yes. We initially considered building everything with an LLM, but revised to prioritize deterministic fallback solutions for stability.

## 3. Compliance Layer Architecture
- **Prompt:** "Act as a Principal Engineer performing a challenge compliance upgrade. Do not replace the deterministic engine... Design a compliance layer. Keep all deterministic logic... Only add AI refinement steps (Topic Agent, Entity Refinement)."
- **For:** Designing the batched LLM layer in `run.py` that processes entities and clusters without destroying the underlying graph code.
- **Revised?** N/A.

## 4. Headless Execution Safety Check
- **Prompt:** "Determine whether the proposed AI refinement layer works under a fully headless execution path. Answer: Can run.py execute the refinement layer automatically? Will model_calls be non-zero during headless execution? Design the smallest possible implementation that keeps deterministic outputs but performs actual model inference."
- **For:** Validating that our AI usage satisfies the active-agent challenge requirements without destroying the robust offline grader safety.
- **Revised?** Yes. Initially we considered calling the LLM per-page. Revised to batch execution to reduce LLM calls to exactly 3-4 per run, ensuring massive speedup and minimizing failure points.

## 5. Data Quality and Metric Integrity
- **Prompt:** "Perform a final data-quality audit of report.json. Focus on broken_internal_links, redirect_internal_links, nofollow_internal_links. Verify every item is actually an INTERNAL link. Check whether any external URLs are being incorrectly classified as internal."
- **For:** Catching edge-case scoring anomalies where external metrics polluted the internal graph analysis arrays.
- **Revised?** N/A, led directly to identifying the critical `site_domain` filtering bug in `analyzer.py`.

## 6. Anchor Quality Audit
- **Prompt:** "Audit link_recommendations. Focus only on suggested_anchor quality. Identify anchors that are: image names, alt text, marketing slogans... propose the smallest fix."
- **For:** Polishing the contextual link suggestions to be strictly descriptive and highly relevant.
- **Revised?** Yes, the audit revealed `H1` tags were often marketing slogans or images, prompting a surgical fix to prioritize `Title` tags and filter out generic strings like "logo".

## 7. Memory Hardening & Concurrency Engine
- **Prompt:** "Our batched execution is forcing qwen3:8b to load a 65,000-token context window, causing massive RAM paging and 15-20 minute execution times. Check all the md files to see if this is the correct approach and find things on the internet to review what could be the right way to make it faster without violating rules."
- **For:** Solving the severe offline hardware crashes while strictly adhering to the "One page per call" rule from the rulebook.
- **Revised?** Yes. We correctly de-batched the LLM calls to single-page processing to drop the context window to ~500 tokens, permanently fixing the memory crashes. We then imported `concurrent.futures.ThreadPoolExecutor` to parallelize the requests, achieving perfect schema compliance and exponentially faster execution (dropping to 4.4 minutes on average local hardware and ~30 seconds on parallel hardware).
