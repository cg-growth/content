<script lang="ts">
	import {
		Table,
		TableHead,
		TableHeadCell,
		TableBody,
		TableBodyRow,
		TableBodyCell
	} from 'flowbite-svelte';
	import PriceTag from '$lib/Components/PriceTag.svelte';
	import type { PoolData } from '$lib/Types/PoolData';

	interface Props {
		tableData: { data: { response: PoolData[] } };
	}

	let { tableData }: Props = $props();

	let openRow: number | null = $state(null);
	const toggleRow = (i: number) => {
		console.log('opening row');
		openRow = openRow === i ? null : i;
	};

	const formatNumber = (value: number): string => {
		return new Intl.NumberFormat('en-US', {
			notation: 'compact',
			compactDisplay: 'short'
		}).format(value);
	};
</script>

<Table shadow>
	<TableHead>
		<TableHeadCell>Name</TableHeadCell>
		<TableHeadCell>Created At</TableHeadCell>
		<TableHeadCell>Price 24h</TableHeadCell>
		<TableHeadCell>Buys vs Sells 24h</TableHeadCell>
		<TableHeadCell>Market Cap</TableHeadCell>
		<TableHeadCell>Network</TableHeadCell>
	</TableHead>
	<TableBody tableBodyClass="divide-y">
		{#each tableData.data.response as pool, i}
			<TableBodyRow class="cursor-pointer" on:click={() => toggleRow(i)}>
				<TableBodyCell>{pool.attributes.name}</TableBodyCell>
				<TableBodyCell
					><span class="font-normal"
						>{new Date(pool.attributes.pool_created_at).toLocaleString()}</span
					></TableBodyCell
				>
				<TableBodyCell>
					<PriceTag
						primaryNumber={pool.attributes.base_token_price_usd}
						primaryNumberType="absolute"
						secondaryNumber={pool.attributes.price_change_percentage.h24}
						secondaryNumberType="relative"
					/>
				</TableBodyCell>
				<TableBodyCell>
					<PriceTag
						primaryNumber={pool.attributes.transactions.h24.buys}
						primaryNumberType="raw"
						secondaryNumber={pool.attributes.transactions.h24.sells}
						secondaryNumberType="raw"
						layout="pipe"
						manualColor="dark"
					/></TableBodyCell
				>
				<TableBodyCell
					><span class="font-normal">${formatNumber(pool.attributes.market_cap_usd) ?? '-'}</span
					></TableBodyCell
				>
				<TableBodyCell
					><span class="font-normal">
						{pool.relationships.network.data.id} | {pool.relationships.dex.data.id}
					</span>
				</TableBodyCell>
			</TableBodyRow>
			{#if openRow === i}
				<TableBodyRow class="my-0 bg-slate-50 py-0">
					<TableBodyCell class="py-2">
						5m Change
						<div class="flex gap-2">
							<PriceTag
								primaryNumber={pool.attributes.price_change_percentage.m5}
								primaryNumberType="relative"
								noSecondary
							/>
							<PriceTag
								primaryNumber={pool.attributes.transactions.m5.buys}
								primaryNumberType="raw"
								secondaryNumber={pool.attributes.transactions.m5.sells}
								secondaryNumberType="raw"
								layout="pipe"
								manualColor="dark"
							/>
						</div>
					</TableBodyCell>
					<TableBodyCell class="py-px">
						1h Change
						<div class="flex gap-2">
							<PriceTag
								primaryNumber={pool.attributes.price_change_percentage.h1}
								primaryNumberType="relative"
								noSecondary
							/>
							<PriceTag
								primaryNumber={pool.attributes.transactions.h1.buys}
								primaryNumberType="raw"
								secondaryNumber={pool.attributes.transactions.h1.sells}
								secondaryNumberType="raw"
								layout="pipe"
								manualColor="dark"
							/>
						</div>
					</TableBodyCell>
					<TableBodyCell class="py-px">
						6h Change
						<div class="flex gap-2">
							<PriceTag
								primaryNumber={pool.attributes.price_change_percentage.h6}
								primaryNumberType="relative"
								noSecondary
							/>
							<PriceTag
								primaryNumber={pool.attributes.transactions.h6.buys}
								primaryNumberType="raw"
								secondaryNumber={pool.attributes.transactions.h6.sells}
								secondaryNumberType="raw"
								layout="pipe"
								manualColor="dark"
							/>
						</div>
					</TableBodyCell>
					<TableBodyCell class="py-px">
						Volume 24h
						<div class="flex gap-2">
							<PriceTag
								primaryNumber={pool.attributes.volume_usd.h24}
								primaryNumberType="absolute"
								noSecondary
								manualColor="dark"
							/>
						</div>
					</TableBodyCell>
					<TableBodyCell class="flex flex-col py-2">
						<span class="pb-4">Address</span>
						{pool.attributes.address}
					</TableBodyCell>
					<TableBodyCell class="py-2">
						<div class="flex gap-2"></div>
					</TableBodyCell>
				</TableBodyRow>
			{/if}
		{/each}
	</TableBody>
</Table>
