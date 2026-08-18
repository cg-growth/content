import json
import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You score crypto news headlines for short-term price impact.

Return JSON only, matching this schema:
{"score": float, "confidence": float, "reasoning": string}

score: -1.0 (strongly bearish) to 1.0 (strongly bullish) for the coin named
confidence: 0.0 to 1.0

Score the likely effect on price, not whether the news is good in general.
Return score 0.0 and confidence 0.0 when a headline carries no clear
directional signal. Most headlines are noise, and scoring them as neutral
is the correct answer."""

def score_headline(title, source_name):
    """Convert a headline into a numeric trading signal."""
    # Source is included because a wire service and an unattributed blog
    # do not deserve the same weight
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Source: {source_name}\nHeadline: {title}"
        }],
    )
    return json.loads(message.content[0].text)

if __name__ == "__main__":
    samples = [
        ("Bitcoin Demand Strengthens as ETFs Add $865M and New Wallets Hit One-Year High", "Blockonomi"),
        ("Eliza Labs founder sells $25M in ElizaOS tokens as project collapses after lawsuit", "Crypto Briefing"),
        ("Crypto card spending hits $759 million in July 2026, led by USDC and USDT", "COINTURK NEWS"),
    ]
    for title, source in samples:
        result = score_headline(title, source)
        print(f"{result['score']:+.2f}  conf {result['confidence']:.2f}  {title[:58]}")
        print(f"       {result['reasoning']}\n")
