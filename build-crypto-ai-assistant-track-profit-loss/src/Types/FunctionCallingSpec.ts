import type {ChatCompletionTool} from "openai/resources/chat/completions";
import CoinGeckoService from "../Services/CoinGeckoService";

function createFunctionSpec(
    func: Function,
    description: string
): ChatCompletionTool {
    const functionName = func.name;

    const funcArgs = (func.toString().match(/\(([^)]*)\)/)?.[1] || "")
        .split(",")
        .map(arg => arg.trim())
        .filter(Boolean);

    const parameters = {
        type: "object",
        properties: funcArgs.reduce((acc, arg) => {
            acc[arg] = {
                type: "string",
                description: `The value of the argument '${arg}'`,
            };
            return acc;
        }, {} as Record<string, { type: string; description: string }>),
        required: funcArgs,
        additionalProperties: false,
    };

    return {
        type: "function",
        function: {
            name: functionName,
            description: description,
            parameters: parameters,
        },
    };
}

export const FunctionCallingSpec: ChatCompletionTool[] = [
    createFunctionSpec(
        CoinGeckoService.prototype.getCurrentPrice,
        "Get the latest price and price change for a cryptocurrency using the coin gecko API. Price change % will be returned in: \"usd_24h_change"
    ),
    createFunctionSpec(
        CoinGeckoService.prototype.getPnl,
        "Get the Price change in % for a cryptocurrency. Use to answer user requests surrounding pnl, or price change. Calling this function completely fulfills these requests."
    ),
];