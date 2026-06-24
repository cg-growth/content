<script lang="ts">
	import { Button, Dropdown, DropdownDivider, DropdownItem } from 'flowbite-svelte';
	import { ChevronDownOutline } from 'flowbite-svelte-icons';
	import type { Sorter } from '$lib/Types/Sorters';

	interface Props {
		options: Sorter;
		name: string;
		selectedOption?: string | number;
	}

	let { name, options, selectedOption = $bindable() }: Props = $props();
	let optionName = $state();

	const handleClick = (value: { name: string; value: string | number }) => {
		if (value && selectedOption === value.value) {
			selectedOption = undefined;
		} else {
			selectedOption = value.value;
			optionName = value.name;
		}
	};
</script>

<Button color="alternative" class="min-w-20"
	>{optionName ?? name}<ChevronDownOutline class="ms-2 h-6" /></Button
>
<Dropdown class="w-40">
	{#each options as option}
		<DropdownItem on:click={() => handleClick(option)}>{option.name}</DropdownItem>
		<DropdownDivider />
	{/each}
</Dropdown>
