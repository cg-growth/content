#!/usr/bin/env bash
# Env precedence for keys files, and start.sh with no key. Values are not printed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=../scripts/load_keys.sh
source "$ROOT/scripts/load_keys.sh"

tmp="$(mktemp -d)"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT
export HOME="$tmp"
mkdir -p "$HOME/.coingecko" "$HOME/.grokbot-memecoin"
printf '%s\n' 'COINGECKO_DEMO_API_KEY=file-value-b' > "$HOME/.coingecko/keys.env"

export COINGECKO_DEMO_API_KEY="env-value-a"
memescan_load_keys
[ "$COINGECKO_DEMO_API_KEY" = "env-value-a" ] || { echo "env did not win"; exit 1; }

unset COINGECKO_DEMO_API_KEY
memescan_load_keys
[ "$COINGECKO_DEMO_API_KEY" = "file-value-b" ] || { echo "empty name was not filled from the file"; exit 1; }

export COINGECKO_DEMO_API_KEY=""
memescan_load_keys
[ "$COINGECKO_DEMO_API_KEY" = "file-value-b" ] || { echo "empty value was not filled from the file"; exit 1; }

printf '%s\n' 'COINGECKO_PRO_API_KEY="quoted-pro"' 'TELEGRAM_BOT_TOKEN=$(echo should-not-run)' > "$HOME/.grokbot-memecoin/keys.env"
unset COINGECKO_PRO_API_KEY TELEGRAM_BOT_TOKEN
memescan_load_keys
[ "$COINGECKO_PRO_API_KEY" = "quoted-pro" ] || { echo "quotes were not stripped"; exit 1; }
[ "$TELEGRAM_BOT_TOKEN" = '$(echo should-not-run)' ] || { echo "file was executed"; exit 1; }

# a name outside the allowlist is ignored
printf '%s\n' 'NOT_A_KEY=ignored' >> "$HOME/.coingecko/keys.env"
memescan_load_keys
[ -z "${NOT_A_KEY:-}" ] || { echo "allowlist missed a name"; exit 1; }

unset COINGECKO_DEMO_API_KEY COINGECKO_PRO_API_KEY TELEGRAM_BOT_TOKEN
# no key: start.sh must refuse before any service starts
empty="$(mktemp -d)"
set +e
out="$(env -u COINGECKO_DEMO_API_KEY -u COINGECKO_PRO_API_KEY -u CG_TIER -u MEMESCAN_CG_TIER HOME="$empty" bash "$ROOT/start.sh" 2>&1)"
code=$?
set -e
rm -rf "$empty"
[ "$code" -ne 0 ] || { echo "start.sh exited 0 with no key"; exit 1; }
printf '%s\n' "$out" | grep -q "CoinGecko API key" || { echo "start.sh missing-key message not found"; exit 1; }
printf '%s\n' "$out" | grep -q "utm_source=grokbot" || { echo "start.sh link was not tagged"; exit 1; }
printf '%s\n' "$out" | grep -q "utm_content=start-no-key-pricing" || { echo "start.sh missing pricing link"; exit 1; }
printf '%s\n' "$out" | grep -q "utm_content=start-no-key#api-keys" || { echo "start.sh missing dashboard link"; exit 1; }
printf '%s\n' "$out" | grep -q "New to CoinGecko API" || { echo "start.sh missing new-account line"; exit 1; }
if printf '%s\n' "$out" | grep -q "Create a key"; then echo "start.sh still leads with creating a key on the dashboard"; exit 1; fi
# The new-account pricing link comes before the existing-account dashboard link.
pricing_at="$(printf '%s\n' "$out" | grep -n "en/api/pricing" | head -n 1 | cut -d: -f1)"
dash_at="$(printf '%s\n' "$out" | grep -n "developers/dashboard" | head -n 1 | cut -d: -f1)"
[ -n "$pricing_at" ] && [ -n "$dash_at" ] && [ "$pricing_at" -lt "$dash_at" ] || { echo "start.sh pricing link is not before the dashboard link"; exit 1; }

echo "env precedence and no-key start: ok"
