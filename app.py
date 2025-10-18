from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from openai import OpenAI
from database import Database
import json
import os

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

db = Database()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get('NVIDIA_API_KEY', '')
)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/chats', methods=['GET'])
def get_chats():
    chats = db.get_all_chats()
    return jsonify(chats)

@app.route('/api/chats', methods=['POST'])
def create_chat():
    data = request.json
    title = data.get('title', 'New Chat')
    chat_id = db.create_chat(title)
    return jsonify({'id': chat_id, 'title': title})

@app.route('/api/chats/<int:chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    db.delete_chat(chat_id)
    return jsonify({'success': True})

@app.route('/api/chats/<int:chat_id>/messages', methods=['GET'])
def get_messages(chat_id):
    messages = db.get_chat_messages(chat_id)
    return jsonify(messages)

@app.route('/api/chats/<int:chat_id>/messages', methods=['POST'])
def send_message(chat_id):
    data = request.json
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    db.add_message(chat_id, 'user', user_message)
    
    chat_messages = db.get_chat_messages(chat_id)
    api_messages = [{'role': msg['role'], 'content': msg['content']} for msg in chat_messages]
    
    def generate():
        try:
            completion = client.chat.completions.create(
                model="meta/llama-3.2-3b-instruct",
                messages=api_messages,
                temperature=0.2,
                top_p=0.7,
                max_tokens=1024,
                stream=True
            )
            
            full_response = ""
            for chunk in completion:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield f"data: {json.dumps({'content': content})}\n\n"
            
            db.add_message(chat_id, 'assistant', full_response)
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
