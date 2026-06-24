<script lang="ts">
	import { goto } from '$app/navigation';
	import { Pagination } from 'flowbite-svelte';
	import DataTable from '$lib/Components/DataTable.svelte';
	import FilterTabs from '$lib/Components/FilterTabs.svelte';

	let data = $props();
	let currentPage = $state(1);

	let selectedNetworks = $state([]);
	let checks = $state('');
	let trendingSorter = $state('');
	let poolCreatedHoursMax = $state(undefined);
	let minFDV = $state(undefined);
	let maxFDV = $state(undefined);
	let minVolume = $state(undefined);
	let maxVolume = $state(undefined);
	let minTxCount = $state(undefined);
	let maxTxCount = $state(undefined);
	let maxBuyTax = $state(undefined);
	let networkParams = $derived(() => selectedNetworks.join(','));

	const previous = () => {
		if (currentPage == 1) return;
		currentPage -= 1;
	};
	const next = () => {
		currentPage += 1;
	};

	$effect(() => {
		updateQueryParams();
	});

	const updateQueryParams = () => {
		const url = new URL(window.location.href);

		const queryParams: Record<string, string | undefined> = {
			page: currentPage.toString(),
			networks: networkParams(),
			checks,
			sort: trendingSorter,
			pool_created_hour_max: poolCreatedHoursMax,
			fdv_usd_min: minFDV,
			fdv_usd_max: maxFDV,
			h24_volume_usd_min: minVolume,
			h24_volume_usd_max: maxVolume,
			tx_count_min: minTxCount,
			tx_count_max: maxTxCount,
			buy_tax_percentage_max: maxBuyTax
		};

		Object.entries(queryParams).forEach(([key, value]) => {
			if (value) {
				url.searchParams.set(key, value);
			} else {
				url.searchParams.delete(key);
			}
		});

		goto(url.toString(), { replaceState: true });
	};
</script>

<div class="flex w-full flex-col gap-8 p-20">
	<h2 class="text-xl font-semibold">Pool Finder</h2>
	<p>Welcome to Pool Finder. Use this tool identify new and promising liquidity pools.</p>
	<div>
		<FilterTabs
			bind:selectedNetworks
			bind:checks
			bind:trendingSorter
			bind:poolCreatedHoursMax
			bind:minFDV
			bind:maxFDV
			bind:minVolume
			bind:maxVolume
			bind:minTxCount
			bind:maxTxCount
			bind:maxBuyTax
		></FilterTabs>
	</div>
	<DataTable tableData={data} />
	<div class="flex w-full items-center justify-center">
		<Pagination
			pages={[]}
			large
			on:previous={previous}
			on:next={next}
			on:change={updateQueryParams}
		>
			<span slot="prev">Prev</span>
		</Pagination>
	</div>
</div>
