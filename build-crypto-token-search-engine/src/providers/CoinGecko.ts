import axios from 'axios';
import type { SearchResponse } from '../types/search';
import type { OnchainSearchResponse } from '../types/onchain';

export class CoinGecko {
	private apiKey: string;
	private baseUrl = 'https://pro-api.coingecko.com/api/v3/';
	private headers = {};

	constructor(apiKey: string) {
		this.apiKey = apiKey;
		this.headers = { 'x-cg-pro-api-key': this.apiKey };
	}

	async search(query: string): Promise<SearchResponse> {
		const url = `${this.baseUrl}search?query=${encodeURIComponent(query)}`;
		const response = await axios.get<SearchResponse>(url, { headers: this.headers });
		return response.data;
	}

	async onchainSearch(query: string, chain?: string): Promise<OnchainSearchResponse> {
		let url = `${this.baseUrl}onchain/search/pools?query=${encodeURIComponent(query)}&include=base_token`;
		if (chain) {
			url += `&network=${encodeURIComponent(chain)}`;
		}
		const response = await axios.get<OnchainSearchResponse>(url, { headers: this.headers });
		return response.data;
	}
}
