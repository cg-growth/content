import { COINGECKO_API_KEY } from '$env/static/private';
import { CoinGecko } from '../providers/CoinGecko';
import type { Actions, PageServerLoad } from './$types';

export const actions: Actions = {
	default: async ({ request }) => {
		const formData = await request.formData();
		const query = formData.get('query') as string;
		if (!query || query.length < 3) return { result: null };
		const cg = new CoinGecko(COINGECKO_API_KEY);

		const [searchResult, onchainResult] = await Promise.all([
			cg.search(query),
			cg.onchainSearch(query)
		]);

		return {
			result: {
				search: searchResult,
				onchain: onchainResult
			}
		};
	}
};

export const load: PageServerLoad = async () => {
	return { result: null };
};
