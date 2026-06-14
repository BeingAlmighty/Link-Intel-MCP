# PROMPTS.md - my key prompts log

- **Prompt:** "Determine whether the proposed AI refinement layer works under a fully headless execution path. Answer: Can run.py execute the refinement layer automatically? Will model_calls be non-zero during headless execution? Design the smallest possible implementation that keeps deterministic outputs but performs actual model inference."
- **For:** Validating that our AI usage satisfies the active-agent challenge requirements without destroying the robust offline grader safety.
- **Revised?** Yes. Initially we considered calling the LLM per-page. Revised to batch execution to reduce LLM calls to exactly 3-4 per run, ensuring massive speedup and minimizing failure points.

- **Prompt:** "Perform a final data-quality audit of report.json. Focus on broken_internal_links, redirect_internal_links, nofollow_internal_links. Verify every item is actually an INTERNAL link. Check whether any external URLs are being incorrectly classified as internal."
- **For:** Catching edge-case scoring anomalies where external metrics polluted the internal graph analysis arrays.
- **Revised?** N/A, led directly to identifying the critical site_domain filtering bug in nalyzer.py.
