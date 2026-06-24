from dataclasses import dataclass
from dataclass_wizard import JSONWizard
from typing import Dict, Optional, List


@dataclass
class TransactionPeriod:
    buys: int
    sells: int
    buyers: int
    sellers: int


@dataclass
class PriceChangePercentage:
    m5: str
    m15: str
    m30: str
    h1: str
    h6: str
    h24: str


@dataclass
class VolumeUsd:
    m5: str
    m15: str
    m30: str
    h1: str
    h6: str
    h24: str


@dataclass
class RelationshipData:
    id: str
    type: str


@dataclass
class Relationship:
    data: RelationshipData


@dataclass
class Relationships:
    base_token: Relationship
    quote_token: Relationship
    dex: Relationship


@dataclass
class Attributes:
    base_token_price_usd: str
    base_token_price_native_currency: str
    quote_token_price_usd: str
    quote_token_price_native_currency: str
    base_token_price_quote_token: str
    quote_token_price_base_token: str
    address: str
    name: str
    pool_created_at: str
    fdv_usd: Optional[str]
    market_cap_usd: Optional[str]
    price_change_percentage: PriceChangePercentage
    transactions: Dict[str, TransactionPeriod]
    volume_usd: VolumeUsd
    reserve_in_usd: Optional[str]


@dataclass
class Pool:
    id: str
    type: str
    attributes: Attributes
    relationships: Relationships


@dataclass
class Pools(JSONWizard):
    data: List[Pool]
