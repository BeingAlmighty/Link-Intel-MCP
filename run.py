#!/usr/bin/env python3
"""
run.py - headless runner for the Link Intel Suite (also the grader's entry point).

Runs the full internal-linking analysis on a Screaming Frog export with no Claude Code:
  load -> graph -> anchors -> topics -> entities (TF proxy) -> recommend (candidates)
       -> write report.json + report.html

Usage:
  python run.py sample-export/
  python run.py sample-export/ --no-dashboard

The model-driven steps (cluster naming, entity extraction, writing the contextual link
anchors) are left as build TODOs; the starter writes deterministic placeholders so the
report.json contract stays valid and the pipeline always produces a graded artifact.
"""
from __future__ import annotations
import argparse, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "mcp"))
sys.path.insert(0, HERE)
import server  # the MCP server module exposes every tool as a function


import urllib.request
import json

def call_llm_batched(prompt: str, agent_file: str) -> dict | None:
    try:
        with open(os.path.join(HERE, "agents", agent_file), "r", encoding="utf-8") as f:
            sys_prompt = f.read()
    except Exception:
        sys_prompt = "You are an internal linking agent."
        
    req_body = {
        "model": server.MODEL,
        "system": sys_prompt,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps(req_body).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30.0) as response:
            res = json.loads(response.read().decode("utf-8"))
            return json.loads(res.get("response", "{}"))
    except Exception as e:
        print(f"[li] LLM timeout or error ({type(e).__name__}). Using offline deterministic fallback data.", flush=True)
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export_dir")
    ap.add_argument("--no-dashboard", action="store_true")
    args = ap.parse_args()

    if not args.no_dashboard:
        server.start_dashboard()
        print(f"[li] dashboard: http://localhost:{server.PORT}", flush=True)
        time.sleep(1)

    t0 = time.time()
    server.li_load(args.export_dir)
    server.li_graph()
    server.li_anchors()
    server.li_topics()
    
    server.RUN["model_calls"] = 0
    server.RUN_INTERNAL = {"clusters_named": 0, "entities_refined": 0, "anchors_generated": 0}

    # Phase 2: Cluster Refinement
    cl = server._A.get("clusters", {}).get("clusters", [])
    clusters_batch = {c["key"]: c.get("keywords", [])[:5] for c in cl}
    if clusters_batch:
        prompt = f"Name these clusters in 1-3 words. Return ONLY a JSON dictionary mapping keys to strings. clusters={json.dumps(clusters_batch)}"
        res = call_llm_batched(prompt, "topic-agent.md")
        if res and isinstance(res, dict):
            server.RUN["model_calls"] += 1
            server.RUN_INTERNAL["clusters_named"] = len(res)
            server.li_topics(names=res)

    server.li_entities()

    # Phase 3: Entity Refinement
    pages = server._A.get("pages", [])
    idx200 = [p for p in pages if server.analyzer.is_html(p) and server.analyzer.is_200(p) and server.analyzer.indexable(p)]
    inl = {server.analyzer._norm(p["Address"]): server.analyzer._int(p.get("Unique Inlinks")) for p in idx200}
    top_urls = sorted(inl, key=lambda u: -inl[u])[:40]
    
    entities_batch = {}
    for u in top_urls:
        kw = server._A.get("page_keywords", {}).get(u, [])
        if kw:
            entities_batch[u] = kw
            
    if entities_batch:
        prompt = f"Refine these entity lists to exactly 5-10 clean entities. Return ONLY a JSON dictionary mapping url strings to an array of string entities. urls={json.dumps(entities_batch)}"
        res = call_llm_batched(prompt, "topic-agent.md")
        if res and isinstance(res, dict):
            server.RUN["model_calls"] += 1
            server.RUN_INTERNAL["entities_refined"] = len(res)
            full_entities = dict(server._A.get("page_keywords", {}))
            full_entities.update(res)
            server.li_entities(entities=full_entities)

    # Phase 4: Anchor Refinement
    recs_batch = {}
    flat_recs = []
    for blk in server._A.get("link_candidates", []):
        for c in blk["candidates"]:
            flat_recs.append({
                "source": blk["source"],
                "target": c["target"],
                "relatedness": c["relatedness"],
                "reason": c.get("reason", ""),
                "suggested_anchor": c.get("suggested_anchor", "")
            })
            key = f"{blk['source']}->{c['target']}"
            recs_batch[key] = {
                "reason": c.get("reason", ""),
                "deterministic_anchor": c.get("suggested_anchor", "")
            }
            
    if recs_batch:
        prompt = f"Write specific, contextual anchor text (3-7 words) for these internal links. Use the reason and deterministic anchor as hints. Return ONLY a JSON dictionary mapping keys to strings. keys={json.dumps(recs_batch)}"
        res = call_llm_batched(prompt, "linker-agent.md")
        if res and isinstance(res, dict):
            server.RUN["model_calls"] += 1
            server.RUN_INTERNAL["anchors_generated"] = len(res)
            for r in flat_recs:
                key = f"{r['source']}->{r['target']}"
                if key in res:
                    r["suggested_anchor"] = res[key]
            
    server.li_set_recommendations(flat_recs)
    
    server.RUN["duration_sec"] = round(time.time() - t0, 1)
    server.li_report()
    server.li_export()

    s = server.RUN["summary"]
    print("\n=== INTERNAL LINKING INTELLIGENCE ===")
    print(f"Site            : {server.RUN['site']}  ({s['pages_crawled']} pages)")
    print(f"Internal links  : {s['internal_links']}")
    print(f"Orphan pages    : {s['orphan_pages']}")
    print(f"Broken internal : {s['broken_internal_links']}")
    print(f"Generic anchors : {s['generic_anchors']}")
    print(f"Topical clusters: {s['topical_clusters']}")
    print(f"Link suggestions: {s['link_recommendations']}")
    print("Wrote outputs/report.json and outputs/report.html")


if __name__ == "__main__":
    main()
