<script lang="ts">
	import { Search, Card } from 'flowbite-svelte';
	import { enhance } from '$app/forms';
	import { fade } from 'svelte/transition';
	import CoinList from '$lib/CoinList.svelte';
	import OnchainPoolList from '$lib/OnchainPoolList.svelte';

	export let data;
	export let form;
	let query = '';
	let formEl: HTMLFormElement;
	let debounceTimeout: ReturnType<typeof setTimeout>;
	let loading = false;

	$: results = form?.result ?? data?.result;
	$: active = query.length > 2 || loading || results;

	$: if (formEl) {
		clearTimeout(debounceTimeout);
		if (query.length > 2) {
			loading = true;
			debounceTimeout = setTimeout(() => {
				formEl.requestSubmit();
			}, 300); //Delay for auto search
		}
	}

	$: if (results) {
		loading = false;
	}
</script>

<div class="flex h-screen w-full flex-col items-center justify-center">
	<div
		class="search-container flex w-11/12 flex-col items-center justify-center gap-6 xl:w-3/5 {active
			? 'active'
			: ''}"
	>
		<form
			class="w-full"
			method="POST"
			use:enhance={() => {
				return async ({ update }) => {
					update({ reset: false });
				};
			}}
			bind:this={formEl}
		>
			<Search clearable bind:value={query} name="query" placeholder="Search token..." required />
		</form>
		{#if active}
			<div class="flex w-full items-center justify-center" transition:fade>
				<Card class="max-h-[70vh] w-full overflow-y-auto p-6" size="xl">
					<div class="flex w-full flex-col gap-8 lg:flex-row">
						{#if results?.search?.coins?.length}
							<CoinList search={results.search} />
						{:else}
							<p class="text-center text-gray-500">No coins found.</p>
						{/if}

						{#if results?.onchain?.data?.length}
							<OnchainPoolList onchain={results.onchain} />
						{/if}
					</div>
				</Card>
			</div>
		{/if}
	</div>
</div>
