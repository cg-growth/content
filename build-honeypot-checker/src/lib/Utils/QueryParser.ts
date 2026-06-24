import type { Filter } from '$lib/Types/Filter';

export function buildQueryString(filter: Filter): string {
	const queryParams = new URLSearchParams();

	Object.entries(filter).forEach(([key, value]) => {
		if (value !== undefined && value !== '') {
			queryParams.append(key, value.toString());
		}
	});
	return queryParams.toString();
}
