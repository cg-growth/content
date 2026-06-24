import fs from 'fs';
import path from 'path';
import type { CoinMarket } from '../types/coinMarket';
import type { MarketPrediction } from '../types/marketPrediction';
import type { CoinGecko } from '../../providers/CoinGecko';

const DATA_PATH = path.resolve('src/lib/data/prediction_markets.json');

export class PredictionMarketService {
	static generateMarkets(coins: CoinMarket[]): MarketPrediction[] {
		const now = new Date();
		const endDate = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
		const storedMarkets = this.loadMarkets();
		const markets: MarketPrediction[] = [];

		for (const coin of coins) {
			if (coin.id.includes('usd') || coin.symbol.toLowerCase().includes('usd')) {
				continue;
			}

			const coinId = coin.id;
			const stored = storedMarkets[coinId];

			const needsRefresh = !stored || this.daysSince(stored.prediction_start) >= 30;

			const market: MarketPrediction = needsRefresh
				? this.createNewMarket(coin, now, endDate)
				: {
						...stored,
						current_price: coin.current_price,
						market_cap: coin.market_cap,
						days_remaining: Math.max(
							0,
							Math.ceil((endDate.getTime() - now.getTime()) / (24 * 60 * 60 * 1000))
						)
					};

			markets.push(market);
		}

		this.saveMarkets(markets);
		return markets;
	}

	private static createNewMarket(coin: CoinMarket, now: Date, endDate: Date): MarketPrediction {
		const predictionPrice = this.generatePredictionPrice(coin.current_price);

		return {
			coinId: coin.id,
			name: coin.name,
			symbol: coin.symbol.toUpperCase(),
			image: coin.image,
			current_price: coin.current_price,
			market_cap: coin.market_cap,
			initial_price: coin.current_price,
			prediction_price: predictionPrice,
			prediction_start: now.toISOString().split('T')[0],
			prediction_end: endDate.toISOString().split('T')[0],
			days_remaining: 1,
			odds: {
				coinId: coin.id,
				yes: 0,
				no: 0,
				oddsYes: 1,
				oddsNo: 1
			}
		};
	}

	private static loadMarkets(): Record<string, MarketPrediction> {
		try {
			if (!fs.existsSync(DATA_PATH)) return {};
			const raw = fs.readFileSync(DATA_PATH, 'utf-8') || '{}';
			return JSON.parse(raw);
		} catch {
			return {};
		}
	}

	static async evaluateMarketOutcomes(coinGecko: CoinGecko): Promise<
		Array<{
			coinId: string;
			closed: boolean;
			outcome: 'yes' | 'no' | null;
		}>
	> {
		const markets = this.loadMarkets();
		const now = new Date();

		return Promise.all(
			Object.values(markets).map(async (market) => {
				const endDate = new Date(market.prediction_end);
				const closed = now >= endDate;
				let outcome: 'yes' | 'no' | null = null;

				if (closed) {
					const current_price = await coinGecko.getCoinById(market.coinId);
					outcome = current_price >= market.prediction_price ? 'yes' : 'no';
				}

				return {
					coinId: market.coinId,
					closed,
					outcome
				};
			})
		);
	}

	private static saveMarkets(markets: MarketPrediction[]): void {
		const marketMap: Record<string, MarketPrediction> = {};
		for (const market of markets) {
			marketMap[market.coinId] = market;
		}
		fs.writeFileSync(DATA_PATH, JSON.stringify(marketMap, null, 2));
	}

	private static generatePredictionPrice(currentPrice: number): number {
		const randomPercent = (Math.random() - 0.5) * 40;
		return Math.round(currentPrice * (1 + randomPercent / 100));
	}

	private static daysSince(dateStr: string): number {
		const startDate = new Date(dateStr);
		const now = new Date();
		return (now.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24);
	}
}
