<script lang="ts">
	import { Listgroup, Avatar } from 'flowbite-svelte';
	import type { SearchResponse } from '../types/search';
	export let search: SearchResponse;
</script>

<div class="flex w-1/3 flex-col">
	<h5 class="mb-2 text-lg font-bold">Coins</h5>
	<Listgroup class="border-0 dark:bg-transparent!">
		{#each search.coins as coin}
			<div class="flex items-center space-x-4 py-2 rtl:space-x-reverse">
				<Avatar src={coin.large} alt={coin.name} class="shrink-0" />
				<div class="min-w-0 flex-1">
					<p class="truncate text-sm font-medium text-gray-900 dark:text-white">{coin.name}</p>
					<p class="truncate text-sm text-gray-500 dark:text-gray-400">{coin.symbol}</p>
				</div>
				<div class="inline-flex items-center text-base font-semibold text-gray-900 dark:text-white">
					{coin.market_cap_rank ? `Rank #${coin.market_cap_rank}` : ''}
				</div>
			</div>
		{/each}
	</Listgroup>

	{#if search.exchanges?.length}
		<h5 class="mt-6 mb-2 text-lg font-bold">Exchanges</h5>
		<Listgroup class="border-0 dark:bg-transparent!">
			{#each search.exchanges as exchange}
				<div class="flex items-center space-x-4 py-2 rtl:space-x-reverse">
					<Avatar src={exchange.large} alt={exchange.name} class="shrink-0" />
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-gray-900 dark:text-white">
							{exchange.name}
						</p>
						<p class="truncate text-sm text-gray-500 dark:text-gray-400">{exchange.market_type}</p>
					</div>
				</div>
			{/each}
		</Listgroup>
	{/if}

	{#if search.nfts?.length}
		<h5 class="mt-6 mb-2 text-lg font-bold">NFTs</h5>
		<Listgroup class="border-0 dark:bg-transparent!">
			{#each search.nfts as nft}
				<div class="flex items-center space-x-4 py-2 rtl:space-x-reverse">
					<Avatar src={nft.thumb} alt={nft.name} class="shrink-0" />
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-gray-900 dark:text-white">{nft.name}</p>
						<p class="truncate text-sm text-gray-500 dark:text-gray-400">{nft.symbol}</p>
					</div>
				</div>
			{/each}
		</Listgroup>
	{/if}

	{#if search.categories?.length}
		<h5 class="mt-6 mb-2 text-lg font-bold">Categories</h5>
		<Listgroup class="border-0 dark:bg-transparent!">
			{#each search.categories as category}
				<div class="flex items-center space-x-4 py-2 rtl:space-x-reverse">
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium text-gray-900 dark:text-white">
							{category.name}
						</p>
						<p class="truncate text-xs text-gray-500 dark:text-gray-400">ID: {category.id}</p>
					</div>
				</div>
			{/each}
		</Listgroup>
	{/if}
</div>
