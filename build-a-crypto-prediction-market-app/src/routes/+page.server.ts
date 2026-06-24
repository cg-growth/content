import { COINGECKO_API_KEY } from '$env/static/private';
import { CoinGecko } from '../providers/CoinGecko';
import { PredictionMarketService } from '$lib/services/PredictionMarketService';
import { OddsService } from '$lib/services/OddsService';
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = async () => {
	const cg = new CoinGecko(COINGECKO_API_KEY);
	const coinMarkets = await cg.getCoins('usd', { ids: '', per_page: 50, page: 1 });
	const markets = PredictionMarketService.generateMarkets(coinMarkets);
	const marketOutcomes = await PredictionMarketService.evaluateMarketOutcomes(cg);

	// Example contract addresses for demo:
	const contractAddresses = [
		'0xf831938caf837cd505de196bbb408d81a06376ab',
		'0x6982508145454Ce325dDbE47a25d4ec3d2311933',
		'0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce'
	];

	const onChainTokens = await Promise.all(
		contractAddresses.map(async (address) => {
			const tokenData = await cg.getTokenDataByTokenAddress(address);
			const safe = await cg.getTokenInfoByTokenAddress(address);
			return {
				address,
				price: tokenData.price,
				image: tokenData.image,
				name: tokenData.name,
				symbol: tokenData.symbol,
				safe: safe
			};
		})
	);

	return {
		result: {
			markets,
			marketOutcomes,
			onChainTokens
		}
	};
};

export const actions: Actions = {
	vote: async ({ request }) => {
		const formData = await request.formData();
		const coinId = formData.get('coinId') as string;
		const type = formData.get('type') as 'yes' | 'no';

		OddsService.recordClick(coinId, type);

		return { success: true };
	}
};
