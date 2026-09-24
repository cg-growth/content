from typesafe_sdk import Choice, Noul, Score

PERSONAS = {
    "market_maker_bot": "automated market maker, arbitrage or trading bot: very high trade counts, tiny margins, trades constantly across many pools",
    "sniper": "buys within minutes of a pool launching and flips quickly",
    "insider_like": "shows insider BEHAVIOUR on this token: got in at launch or before at a very low cost basis and is now selling or distributing into strength. Merely holding a large never-traded balance is NOT enough",
    "treasury_allocation": "never bought on-chain; holds a large balance received by transfer, like a team, treasury, vesting, investor or exchange custody wallet, and is not selling",
    "proven_trader": "discretionary trader with repeatable profits across MANY tokens (not just one or two), decent win rate, profits not from a single lucky hit",
    "one_hit_winner": "big profit that comes mostly from one or two tokens, with little other track record",
    "accumulator": "steadily buys and holds, rarely sells",
    "flipper": "trades many tokens quickly with mediocre or poor results",
    "whale": "very large portfolio or positions, not a bot, not clearly skilled",
    "new_wallet": "little history: few trades or tokens",
}
PERSONA_LABEL = {
    "market_maker_bot": "Market maker / bot", "sniper": "Sniper", "insider_like": "Insider-like", "treasury_allocation": "Treasury / allocation",
    "proven_trader": "Proven trader", "one_hit_winner": "One-hit winner", "accumulator": "Accumulator", "flipper": "Flipper",
    "whale": "Whale", "new_wallet": "New wallet", "protocol": "Protocol / contract",
}
STANCE = {"accumulating": "net buying recently", "holding": "holding without much activity", "distributing": "net selling recently", "exited": "sold out or nearly all"}

WALLET_QUESTIONS = {
    "persona": Choice(
        instructions="Which behaviour best describes this wallet, judged from its multi-chain lifetime PnL, portfolio, recent trading cadence, the tokens it trades, and its behaviour on this token?",
        criteria=PERSONAS,
    ),
    "skill": Score(
        instructions="Is this wallet's profit repeatable skill (profitable across many tokens, consistent, not one lucky hit, not insider access)?",
        criteria=["luck or none", "some", "proven"],
    ),
    "insider": Noul(
        instructions="Does this wallet act like an insider on this token: in at launch or before at a very low cost, then selling or distributing into strength? A never-traded treasury or custody balance alone is not insider behaviour."
    ),
    "copyable": Noul(instructions="Would copying this wallet's future trades likely be worthwhile: proven skill, not a bot, not an insider, human-sized trades?"),
    "stance": Choice(instructions="What is this wallet doing with this token right now?", criteria=STANCE),
}
WALLET_SIZES = {"skill": 3}

# Wallet-first (profile page and radar): no single-token context.
PROFILE_PERSONAS = {k: v for k, v in PERSONAS.items() if k not in ("insider_like", "treasury_allocation")}
STYLES = {
    "scalper": "many small, very short-lived trades",
    "swing_trader": "positions held hours to weeks",
    "position_holder": "buys and holds for long periods",
    "arbitrage_bot": "automated two-sided flow across pools",
}
TAGS = {
    "memecoin_focus": "Mostly trades memecoins or very new, speculative tokens (judge from the token names and symbols)",
    "bluechip_focus": "Mostly trades established large-cap tokens and majors (judge from the token names and symbols)",
    "early_buyer": "Habitually buys tokens very early in their life",
    "risk_manager": "Takes profits and cuts losses in a disciplined way (many small losses, fewer large wins)",
}
TAG_LABEL = {
    "memecoin_focus": "Memecoin-focused", "bluechip_focus": "Blue-chip focused", "early_buyer": "Early buyer", "risk_manager": "Disciplined exits",
    "high_frequency": "High-frequency", "multi_chain": "Multi-chain", "whale_sized": "Whale-sized", "stablecoin_heavy": "Stablecoin-heavy", "dormant": "Dormant",
}
PROFILE_QUESTIONS = {
    "persona": Choice(instructions="Which behaviour best describes this wallet overall, judged from its multi-chain lifetime PnL, portfolio, recent cadence and the tokens it trades?", criteria=PROFILE_PERSONAS),
    "skill": Score(instructions="Is this wallet's profit repeatable skill (profitable across many tokens, consistent, not one lucky hit)?", criteria=["luck or none", "some", "proven"]),
    "copyable": Noul(instructions="Would copying this wallet's future trades likely be worthwhile: proven skill, not a bot, human-sized trades, recently active?"),
    "style": Choice(instructions="Which trading style fits best?", criteria=STYLES),
    **{f"tag_{k}": Noul(instructions=v) for k, v in TAGS.items()},
}
PROFILE_SIZES = {"skill": 3}

VERDICTS = {
    "smart_money_accumulating": "proven traders and accumulators are net buying",
    "smart_money_distributing": "proven traders are net selling or exiting",
    "insider_heavy": "wallets showing insider behaviour hold a large share or are selling",
    "treasury_concentrated": "most supply sits in never-traded treasury, allocation or custody wallets; trading is a thin layer on top",
    "bot_heavy_trading": "the most active traders are bots and market makers (common for liquid tokens)",
    "organic_mixed": "broad, mixed holder and trader base with no dominant group",
}
VERDICT_LABEL = {
    "smart_money_accumulating": "Smart money accumulating", "smart_money_distributing": "Smart money distributing",
    "insider_heavy": "Insider-heavy", "treasury_concentrated": "Treasury-concentrated", "bot_heavy_trading": "Bot-heavy trading", "organic_mixed": "Organic / mixed",
}
TOKEN_QUESTIONS = {
    "verdict": Choice(instructions="Given this breakdown of who holds (by supply) and who trades (by volume), which verdict fits best?", criteria=VERDICTS),
    "quality": Score(instructions="Overall quality of the holder and trader base for a new buyer.", criteria=["poor", "mixed", "strong"]),
    "rug_signal": Noul(instructions="Do insider-behaving or dominant wallets look positioned to dump on new buyers?"),
}
TOKEN_SIZES = {"quality": 3}
