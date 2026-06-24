<script lang="ts">
	import type { MarketPrediction } from '$lib/types/marketPrediction';
	import { Button, Progressbar, Card, Avatar } from 'flowbite-svelte';
	import { sineOut } from 'svelte/easing';

	let { coin, outcome, onVote } = $props<{
		coin: MarketPrediction;
		outcome?: { closed: boolean; outcome: 'yes' | 'no' | null };
		onVote: (coinId: string, type: 'yes' | 'no') => void;
	}>();

	const emitVote = (type: 'yes' | 'no') => {
		onVote(coin.coinId, type);
	};

	let yesPercentage = $derived(
		Math.round((coin.odds.yes / (coin.odds.yes + coin.odds.no)) * 100) || 50
	);
	let noPercentage = $derived(100 - yesPercentage);

	let formattedEndDate = $derived(
		new Date(coin.prediction_end).toLocaleDateString('en-US', {
			month: 'long',
			day: 'numeric'
		})
	);

	let statusText = $derived(() => {
		if (outcome?.closed) {
			return `Market closed: Winner is ${outcome.outcome ? outcome.outcome.toUpperCase() : 'N/A'}`;
		}
		return `Will it reach $${coin.prediction_price.toLocaleString()} by ${formattedEndDate}?`;
	});

	let statusClass = $derived(() => {
		if (outcome?.closed) {
			return outcome.outcome === 'yes'
				? 'text-green-600'
				: outcome.outcome === 'no'
					? 'text-red-600'
					: '';
		}
		return '';
	});

	let winningAmount = $derived(() => {
		if (!outcome?.closed || !outcome?.outcome) return null;
		if (outcome.outcome === 'yes') {
			return coin.odds.yes * coin.odds.oddsYes;
		} else if (outcome.outcome === 'no') {
			return coin.odds.no * coin.odds.oddsNo;
		}
		return 0;
	});

	let oddsPrimeDivision = $derived(() => {
		const yes = coin.odds.yes;
		const no = coin.odds.no;
		if (yes === 0 && no === 0) return '0 : 0';
		if (yes === 0) return `0 : 1`;
		if (no === 0) return `1 : 0`;
		function gcd(a: number, b: number): number {
			return b === 0 ? a : gcd(b, a % b);
		}
		const divisor = gcd(yes, no);
		return `${yes / divisor} : ${no / divisor}`;
	});
</script>

{#if coin}
	<Card class="p-4 transition-all hover:shadow-lg sm:p-5 md:p-7">
		<div class="flex flex-col items-center pb-4">
			<Avatar size="md" src={coin.image} class="border border-solid border-zinc-300 p-px" />
			<h5 class="mb-1 text-xl font-medium text-gray-900 dark:text-white">{coin.name}</h5>
			<p class={`mt-2 mb-4 text-lg font-bold text-gray-700 dark:text-gray-200 ${statusClass}`}>
				{statusText()}
			</p>
			<div class="mt-2 mb-4 flex items-center justify-center gap-2">
				<p class="text-xs text-gray-400">${coin.current_price.toLocaleString()}</p>
				<p class="text-xs text-gray-400">|</p>
				<p class="text-xs text-gray-400">{coin.prediction_end}</p>
				<p class="text-xs text-gray-400">|</p>
				<p class="text-xs text-gray-400">
					Odds: {oddsPrimeDivision()}
				</p>
			</div>
			<div class="w-full">
				<Progressbar
					progress={yesPercentage}
					animate
					precision={0}
					tweenDuration={800}
					easing={sineOut}
					color="emerald"
					size="h-2.5"
					class="mb-3"
				/>
			</div>
			{#if outcome?.closed && winningAmount !== null}
				<p class="mt-6 text-sm font-medium text-emerald-600">
					Winning payout: ${winningAmount().toLocaleString()}
				</p>
			{/if}
			{#if !outcome?.closed}
				<div class="mt-2 flex gap-4">
					<Button
						class="cursor-pointer"
						outline
						color="green"
						size="md"
						onclick={() => emitVote('yes')}
					>
						Yes {yesPercentage}¢
					</Button>
					<Button
						class="cursor-pointer"
						outline
						color="red"
						size="md"
						onclick={() => emitVote('no')}
					>
						No {noPercentage}¢
					</Button>
				</div>
			{/if}
		</div>
	</Card>
{/if}
