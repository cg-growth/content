type PriceChange = Record<'m5' | 'm15' | 'm30' | 'h1' | 'h6' | 'h24', number>;

type TransactionData = {
	buys: number;
	sells: number;
	buyers: number;
	sellers: number;
};

type Transactions = Record<keyof PriceChange, TransactionData>;

type VolumeUSD = Record<keyof PriceChange, number>;

type TokenData = {
	id: string;
	type: string;
};

type Relationship = {
	data: TokenData;
};

type Relationships = {
	base_token: Relationship;
	quote_token: Relationship;
	network: Relationship & { data: { id: string; type: 'network' } };
	dex: Relationship & { data: { id: string; type: 'dex' } };
};

type Attributes = {
	base_token_price_usd: number;
	base_token_price_native_currency: number;
	quote_token_price_usd: number;
	quote_token_price_native_currency: number;
	base_token_price_quote_token: number;
	quote_token_price_base_token: number;
	address: string;
	name: string;
	pool_created_at: string;
	fdv_usd: number;
	market_cap_usd: number;
	price_change_percentage: PriceChange;
	transactions: Transactions;
	volume_usd: VolumeUSD;
	reserve_in_usd: number;
};

export type PoolData = {
	id: string;
	type: string;
	attributes: Attributes;
	relationships: Relationships;
};
