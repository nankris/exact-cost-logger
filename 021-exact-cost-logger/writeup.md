# I logged every Grok CLI call to the fraction of a cent. Most of the bill was the agent talking to itself.

*Draft for Tech in General: honest numbers from one session on 14 Oct 2026.*

I use AI coding CLIs for small everyday jobs: summarise this, write a quick function, explain an error, draft a tweet. I wanted to know what one of those really costs. A monthly estimate wasn't enough; I wanted the exact number for each call.

Grok Build CLI makes this easy. Run it headless with `--output-format json` and every call returns its token usage and a `total_cost_usd`. I wrote a 100-line wrapper that appends each call to a CSV, then ran 10 everyday prompts three times each.

## The headline

**About 1.1 cents per prompt.** All ten prompts once a day would come to about 11¢ a day, or roughly $3.30 a month at API rates.

That sounds cheap, and it is. The interesting part is *where* that cent goes.

## 86% of the cost is input I never wrote

My prompts are 50 to 150 words. Yet every call sent Grok about **20,000 input tokens** on average. Almost all of them are the CLI's own system prompt and tool definitions, which go out with every request.

Fitting the logged costs against the token counts gives the price list exactly (all 30 calls match to the last decimal):

- uncached input: $0.68 per million tokens
- cached input: $0.17 per million
- output: $2.04 per million, and **reasoning tokens count as output** (81% of my output tokens were reasoning)

The prompt cache helped: 42% of input tokens were cache reads at a quarter of the price. Input still made up 86% of the bill.

## The fix was one set of flags

I ran the same ten prompts again with a minimal setup:

```
--system-prompt-override "You are a concise helpful assistant." \
--disable-web-search --no-subagents --tools read_file
```

Input dropped from ~20K to ~5K tokens per call. **Cost dropped from 1.11¢ to 0.39¢, about 65% less**, and latency fell from 14s to 9.5s on average.

## Worse: 1 in 5 calls returned nothing

The real surprise was in the `stopReason` column. With the default setup, **6 of 30 calls ended in `cancelled` with no answer**:

- **Draft a tweet:** all three runs said something like "I'll look through the workspace for the blog post so the tweet matches", went looking in an empty folder, and stopped.
- **Regex help:** all three tried to run a shell command to test the pattern. In headless mode nobody can approve that, so the run was cancelled.

Those six calls cost 7.7¢ and produced only a one-line plan. The lean setup answered all 20 of its calls.

The default CLI is a *coding agent*. It assumes there is a repo to explore and commands to run, even when you just want a tweet.

## What I'm changing

1. **Chat-style jobs get the lean flags.** Same model, a third of the price, and it answers instead of exploring.
2. **Agent mode is for agent work.** If I want it to run tests, I pass `--always-approve` in a throwaway directory, on purpose.
3. **Log everything.** The wrapper is tiny and the CSV caught a silent failure I would never have noticed in the terminal.

## Caveats

- I'm on a SuperGrok subscription, so I don't actually pay per call. These are API-equivalent prices, which make a fair yardstick. What really limits me is the 5-hour usage window.
- This was one session with three runs per prompt, not a week of real use.
- The CLI chose the model (`grok-4.7-build`), and that can change on xAI's side.
- Five calls ran in parallel, which affects cache hits.

*The scripts, raw CSVs and every response are in the experiment repo.*
