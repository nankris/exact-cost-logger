# Same 10 prompts, but with a minimal agent config: short system prompt, one tool, no web/subagents.
import json, os, sys, tempfile, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__))
from grok_log import run_grok, QuotaHit
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(open(os.path.join(D, "scripts", "prompts.json")))
CSV = os.path.join(D, "results", "calls_lean.csv")
LEAN = ["--system-prompt-override", "You are a concise helpful assistant.", "--disable-web-search",
        "--no-subagents", "--tools", "read_file"]
def job(label, rep):
    r = run_grok(P[label], label, CSV, "021-lean", rep, cwd=tempfile.mkdtemp(), extra=LEAN)
    json.dump({"label": label, "rep": rep, "text": r["text"], "raw": r["raw"]},
              open(os.path.join(D, "results", "responses", f"lean_{label}_r{rep}.json"), "w"), indent=1)
    return label, rep, r["cost_usd"]
for rep in (1, 2):
    with cf.ThreadPoolExecutor(5) as ex:
        for f in cf.as_completed([ex.submit(job, l, rep) for l in P]):
            try: print(f.result(), flush=True)
            except QuotaHit as e: print("QUOTA HIT", e); sys.exit(3)
