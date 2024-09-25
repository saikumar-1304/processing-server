import openai
import requests

class ChatGPT:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = 'https://api.openai.com/v1/chat/completions'

    def chat_with_gpt(self, prompt):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [{'role': 'user', 'content': prompt}],
        }

        response = requests.post(self.url, headers=headers, json=data)

        if response.status_code == 200:
            response_data = response.json()
            return response_data['choices'][0]['message']['content']
        else:
            return f"Error: {response.status_code}, {response.text}"
