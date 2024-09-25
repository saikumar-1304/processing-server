from flask import Flask, request, jsonify
from chatgpt import ChatGPT

app = Flask(__name__)

# Replace 'your_api_key_here' with your actual OpenAI API key
chatgpt_instance = ChatGPT(api_key='your_api_key_here')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    prompt = data.get('prompt')

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    response = chatgpt_instance.chat_with_gpt(prompt)
    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
