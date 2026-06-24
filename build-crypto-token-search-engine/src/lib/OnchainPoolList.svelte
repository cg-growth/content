<script lang="ts">
	import type { OnchainSearchResponse } from '../types/onchain';
	import { Card } from 'flowbite-svelte';
	export let onchain: OnchainSearchResponse;
	console.log(onchain);
</script>

<div>
	<h5 class="mb-4 text-lg font-bold">Onchain Tokens</h5>

	{#if onchain.included?.length}
		<div class="grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-2">
			{#each onchain.included as token}
				<a
					class="min-w-60"
					href={`https://arbiscan.io/address/${token.attributes.address}`}
					target="_blank"
					rel="noopener noreferrer"
				>
					<Card class=" cursor-pointer transition-transform hover:scale-[1.02]">
						<div class="flex gap-2 p-2">
							<img
								src={token.attributes.image_url}
								alt={token.attributes.name}
								class="h-12 w-12 rounded-full"
							/>
							<div>
								<h5 class="text-lg font-semibold text-gray-900 dark:text-white">
									{token.attributes.name} ({token.attributes.symbol})
								</h5>
								<p class="truncate text-xs text-gray-500 dark:text-gray-400">
									<span
										class="block w-40 overflow-hidden font-mono text-ellipsis whitespace-nowrap"
									>
										{token.attributes.address}</span
									>
								</p>
							</div>
						</div>
					</Card>
				</a>
			{/each}
		</div>
	{:else}
		<p class="text-xs text-gray-400">No onchain tokens found for this query.</p>
	{/if}
</div>
