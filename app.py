from flask import Flask, request, jsonify, Response, stream_with_context, session, redirect, url_for
from flask_cors import CORS
from openai import OpenAI
from database import Database
from auth import init_auth, requires_auth, get_user
import json
import os
from urllib.parse import quote_plus, urlencode

app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

CORS(app, supports_credentials=True)

db = Database()
oauth = init_auth(app)

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get('NVIDIA_API_KEY', '')
)

def get_user_id():
    user = get_user()
    if user and 'sub' in user:
        return user['sub']
    return None

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/auth/user')
def auth_user():
    user = get_user()
    if user:
        return jsonify({'authenticated': True, 'user': user})
    return jsonify({'authenticated': False})

@app.route('/api/auth/login')
def login():
    redirect_uri = url_for('callback', _external=True)
    return oauth.auth0.authorize_redirect(redirect_uri)

@app.route('/api/auth/callback')
def callback():
    try:
        token = oauth.auth0.authorize_access_token()
        session['user'] = token['userinfo']
        return redirect('/')
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/auth/logout')
def logout():
    session.clear()
    auth0_domain = os.environ.get('AUTH0_DOMAIN')
    return redirect(
        f'https://{auth0_domain}/v2/logout?' + 
        urlencode({
            'returnTo': url_for('index', _external=True),
            'client_id': os.environ.get('AUTH0_CLIENT_ID')
        }, quote_via=quote_plus)
    )

@app.route('/api/chats', methods=['GET'])
@requires_auth
def get_chats():
    user_id = get_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    chats = db.get_all_chats(user_id)
    return jsonify(chats)

@app.route('/api/chats', methods=['POST'])
@requires_auth
def create_chat():
    user_id = get_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    data = request.json
    title = data.get('title', 'New Chat')
    chat_id = db.create_chat(user_id, title)
    return jsonify({'id': chat_id, 'title': title})

@app.route('/api/chats/<int:chat_id>', methods=['DELETE'])
@requires_auth
def delete_chat(chat_id):
    user_id = get_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    success = db.delete_chat(chat_id, user_id)
    if not success:
        return jsonify({'error': 'Chat not found or access denied'}), 403
    return jsonify({'success': True})

@app.route('/api/chats/<int:chat_id>/messages', methods=['GET'])
@requires_auth
def get_messages(chat_id):
    user_id = get_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    messages = db.get_chat_messages(chat_id, user_id)
    return jsonify(messages)

@app.route('/api/chats/<int:chat_id>/messages', methods=['POST'])
@requires_auth
def send_message(chat_id):
    user_id = get_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    data = request.json
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    message_id = db.add_message(chat_id, 'user', user_message, user_id)
    if not message_id:
        return jsonify({'error': 'Chat not found or access denied'}), 403
    
    chat_messages = db.get_chat_messages(chat_id, user_id)
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
            
            db.add_message(chat_id, 'assistant', full_response, user_id)
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
