import CoinGecko from '$lib/Providers/CGProvider';
import { error } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import type { PageServerLoad } from './$types';
import type { Filter } from '$lib/Types/Filter';

const cg = new CoinGecko(env.CG_API_KEY ?? '');

export const load: PageServerLoad = async (request) => {
	const searchParams = new URL(request.url).searchParams;
	const filters: Filter = {
		page: searchParams.get('page') ?? '1',
		networks: searchParams.get('networks') ?? undefined,
		dexes: searchParams.get('dexes') ?? undefined,
		sort: searchParams.get('sort') ?? undefined,
		fdv_usd_min: searchParams.get('fdv_usd_min') ?? undefined,
		fdv_usd_max: searchParams.get('fdv_usd_max') ?? undefined,
		h24_volume_usd_min: searchParams.get('h24_volume_usd_min') ?? undefined,
		h24_volume_usd_max: searchParams.get('h24_volume_usd_max') ?? undefined,
		pool_created_hour_min: searchParams.get('pool_created_hour_min') ?? undefined,
		pool_created_hour_max: searchParams.get('pool_created_hour_max') ?? undefined,
		tx_count_min: searchParams.get('tx_count_min') ?? undefined,
		tx_count_max: searchParams.get('tx_count_max') ?? undefined,
		tx_count_duration: searchParams.get('tx_count_duration') ?? undefined,
		buys_min: searchParams.get('buys_min') ?? undefined,
		buys_max: searchParams.get('buys_max') ?? undefined,
		buy_tax_percentage_max: searchParams.get('buy_tax_percentage_max') ?? undefined,
		sells_min: searchParams.get('sells_min') ?? undefined,
		sells_max: searchParams.get('sells_max') ?? undefined,
		checks: searchParams.get('checks') ?? undefined
	};
	try {
		const response = await cg.getFilteredPools(filters);

		if (!response || response.length === 0) {
			// If no data is found, return a 404 error
			throw error(404, 'Not found');
		}
		return {
			response
		};
	} catch (err) {
		console.error(err);
		throw error(500, 'Error fetching chart data');
	}
};
