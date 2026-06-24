<script lang="ts">
	import type { MarketPrediction } from '$lib/types/marketPrediction';
	import MarketCard from '$lib/MarketCard.svelte';
	import { invalidateAll } from '$app/navigation';
	import OnChainTokenCard from '$lib/OnChainTokenCard.svelte';

	let { data } = $props();
	let markets = $state(data?.result.markets ?? ([] as MarketPrediction[]));
	let marketOutcomes = $state(data?.result.marketOutcomes ?? []);
	let onChainTokens = $state(data?.result.onChainTokens ?? []);

	$effect(() => {
		markets = data?.result.markets ?? [];
	});

	function getOutcomeForMarket(market: MarketPrediction) {
		const found = marketOutcomes.find((o) => o.coinId === market.coinId);
		return found ?? { closed: false, outcome: null };
	}

	async function handleVote(coinId: string, type: 'yes' | 'no') {
		const formData = new FormData();
		formData.append('coinId', coinId);
		formData.append('type', type);

		const res = await fetch('./?/vote', {
			method: 'POST',
			body: formData
		});

		if (res.ok) {
			await invalidateAll();
		}
	}
</script>

<div class=" flex min-h-screen w-full flex-col items-center py-8">
	<div class="container mx-auto max-w-7xl px-4">
		<h2 class="mb-6 text-center text-3xl font-bold">Prediction Markets</h2>
		{#if markets.length}
			<div class="grid w-full grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
				{#each markets as market}
					<MarketCard outcome={getOutcomeForMarket(market)} coin={market} onVote={handleVote} />
				{/each}
			</div>
		{:else}
			<p class="text-center text-gray-500">Loading prediction markets...</p>
		{/if}
	</div>

	<div class="container mx-auto mt-10 max-w-7xl px-4 pb-20">
		<h2 class="mb-4 text-center text-2xl font-bold">On-Chain Tokens</h2>
		<div class="flex gap-10">
			{#each onChainTokens as token}
				<OnChainTokenCard {token} />
			{/each}
		</div>
	</div>
</div>
<div class="my-20"></div>
