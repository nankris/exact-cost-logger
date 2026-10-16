import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, os, json
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = pd.read_csv(f"{D}/results/calls.csv"); l = pd.read_csv(f"{D}/results/calls_lean.csv")
for x in (d, l):
    x["total_input_tokens"] = x.input_tokens + x.cache_read_input_tokens
# implied price per 1M tokens from exact least squares fit
X = d[["input_tokens", "cache_read_input_tokens", "output_tokens"]].values.astype(float)
coef, *_ = np.linalg.lstsq(X, d.cost_usd.values, rcond=None)
resid = float(np.abs(X @ coef - d.cost_usd.values).max())
agg = lambda x: x.groupby("label").agg(runs=("cost_usd", "size"), cost_mean=("cost_usd", "mean"), cost_min=("cost_usd", "min"),
        cost_max=("cost_usd", "max"), in_uncached=("input_tokens", "mean"), in_cached=("cache_read_input_tokens", "mean"),
        out=("output_tokens", "mean"), reasoning=("reasoning_tokens", "mean"), turns=("num_turns", "mean"), latency=("latency_s", "mean"))
a = agg(d); b = agg(l)
t = a[["runs", "cost_mean", "cost_min", "cost_max", "in_uncached", "in_cached", "out", "reasoning", "latency"]].copy()
t["lean_cost_mean"] = b.cost_mean; t["lean_saving_pct"] = (1 - b.cost_mean / a.cost_mean) * 100
t["default_answered"] = d.assign(ok=d.stop_reason == "end_turn").groupby("label").ok.sum()
t = t.sort_values("cost_mean", ascending=False)
t.round(5).to_csv(f"{D}/results/summary_by_prompt.csv")
s = dict(default_calls=len(d), lean_calls=len(l), default_total_usd=round(d.cost_usd.sum(), 4), lean_total_usd=round(l.cost_usd.sum(), 4),
         default_mean_usd=round(d.cost_usd.mean(), 5), lean_mean_usd=round(l.cost_usd.mean(), 5),
         default_mean_total_input=round(d.total_input_tokens.mean()), lean_mean_total_input=round(l.total_input_tokens.mean()),
         default_mean_output=round(d.output_tokens.mean()), default_cached_share=round(d.cache_read_input_tokens.sum() / d.total_input_tokens.sum(), 3),
         implied_price_per_M=dict(uncached_input=round(coef[0] * 1e6, 4), cached_input=round(coef[1] * 1e6, 4), output_incl_reasoning=round(coef[2] * 1e6, 4)),
         fit_max_abs_residual_usd=resid, reasoning_share_of_output=round(d.reasoning_tokens.sum() / d.output_tokens.sum(), 3),
         input_share_of_cost=round(float((d.input_tokens * coef[0] + d.cache_read_input_tokens * coef[1]).sum() / d.cost_usd.sum()), 3),
         models=sorted(set(d.model)), first_call=d.ts_ist.min(), last_call=l.ts_ist.max(),
         default_cancelled=int((d.stop_reason != "end_turn").sum()), lean_cancelled=int((l.stop_reason != "end_turn").sum()),
         cancelled_labels=sorted(set(d.label[d.stop_reason != "end_turn"])), cost_of_cancelled_usd=round(d.cost_usd[d.stop_reason != "end_turn"].sum(), 4),
         daily_10_prompts_default=round(a.cost_mean.sum(), 4), daily_10_prompts_lean=round(b.cost_mean.sum(), 4))
json.dump(s, open(f"{D}/results/summary.json", "w"), indent=1); print(json.dumps(s, indent=1)); print(t.round(4).to_string())
# chart
fig, ax = plt.subplots(figsize=(10, 5.5)); y = np.arange(len(t)); tt = t.iloc[::-1]
ax.barh(y + 0.2, tt.cost_mean * 100, 0.4, xerr=[(tt.cost_mean - tt.cost_min) * 100, (tt.cost_max - tt.cost_mean) * 100], color="#4C72B0", label="Grok Build CLI defaults (3 runs, min-max)", capsize=3)
ax.barh(y - 0.2, tt.lean_cost_mean * 100, 0.4, color="#DD8452", label="Lean config: short system prompt, 1 tool (2 runs)")
ax.set_yticks(y); ax.set_yticklabels([n.replace("_", " ") + ("" if tt.default_answered[n] == 3 else f"\n(default: {int(tt.default_answered[n])}/3 answered)") for n in tt.index]); ax.set_xlabel("API-equivalent cost per prompt (US cents)")
ax.set_title(f"What one everyday prompt costs in Grok Build CLI ({', '.join(s['models'])})\nmean {s['default_mean_usd']*100:.2f}¢ default vs {s['lean_mean_usd']*100:.2f}¢ lean; ~{s['default_mean_total_input']/1000:.0f}K input tokens per call by default")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=9); ax.grid(axis="x", alpha=.3); plt.tight_layout(); plt.savefig(f"{D}/cost_per_prompt.png", dpi=130)
