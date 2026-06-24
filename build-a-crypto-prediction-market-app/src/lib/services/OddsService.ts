import fs from 'fs';
import path from 'path';
import type { OddsEntry } from '../types/oddsEntry';
import type { MarketPrediction } from '../types/marketPrediction';

const DATA_PATH = path.resolve('src/lib/data/prediction_markets.json');

export class OddsService {
	static recordClick(coinId: string, type: 'yes' | 'no'): void {
		const markets = this.loadMarkets();
		const market = markets[coinId];

		if (!market) return;

		const odds = market.odds;
		odds[type]++;

		const total = odds.yes + odds.no;
		odds.oddsYes = total ? (odds.no + 1) / (odds.yes + 1) : 1;
		odds.oddsNo = total ? (odds.yes + 1) / (odds.no + 1) : 1;

		this.saveMarkets(markets);
	}

	static getOdds(coinId: string): OddsEntry | undefined {
		const markets = this.loadMarkets();
		return markets[coinId]?.odds;
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

	private static saveMarkets(markets: Record<string, MarketPrediction>): void {
		fs.writeFileSync(DATA_PATH, JSON.stringify(markets, null, 2));
	}
}
