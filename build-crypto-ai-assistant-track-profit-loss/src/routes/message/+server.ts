import ChatGPTService from "../../Services/ChatGPTService";

const cgpt = new ChatGPTService();

export async function POST({request}) {
    const body = await request.json();
    console.log(body);
    const response = await cgpt.createChatCompletion({role: "user", content: body})
    return new Response(JSON.stringify(response), {
        headers: {
            'Content-Type': 'application/json',
        },
    });
}