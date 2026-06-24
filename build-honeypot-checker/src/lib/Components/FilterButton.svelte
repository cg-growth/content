<script lang="ts">
	import { Button } from 'flowbite-svelte';
	interface Props {
		isValue: boolean;
		label: string;
	}
	let { isValue = $bindable(), label }: Props = $props();

	const handleValue = () => {
		isValue = !isValue;
	};
</script>

<Button
	color={isValue ? 'primary' : 'alternative'}
	on:click={() => handleValue()}
	size="md"
	class="cursor-pointer py-[11px]">{label}</Button
>
