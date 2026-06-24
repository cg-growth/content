<script lang="ts">
    import {Button, Input} from 'flowbite-svelte';
    import type {ChatCompletionMessageParam} from "openai/resources/chat/completions";
    import {marked} from "marked";

    let inputValue = "";
    let messages: ChatCompletionMessageParam[] | undefined;

    const handleClick = async () => {
        const response = await fetch('/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(inputValue),
        });

        messages = await response.json();
    };
</script>

<div class="bg-zinc-900 h-screen w-full flex items-center flex-col">
    <div class=" bottom-0 w-9/12 flex flex-col gap-6 items-center h-screen justify-end">
        {#if messages}
            <div class="custom-scrollbar bg-zinc-800 rounded-md shadow-md w-full p-6 text-white overflow-y-scroll max-h-10/12">
                {#each messages.filter(x => x.role !== "system") as message}
                    <p class="mb-2 text-amber-50">
                        <strong>{message.role}:</strong> {@html marked(message.content?.toString() ?? '')}
                    </p>
                {/each}
            </div>
        {/if}

        <div class="flex gap-2 m-6 w-full">
            <Input bind:value={inputValue}
                   id="large-input" placeholder="Message" size="lg"/>
            <Button color="alternative" on:click={handleClick}>Send</Button>
        </div>
    </div>
</div>

<style>
    .custom-scrollbar {
        scrollbar-width: thin;
        scrollbar-color: #292929 #1e1e1e;
    }

    .custom-scrollbar::-webkit-scrollbar {
        width: 5px;
    }

    .custom-scrollbar::-webkit-scrollbar-thumb {
        background: #292929;
        border-radius: 10px;
    }

    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
        background: #1e1e1e;
    }

    .custom-scrollbar::-webkit-scrollbar-track {
        background: #1e1e1e;
    }

    :global(code) {
        @apply bg-zinc-950 p-2 text-sm rounded-md font-mono;
    }

    :global(pre) {
        @apply bg-zinc-950 p-1

    }
</style>

