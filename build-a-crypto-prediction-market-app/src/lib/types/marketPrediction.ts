import type { OddsEntry } from './oddsEntry';

export interface MarketPrediction {
	coinId: string;
	name: string;
	symbol: string;
	image: string;
	current_price: number;
	market_cap: number;
	initial_price: number;
	prediction_price: number;
	prediction_start: string;
	prediction_end: string;
	days_remaining: number;
	odds: OddsEntry;
}
