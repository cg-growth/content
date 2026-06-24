<script lang="ts">
	import { Card, Avatar, Progressbar, Button } from 'flowbite-svelte';
	import { BadgeCheckSolid, ExclamationCircleSolid } from 'flowbite-svelte-icons';
	export let token: {
		address: string;
		price: number;
		image: string;
		name: string;
		symbol: string;
		safe: boolean;
	};

	// Dummy odds data for progress bar and buttons
	let yesPercentage = 60;
	let noPercentage = 40;
</script>

<Card class="p-4 transition-all hover:shadow-lg sm:p-5 md:p-7">
	<div class="flex flex-col items-center pb-4">
		<Avatar size="md" src={token.image} class="border border-solid border-zinc-300 p-px" />
		<div class="mb-1 flex items-center gap-2">
			<h5 class="text-xl font-medium text-gray-900 dark:text-white">{token.name}</h5>
			{#if token.safe}
				<BadgeCheckSolid class="h-6 w-6 shrink-0 text-green-500 " />
			{:else}
				<ExclamationCircleSolid class="h-6 w-6 shrink-0 text-red-400" />
			{/if}
		</div>
		<p class="mt-2 mb-4 text-lg font-bold text-gray-700 dark:text-gray-200">{token.symbol}</p>
		<div class="mt-2 mb-4 flex items-center justify-center gap-2">
			<p class="text-xs text-gray-400">${token.price}</p>
		</div>
		<p class="pb-6 text-xs text-gray-400">{token.address}</p>

		<div class="w-full">
			<Progressbar
				progress={yesPercentage}
				animate
				precision={0}
				tweenDuration={800}
				easing={(x) => x}
				color="emerald"
				size="h-2.5"
				class="mb-3"
			/>
		</div>
		<div class="mt-2 flex gap-4">
			<Button class="cursor-pointer" outline color="green" size="md">
				Yes {yesPercentage}¢
			</Button>
			<Button class="cursor-pointer" outline color="red" size="md">
				No {noPercentage}¢
			</Button>
		</div>
	</div>
</Card>
