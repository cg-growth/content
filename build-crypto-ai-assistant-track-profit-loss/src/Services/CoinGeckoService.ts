import axios, {type AxiosRequestConfig} from "axios";
import {CG_API_KEY} from '$env/static/private'

class CoinGecko {
    private root: string;
    private headers: Record<string, string>;

    constructor() {
        this.root = "https://pro-api.coingecko.com/api/v3";
        this.headers = {
            accept: "application/json",
            "x-cg-pro-api-key": CG_API_KEY,
        };
    }

    async getCurrentPrice(name: string): Promise<string> {
        const additionalParams = '&include_market_cap=true&include_24hr_vol=true&include_24hr_change=true&include_last_updated_at=true'
        const requestUrl = `${this.root}/simple/price?ids=${name.toLowerCase()}&vs_currencies=usd${additionalParams}`;
        const config: AxiosRequestConfig = {
            headers: this.headers,
        };
        const response = await axios.get(requestUrl, config);

        // @ts-ignore
        return JSON.stringify(response.data);
    }

    async getPnl(name: string): Promise<string> {
        const additionalParams = '&include_market_cap=true&include_24hr_vol=true&include_24hr_change=true&include_last_updated_at=true'
        const requestUrl = `${this.root}/simple/price?ids=${name.toLowerCase()}&vs_currencies=usd${additionalParams}`;
        const config: AxiosRequestConfig = {
            headers: this.headers,
        };
        const response = await axios.get(requestUrl, config);
        const innerObject = Object.values(response.data)[0];

        // @ts-ignore
        return JSON.stringify({price_change_percentage: innerObject.usd_24h_change});
    }

}

export default CoinGecko;
