export const wallet = {
    getChain: () => ({
        id: 1,
        name: "Ethereum",
        rpcUrls: [],
        type: "radix" as const,
    }),
    getAccounts: () => [
        {
            address: "0x0",
            balance: {
                amount: "0",
                decimals: 18,
                symbol: "ETH",
                name: "Ether",
                value: "0",
                inBaseUnits: "0",
            },
        },
    ],
    signMessage: async () => ({ signature: "stub" }),
    getAddress: () => "0x0",
    balanceOf: async () => ({
        amount: "0",
        decimals: 18,
        symbol: "ETH",
        name: "Ether",
        value: "0",
        inBaseUnits: "0",
    }),
    getCoreTools: () => [],
};