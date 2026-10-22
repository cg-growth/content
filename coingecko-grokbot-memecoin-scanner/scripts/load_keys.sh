# Fill empty settings from the keys files outside the repo.
# A value already set in the environment is kept. Files are not executed.
# Allowed names only. Values are never printed.
memescan_load_keys() {
  local f line key val allow
  allow=" COINGECKO_PRO_API_KEY COINGECKO_DEMO_API_KEY TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID TELEGRAM_FORWARD_URL TELEGRAM_FORWARD_KEY MEMESCAN_TZ PAPER_START_CASH PORT CHROME_BIN MEMESCAN_UTM "
  for f in "${HOME}/.coingecko/keys.env" "${HOME}/.grokbot-memecoin/keys.env"; do
    [ -f "$f" ] || continue
    while IFS= read -r line || [ -n "$line" ]; do
      line="${line#"${line%%[![:space:]]*}"}"
      case "$line" in
        ''|\#*) continue ;;
      esac
      line="${line#export }"
      key="${line%%=*}"
      val="${line#*=}"
      key="${key%"${key##*[![:space:]]}"}"
      key="${key#"${key%%[![:space:]]*}"}"
      case "$allow" in
        *" $key "*) ;;
        *) continue ;;
      esac
      if [ "${val#\"}" != "$val" ] && [ "${val%\"}" != "$val" ]; then
        val="${val#\"}"; val="${val%\"}"
      elif [ "${val#\'}" != "$val" ] && [ "${val%\'}" != "$val" ]; then
        val="${val#\'}"; val="${val%\'}"
      fi
      # non-empty environment wins; empty or unset is filled from the file
      if [[ -v $key ]] && [[ -n ${!key} ]]; then
        continue
      fi
      printf -v "$key" '%s' "$val"
      export "$key"
    done < "$f"
  done
}
