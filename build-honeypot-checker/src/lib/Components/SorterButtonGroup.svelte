<script lang="ts">
	import { Button, ButtonGroup } from 'flowbite-svelte';
	import type { Sorter } from '$lib/Types/Sorters';

	interface Props {
		options: Sorter;
		selectedOption?: string | number;
	}

	let { options, selectedOption = $bindable() }: Props = $props();

	const handleClick = (value: string | number | undefined) => {
		if (value && selectedOption === value) {
			selectedOption = undefined;
		} else {
			selectedOption = value;
		}
	};
</script>

<ButtonGroup>
	{#each options as option}
		<Button
			class="min-w-20 cursor-pointer py-[11px]"
			size="md"
			on:click={() => handleClick(option.value)}>{option.name}</Button
		>
	{/each}
</ButtonGroup>
