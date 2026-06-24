import axios from 'axios';
import type { CoinMarket } from '../lib/types/coinMarket';

export class CoinGecko {
	private apiKey: string;
	private baseUrl = 'https://pro-api.coingecko.com/api/v3/';
	private headers = {};

	constructor(apiKey: string) {
		this.apiKey = apiKey;
		this.headers = { 'x-cg-pro-api-key': this.apiKey };
	}

	async getCoins(
		vs_currency: string,
		options?: {
			ids?: string;
			order?: string;
			per_page?: number;
			page?: number;
			sparkline?: boolean;
			price_change_percentage?: string;
		}
	): Promise<CoinMarket[]> {
		const url = `${this.baseUrl}coins/markets`;
		const params = { vs_currency, ...options };
		const response = await axios.get<CoinMarket[]>(url, { headers: this.headers, params });
		return response.data;
	}

	async getCoinById(id: string, vs_currency: string = 'usd'): Promise<number> {
		const url = `${this.baseUrl}coins/${id}`;
		const params = {
			localization: false,
			tickers: false,
			market_data: true,
			community_data: false,
			developer_data: false,
			sparkline: false
		};
		const response = await axios.get(url, { headers: this.headers, params });
		const data = response.data;
		return data.market_data?.current_price?.[vs_currency] ?? 0;
	}

	async getTokenInfoByTokenAddress(contract_address: string): Promise<boolean> {
		const url = `${this.baseUrl}onchain/networks/eth/tokens/${contract_address}/info`;
		const response = await axios.get(url, { headers: this.headers });
		const data = response.data?.data?.attributes;
		const safe = !data?.is_honeypot && !data?.freeze_authority;
		return safe;
	}

	async getTokenDataByTokenAddress(
		contract_address: string
	): Promise<{ name: string; symbol: string; image: string; price: number }> {
		const url = `${this.baseUrl}onchain/networks/eth/tokens/${contract_address}`;
		const response = await axios.get(url, { headers: this.headers });
		const data = response.data?.data?.attributes;
		return {
			name: data?.name ?? '',
			symbol: data?.symbol ?? '',
			image: data?.image_url ?? '',
			price: parseFloat(data?.price_usd ?? '0')
		};
	}
}
