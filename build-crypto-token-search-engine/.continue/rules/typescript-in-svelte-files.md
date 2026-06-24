---
name: SvelteKit TypeScript Tailwind Rules
alwaysApply: true
description: Enforce TypeScript and Tailwind for SvelteKit project
---

# SvelteKit Project Guidelines
- This is a SvelteKit project using TypeScript and Tailwind CSS.
- ALWAYS generate code in TypeScript syntax for `.ts` and `.svelte` files.
- Use SvelteKit conventions (e.g., `+page.svelte`, `+page.server.ts` for routes).
- For styling, use Tailwind CSS classes exclusively unless specified otherwise.
- Never suggest Python or other languages unless explicitly requested.
- Include JSDoc comments for TypeScript functions.
- Follow SvelteKit’s reactive syntax (e.g., `$:`, `bind:`) where appropriate.
- Ensure compatibility with Tailwind’s JIT compiler for dynamic classes.