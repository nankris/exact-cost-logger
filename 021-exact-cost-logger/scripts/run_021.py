import json, os, sys, tempfile, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__))
from grok_log import run_grok, QuotaHit
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(open(os.path.join(D, "scripts", "prompts.json")))
CSV = os.path.join(D, "results", "calls.csv")
REPS = int(os.environ.get("REPS", 3))
os.makedirs(os.path.join(D, "results", "responses"), exist_ok=True)
def job(label, rep):
    wd = tempfile.mkdtemp(prefix=f"g021_{label}_")  # empty dir: no repo context
    r = run_grok(P[label], label, CSV, "021", rep, cwd=wd, extra=["--disable-web-search"])
    json.dump({"label": label, "rep": rep, "text": r["text"], "raw": r["raw"]},
              open(os.path.join(D, "results", "responses", f"{label}_r{rep}.json"), "w"), indent=1)
    return label, rep, r["cost_usd"], r["latency_s"]
for rep in range(1, REPS + 1):   # one rep at a time across prompts, 5 in parallel
    with cf.ThreadPoolExecutor(5) as ex:
        futs = [ex.submit(job, l, rep) for l in P]
        for f in cf.as_completed(futs):
            try: print(f.result(), flush=True)
            except QuotaHit as e: print("QUOTA HIT", e); sys.exit(3)
