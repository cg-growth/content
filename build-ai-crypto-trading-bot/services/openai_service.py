from utils.load_env import openai_api_key
from openai import OpenAI


class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=openai_api_key)

    def get_chat_completion(self, data, instructions: str, model="gpt-5-mini"):
        response = self.client.responses.create(
            model=model, input=str(data), instructions=instructions
        )
        return response.output_text
