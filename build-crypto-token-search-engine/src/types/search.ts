export type SearchCoin = {
	id: string;
	name: string;
	api_symbol: string;
	symbol: string;
	market_cap_rank: number | null;
	thumb: string;
	large: string;
};

export type SearchExchange = {
	id: string;
	name: string;
	market_type: string;
	thumb: string;
	large: string;
};

export type SearchCategory = {
	id: string;
	name: string;
};

export type SearchNFT = {
	id: string;
	name: string;
	symbol: string;
	thumb: string;
};

export type SearchResponse = {
	coins: SearchCoin[];
	exchanges: SearchExchange[];
	icos: unknown[];
	categories: SearchCategory[];
	nfts: SearchNFT[];
};
