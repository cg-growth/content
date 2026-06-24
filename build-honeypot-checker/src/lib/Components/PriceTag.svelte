<script lang="ts">
	import { Alert } from 'flowbite-svelte';

	interface Props {
		primaryNumber: number | null;
		primaryNumberType?: 'absolute' | 'relative' | 'raw';
		secondaryNumber?: number | null;
		secondaryNumberType?: 'absolute' | 'relative' | 'raw';
		noSecondary?: boolean;
		layout?: 'brackets' | 'pipe';
		manualColor?: 'blue' | 'green' | 'red' | 'yellow' | 'dark';
	}

	let {
		primaryNumber,
		primaryNumberType = 'absolute',
		secondaryNumber = null,
		secondaryNumberType = 'relative',
		noSecondary = false,
		layout = 'brackets',
		manualColor
	}: Props = $props();

	let colorSeverity = $derived(() => {
		if (manualColor) {
			return manualColor;
		}
		return secondaryNumber && secondaryNumber > 0 ? 'green' : 'red';
	});

	let symbol = $derived(() =>
		secondaryNumber && secondaryNumberType !== 'raw' && secondaryNumber > 0 ? '+' : ''
	);

	const formatNumber = (num: number): string => {
		if (num === null || isNaN(num)) return '-';
		return num.toLocaleString(undefined, { maximumSignificantDigits: 2 });
	};

	let formattedPrimaryNumber = $derived(() => {
		if (primaryNumber === null) return '-';
		const formatted = formatNumber(Number(primaryNumber));
		if (primaryNumberType === 'raw') {
			return formatted;
		}
		return primaryNumberType === 'absolute' ? `$${formatted}` : `${formatted}%`;
	});

	let formattedSecondaryNumber = $derived(() => {
		if (!secondaryNumber || noSecondary) return null;

		const formatted = formatNumber(Number(secondaryNumber));
		if (secondaryNumberType === 'raw') {
			return `${symbol()}${formatted}`;
		}
		return secondaryNumberType === 'absolute'
			? `${symbol()}$${formatted}`
			: `${symbol()}${formatted}%`;
	});
</script>

<Alert color={colorSeverity()} class="max-w-fit py-1">
	<div class="flex items-center justify-center gap-2">
		<span class="font-medium">{formattedPrimaryNumber()}</span>
		{#if formattedSecondaryNumber()}
			{#if layout === 'pipe'}
				|
				<span class="font-medium">{formattedSecondaryNumber()}</span>
			{:else}
				<span class="font-medium">({formattedSecondaryNumber()})</span>
			{/if}
		{/if}
	</div>
</Alert>
