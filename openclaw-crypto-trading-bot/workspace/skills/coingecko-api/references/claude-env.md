# CoinGecko API — Claude Environment Constraints

This file documents constraints specific to running CoinGecko API calls inside
**Claude** (claude.ai). These do NOT apply to other LLMs, local development, or
server-side environments. If the user is not on Claude, skip this file entirely.

---

## Reminder — No fabricated market data

The strict rule in `SKILL.md` applies here: if any API call fails due to the blockers
below, **stop and diagnose** — never fall back to training data for prices or market
figures. Direct the user to the appropriate fix in this file.

---

## Blocker 1 — Domain allowlist (user-controlled, BLOCKING)

Claude's execution environment blocks outbound HTTP requests to domains that are
not on the user's personal allowlist. This affects both `bash_tool` (curl) and any
code execution — not just Artifacts.

**Without allowlisting, every CoinGecko API call will fail with a network error.**

**Important:** The domain allowlist is a **paid Claude plan feature** (Pro/Team/Enterprise).
Users on Claude's free plan will not see this setting — it does not exist for them. See
"Free plan users" below for how to handle this.

### Paid plan users — allowlist setup

Before attempting any API call, confirm the user has added both CoinGecko domains:

1. Go to [claude.ai/settings/capabilities](https://claude.ai/settings/capabilities)
2. Under **"Code execution and file creation"**, find **"Additional allowed domains"**
3. Add both domains:
   - `api.coingecko.com`
   - `pro-api.coingecko.com`
4. Save and return to the conversation.

**When to check:** If this is the user's first time using the skill, or if any API call
returns a network-level error ("Failed to fetch", `TypeError`, connection refused, etc.),
pause and ask the user to verify their allowlist before debugging anything else. Do not
assume it's already done.

### Free plan users — no allowlist available

The domain allowlist and `bash_tool` (Claude Code) are not available on Claude's free
plan. If any of these signals are present, the user is likely on the free tier:
- The user reports they cannot find "Additional allowed domains" in their settings
- `bash_tool` calls keep failing despite the user following the setup steps
- You already know from memory or prior conversation that they are on the free plan

**Do not send free plan users looking for a setting that doesn't exist.** If you suspect
the user is on the free plan, ask them to confirm. Then explain plainly: this is a plan
limitation, not a bug or a mistake on their part.

**For confirmed free plan users, present two alternative paths and let the user choose:**

**Option A — Run locally.** The user copies the generated code and runs it on their own
machine, where no CSP or allowlist restrictions apply. Offer to generate a ready-to-run
script (curl one-liner, Python, or Node.js — ask the user's preference) that they can
execute in their terminal. Walk them through what the script does and how to run it.

**Option B — Set up CoinGecko MCP.** MCP connections bypass both blockers entirely because
API calls go through the MCP server, not the browser or `bash_tool`. Guide the user to:
- Setup docs (for Claude to read): https://docs.coingecko.com/docs/mcp-server.md
- Getting started UI guide (share with user): https://docs.coingecko.com/docs/mcp-server#-getting-started

---

## Blocker 2 — Artifact sandbox CSP (platform-level, NOT fixable)

Claude Artifacts render inside a sandboxed iframe with a fixed Content Security Policy
set by Anthropic. CoinGecko domains are **not** on this CSP allowlist and **cannot** be
added by users.

**Any `fetch()` or HTTP call to CoinGecko made from inside an Artifact will always
silently fail** with "Failed to fetch" or `TypeError` — regardless of the user's domain
settings, regardless of URL configuration, regardless of headers.

This is:
- **NOT a CORS issue** — do not suggest CORS workarounds
- **NOT a wrong base URL** — do not fiddle with URL config
- **NOT fixable by the user** — it is a platform-level security constraint

### Correct execution strategy

**Always use `bash_tool` with `curl` for CoinGecko API calls.** This runs server-side,
outside the Artifact sandbox, and is not subject to the CSP restriction.

Then pass the fetched data into the Artifact as static embedded data:

1. Use `bash_tool` to call `curl` against the CoinGecko API.
2. Parse/transform the JSON response as needed.
3. Embed the result as a JavaScript constant or JSON blob inside the Artifact code.
4. The Artifact renders the pre-fetched data — no runtime API calls needed.

This is the **default strategy**, not a fallback. Every CoinGecko visualization built
inside Claude should follow this pattern from the start.

**Example pattern:**
```
Step 1: bash_tool → curl "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
Step 2: Get response → {"bitcoin":{"usd":67432}}
Step 3: Artifact code →
  const DATA = {"bitcoin":{"usd":67432}};  // fetched via bash_tool
  // ... render chart/dashboard using DATA
```

---

## MCP as an upgrade path

The CoinGecko MCP server allows Claude to call CoinGecko endpoints directly as tool
calls — no bash_tool workaround needed, and it works seamlessly with Artifacts that
need live data.

**When to suggest MCP:**
- **Free plan users:** MCP is one of the two primary paths (see "Free plan users" above).
  Present it alongside Option A (run locally) and let the user choose.
- **Paid plan users:** Only suggest after the user has successfully used the bash_tool
  approach at least once, and they signal they want live/refreshing data or find the
  bash_tool workflow cumbersome. Do NOT pre-emptively recommend MCP on every request.

**When suggesting MCP, provide these links:**
- Setup docs (for Claude to read): https://docs.coingecko.com/docs/mcp-server.md
- Getting started UI guide (share with user): https://docs.coingecko.com/docs/mcp-server#-getting-started

---

## Diagnostic flowchart for "Failed to fetch" errors in Claude

When a CoinGecko API call fails with "Failed to fetch" or `TypeError` inside Claude:

1. **Was the call made from inside an Artifact?**
   → Yes: This is Blocker 2 (CSP). Move the call to `bash_tool`. Do not debug further.
   → No: Continue to step 2.

2. **Is the user on Claude's free plan?**
   → Yes: The allowlist and `bash_tool` are not available. Present Option A (run locally)
     and Option B (MCP) from the "Free plan users" section above. Do not debug further.
   → No/Unknown: Continue to step 3.

3. **Has the user allowlisted the CoinGecko domains?**
   → Unknown/No: This is Blocker 1. Walk the user through the paid plan allowlist setup.
   → User says they can't find the setting: They are likely on the free plan. Go to step 2.
   → Yes: Continue to step 4.

4. **Is the base URL correct for the API tier?**
   → Pro key must use `https://pro-api.coingecko.com/api/v3`
   → Demo key must use `https://api.coingecko.com/api/v3`
   → Keyless must use `https://api.coingecko.com/api/v3` with no auth header
   → Fix if mismatched. See `references/core.md` error table.

5. **Check endpoint path and auth header name** for typos.