import type { Filter } from '$lib/Types/Filter';
import type { PoolData } from '$lib/Types/PoolData';
import { buildQueryString } from '$lib/Utils/QueryParser';

class CoinGecko {
	private root: string;
	private headers: Record<string, string>;

	constructor(apiKey: string) {
		this.root = 'https://pro-api.coingecko.com/api/v3';
		this.headers = {
			accept: 'application/json',
			'x-cg-pro-api-key': apiKey
		};
	}

	async getFilteredPools(filter: Filter): Promise<PoolData[]> {
		const queryString = buildQueryString(filter);
		const requestUrl = `${this.root}/onchain/pools/megafilter?${queryString}`;
		console.log(requestUrl);

		const response = await fetch(requestUrl, { headers: this.headers });

		if (!response.ok) {
			console.error(`Error fetching data: ${response.statusText}`);
			return [];
		}

		const result = await response.json();
		return result.data as PoolData[];
	}
}

export default CoinGecko;
