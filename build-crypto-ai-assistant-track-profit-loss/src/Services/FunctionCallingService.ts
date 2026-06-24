import CoinGecko from "./CoinGeckoService";

class FunctionCallingService {
    coinGecko: CoinGecko;
    functionMap: { [K: string]: Function };

    constructor() {
        this.coinGecko = new CoinGecko();
        this.functionMap = {
            "getCurrentPrice": this.coinGecko.getCurrentPrice.bind(this.coinGecko),
            "getPnl": this.coinGecko.getPnl.bind(this.coinGecko),
        };
    }

    public async invokeFunction(name: string, args: string): Promise<any> {
        const func = this.functionMap[name];
        const parsedArgs = JSON.parse(args);
        if (func) {
            return func(...Object.values(parsedArgs));
        }
        throw new Error(`Method '${name}' not found in CoinGecko service.`);
    }
}

export default FunctionCallingService;
