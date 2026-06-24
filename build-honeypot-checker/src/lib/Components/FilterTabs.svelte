<script lang="ts">
	import { Tabs, TabItem, MultiSelect, Label, ButtonGroup, Range } from 'flowbite-svelte';
	import { networks } from '$lib/Data/AvailableNetworks.js';
	import FilterButton from '$lib/Components/FilterButton.svelte';
	import SorterButtonGroup from '$lib/Components/SorterButtonGroup.svelte';
	import {
		taxOptions,
		trendingSorters,
		txCountOptions,
		volumeOptions
	} from '$lib/Data/PoolSortingOptions';
	import DropDownButtonGroup from '$lib/Components/DropDownButtonGroup.svelte';

	let {
		selectedNetworks = $bindable(),
		checks = $bindable(),
		trendingSorter = $bindable(''),
		poolCreatedHoursMax = $bindable(),
		minFDV = $bindable(),
		maxFDV = $bindable(),
		minVolume = $bindable(),
		maxVolume = $bindable(),
		minTxCount = $bindable(),
		maxTxCount = $bindable(),
		maxBuyTax = $bindable()
	} = $props();

	let noHoneyPot = $state(false);
	let goodGtScore = $state(false);
	let onCoinGecko = $state(false);
	let hasSocial = $state(false);

	let derivedChecks = $derived(() => {
		const items = [];
		if (noHoneyPot) items.push('no_honeypot');
		if (goodGtScore) items.push('good_gt_score');
		if (onCoinGecko) items.push('on_coingecko');
		if (hasSocial) items.push('has_social');
		return items.join(',');
	});

	$effect(() => {
		checks = derivedChecks();
	});
</script>

<Tabs>
	<TabItem open title="Networks">
		<div class="flex w-full items-end gap-6">
			<div>
				<Label for="first_name" class="mb-2">Select Networks</Label>
				<MultiSelect placeholder="Choose Networks" items={networks} bind:value={selectedNetworks} />
				<p class="text-sm text-gray-500 dark:text-gray-400">
					<b>Tip:</b>
					Select one or more networks to filter by.
				</p>
			</div>
			<div class="min-w-[900px]">
				<Label class="mb-2">Sort by Trending</Label>
				<SorterButtonGroup options={trendingSorters} bind:selectedOption={trendingSorter}
				></SorterButtonGroup>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					<b>Tip:</b>
					Select one or more checks.
				</p>
			</div>
		</div>
	</TabItem>
	<TabItem open title="Pools">
		<div class="flex w-full items-start gap-6">
			<div>
				<Label for="first_name" class="mb-2">Checks</Label>
				<ButtonGroup class="*:ring-primary-700!">
					<FilterButton bind:isValue={noHoneyPot} label="No Honeypot" />
					<FilterButton bind:isValue={goodGtScore} label="Good GT Score" />
					<FilterButton bind:isValue={onCoinGecko} label="On Coingecko" />
					<FilterButton bind:isValue={hasSocial} label="Has Social" />
				</ButtonGroup>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					<b>Tip:</b>
					Select one or more checks.
				</p>
			</div>
			<div>
				<Label for="first_name" class="mb-2">Created Date</Label>
				<Range min="0" max="300" bind:value={poolCreatedHoursMax}></Range>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					<b>Tip:</b>
					Filter by Pools created in the last {poolCreatedHoursMax} hour(s).
				</p>
			</div>
		</div>
	</TabItem>
	<TabItem open title="Performance">
		<div class="flex w-full items-end gap-6">
			<div>
				<Label for="first_name" class="mb-2">FDV</Label>
				<div class="flex items-center gap-2">
					<DropDownButtonGroup name="Min" options={volumeOptions} bind:selectedOption={minFDV} />
					<DropDownButtonGroup name="Max" options={volumeOptions} bind:selectedOption={maxFDV} />
				</div>
			</div>

			<div>
				<Label for="first_name" class="mb-2">Volume</Label>
				<div class="flex items-center gap-2">
					<DropDownButtonGroup name="Min" options={volumeOptions} bind:selectedOption={minVolume} />
					<DropDownButtonGroup name="Max" options={volumeOptions} bind:selectedOption={maxVolume} />
				</div>
			</div>
			<div>
				<Label for="first_name" class="mb-2">Tx Count</Label>
				<div class="flex items-center gap-2">
					<DropDownButtonGroup
						name="Min"
						options={txCountOptions}
						bind:selectedOption={minTxCount}
					/>
					<DropDownButtonGroup
						name="Max"
						options={txCountOptions}
						bind:selectedOption={maxTxCount}
					/>
				</div>
			</div>
			<div>
				<Label for="first_name" class="mb-2">Max Buy Tax</Label>
				<div class="flex items-center gap-2">
					<SorterButtonGroup options={taxOptions} bind:selectedOption={maxBuyTax} />
				</div>
			</div>
		</div>
	</TabItem>
</Tabs>
