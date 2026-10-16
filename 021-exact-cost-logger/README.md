# #021 Exact cost logger: what my everyday Grok prompts really cost

**Question.** What does one ordinary prompt cost when I run it through Grok Build CLI, to the fraction of a cent, and where does the money go?

**Answer, short.** About **1.1¢ per prompt** with the CLI's default agent setup. **86% of that is input tokens**, mostly the agent's own system prompt and tool definitions (~13–15K tokens), not my prompt. A stripped-down config (short system prompt, one tool, no web search) brought it to **0.39¢**, 65% less, and answered every prompt. With the defaults, **6 of 30 calls (all 3 `draft_tweet` and all 3 `regex_help` runs) were cancelled with no answer**, and I still paid for them.

## Setup
- Grok Build CLI 1.0.52, signed in with a SuperGrok subscription. The model the CLI reported for every call was `grok-4.7-build`.
- Headless: `grok --no-auto-update -p "<prompt>" --output-format json`. The JSON includes `usage` (input, cache-read, cache-creation, output and reasoning tokens), `total_cost_usd`, `total_cost_usd_ticks`, `num_turns` and `stopReason`.
- Each call ran in a fresh empty temp directory, with `--disable-web-search`.
- 10 everyday prompts (`scripts/prompts.json`): summarise text, write a function, explain an error, draft a tweet, regex help, SQL query, translate to Telugu, email reply, code review, explain a concept.
- **Default config:** 3 runs per prompt (30 calls), 5 in parallel.
- **Lean config:** 2 runs per prompt (20 calls), with `--system-prompt-override "You are a concise helpful assistant." --disable-web-search --no-subagents --tools read_file`.
- Run on 2026-10-14, 19:25–19:29 IST.

## The wrapper
`scripts/grok_log.py` runs one CLI call and appends one row to a CSV: label, rep, model, tokens (input, cache read, cache creation, total input, cached share, output, reasoning), cost in USD and ticks, latency, turns, exit code, stop reason, and whether it hit a limit. It also writes a STOP file and refuses further calls once Grok returns a usage or rate limit, so a batch can't retry in a loop.

```bash
source /workspace/tools/setup.sh
python scripts/grok_log.py --csv results/mylog.csv --label summarise --prompt "Summarise: ..."
# batch runs used for this post
python scripts/run_021.py        # default config, 3 reps -> results/calls.csv
python scripts/run_021_lean.py   # lean config, 2 reps   -> results/calls_lean.csv
python scripts/analyse_021.py    # -> results/summary.json, results/summary_by_prompt.csv, cost_per_prompt.png
```

**Token accounting gotcha.** Grok CLI's `input_tokens` **excludes** cache reads (Anthropic-style). Total input is `input_tokens + cache_read_input_tokens`. Codex CLI is the opposite: there, `input_tokens` includes the cached tokens.

## Implied price list
A least-squares fit of `total_cost_usd` on the three token counts reproduces all 30 costs **exactly** (max residual ~5e-18 USD):

| token type | USD per 1M |
|---|---|
| uncached input | 0.68 |
| cached input (cache read) | 0.17 |
| output (reasoning included) | 2.04 |

Reasoning tokens make up **81%** of output tokens and are billed as output.

## Results (default config, 3 runs each; lean, 2 runs each)

| prompt | mean ¢ | min–max ¢ | uncached in | cached in | out (reasoning) | default answered | lean mean ¢ | lean saving |
|---|---|---|---|---|---|---|---|---|
| draft_tweet | 1.51 | 1.39–1.65 | 13,708 | 17,920 | 1,320 (1,079) | **0/3** | 0.61 | 60% |
| write_function | 1.36 | 1.20–1.49 | 12,701 | 19,157 | 832 (656) | 3/3 | 0.37 | 73% |
| explain_concept | 1.19 | 1.01–1.32 | 13,425 | 2,261 | 1,144 (987) | 3/3 | 0.35 | 71% |
| email_reply | 1.17 | 1.11–1.29 | 11,214 | 20,395 | 306 (196) | 3/3 | 0.31 | 74% |
| regex_help | 1.07 | 0.81–1.22 | 10,975 | 4,736 | 1,173 (976) | **0/3** | 0.50 | 53% |
| code_review | 1.02 | 0.77–1.17 | 10,990 | 4,736 | 957 (787) | 3/3 | 0.42 | 59% |
| explain_error | 1.01 | 1.00–1.02 | 13,677 | 2,048 | 226 (115) | 3/3 | 0.32 | 68% |
| translate | 1.00 | 0.80–1.25 | 9,976 | 5,717 | 1,113 (995) | 3/3 | 0.39 | 61% |
| sql_query | 0.93 | 0.68–1.07 | 11,232 | 4,480 | 458 (348) | 3/3 | 0.32 | 66% |
| summarise_text | 0.86 | 0.61–0.99 | 11,022 | 4,779 | 155 (50) | 3/3 | 0.32 | 63% |

| | default | lean |
|---|---|---|
| calls | 30 | 20 |
| mean cost per call | **1.11¢** | **0.39¢** |
| mean total input tokens per call | 20,515 | 5,046 |
| share of input tokens served from cache | 42% | 23% (1,152 of ~5K) |
| mean latency | 14.2 s | 9.5 s |
| calls with no answer (`stopReason: cancelled`) | 6 (7.7¢ wasted) | 0 |
| all 10 prompts once a day | 11.1¢/day ≈ $3.3/month | 3.9¢/day ≈ $1.2/month |

Total spend for this experiment: $0.33 (default) + $0.08 (lean), at API-equivalent rates.

Chart: `cost_per_prompt.png`.

## What happened to the cancelled calls
With the default agent setup the model treats every prompt as a coding-agent task. For `draft_tweet` it went looking in the (empty) workspace for the blog post ("I'll look through the workspace for the blog post…"). For `regex_help` it tried to run a shell command to test the pattern. Headless mode without `--always-approve` can't approve tool calls, so the run ends with `stopReason: cancelled` and the only text is the preamble. `email_reply` and `write_function` also took an extra turn looking around the workspace, but did answer. All of this is in `results/responses/`.

## Caveats
- `total_cost_usd` is the CLI's **API-equivalent** price. On a SuperGrok subscription I don't pay per call; what actually limits me is the 5-hour usage window. These numbers are what it would cost on metered pricing and a fair way to compare setups.
- The plan was "10 prompts for a week". This is **one session** (3 runs per prompt), so it shows cost per prompt type, not a week of real habits.
- Prompt-cache hits depend on timing and parallelism. Calls ran 5 at a time, which affects how much of the system prompt was already cached.
- The lean config changes behaviour as well as cost (no web, no shell). It's right for chat-style prompts and wrong for agentic coding work.
- The CLI picked the model (`grok-4.7-build`). A sanity call made a few minutes before the batch reported `grok-4.6-build`, so the default model can change on the server side.
- The prompts contain no private data.
