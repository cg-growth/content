import OpenAI from "openai";
import {OPENAI_API_KEY, OPENAI_ORG_ID, OPENAI_PROJECT_ID} from "$env/static/private";
import type {ChatCompletionMessage, ChatCompletionMessageParam} from "openai/resources/chat/completions";
import {FunctionCallingSpec} from "../Types/FunctionCallingSpec";
import FunctionCallingService from "./FunctionCallingService";

class ChatGpt {
    chatHistory: ChatCompletionMessageParam[];
    functionCallingService: FunctionCallingService;
    private openai: OpenAI;

    constructor() {
        this.functionCallingService = new FunctionCallingService();
        this.openai = new OpenAI({
            apiKey: OPENAI_API_KEY,
            organization: OPENAI_ORG_ID,
            project: OPENAI_PROJECT_ID,
        });
        this.chatHistory = [{role: "system", content: "You are a helpful assistant."}];
    }

    async createChatCompletion(message: ChatCompletionMessageParam) {
        this.handleChatHistory(message);

        try {
            const response = await this.createCompletion();
            const message = response.choices[0].message;
            if (!this.isFunctionCall(message)) {
                this.handleChatHistory(message);
                return this.chatHistory
            }

            const instructions = this.functionDetails(message)
            console.log(instructions);
            if (!instructions) return;
            
            const functionResponse = await this.handleFunctionCall(instructions?.function.name, instructions?.function.arguments);
            console.log(functionResponse)

            this.handleChatHistory({role: "system", content: functionResponse});
            const functionFollowup = await this.createCompletion();
            console.log(functionFollowup.choices[0].message?.tool_calls?.[0].function);

            this.handleChatHistory(functionFollowup.choices[0].message)

            return this.chatHistory;
        } catch (error) {
            console.error("Error while creating chat completion:", error);
            return "An error occurred while processing your request.";
        }
    }

    async createCompletion() {
        const params = {
            model: "gpt-3.5-turbo",
            messages: this.chatHistory,
            tools: FunctionCallingSpec,
        }
        const response = await this.openai.chat.completions.create(params);
        return response
    }

    handleChatHistory(message: ChatCompletionMessageParam) {
        this.chatHistory.push(message);
    }

    isFunctionCall(message: ChatCompletionMessage): boolean {
        return message.tool_calls?.[0].type === "function";
    }

    functionDetails(message: ChatCompletionMessage) {
        if (!message.tool_calls?.[0].function) return undefined;
        return {call_id: message.tool_calls?.[0].id, function: message.tool_calls?.[0].function}
    }

    async handleFunctionCall(functionName: string, functionArguments: string): Promise<string> {
        return this.functionCallingService.invokeFunction(functionName, functionArguments);
    }
}

export default ChatGpt;
