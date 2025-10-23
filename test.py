import os
import json
import base64
from io import StringIO, BytesIO
from urllib.parse import quote_plus, urlencode
import tempfile
from datetime import datetime
import logging

from flask import Flask, request, jsonify, Response, stream_with_context, session, redirect, url_for
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from openai import OpenAI, OpenAIError
from werkzeug.utils import secure_filename
from tenacity import retry, stop_after_attempt, wait_fixed

# LangChain integrations (latest modular imports)
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_xai import ChatXAI
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print(os.getenv('NVIDIA_API_KEY'))
# PDF processing imports
try:
    from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
    from pdfminer.converter import TextConverter
    from pdfminer.layout import LAParams
    from pdfminer.pdfpage import PDFPage
    PDF_MINER_AVAILABLE = True
except ImportError:
    PDF_MINER_AVAILABLE = False
    logger.warning("pdfminer.six not available. PDF processing disabled.")

# PDF to image conversion imports
try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available. Vision processing disabled.")

CUSTOM_MODULES_AVAILABLE = False
# Custom modules
try:
    from database import Database
    from auth import init_auth, requires_auth, get_user
    CUSTOM_MODULES_AVAILABLE = True
except ImportError:
    
    logger.warning("Custom modules (database, auth) not available. Running in demo mode.")

# Configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CORS(app, supports_credentials=True, origins=["http://localhost:5000"])

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Demo mode database
if not CUSTOM_MODULES_AVAILABLE:
    class DemoDB:
        def __init__(self):
            self.chats = {}
            self.messages = {}
            self.next_chat_id = 1
            self.next_message_id = 1
        
        def get_all_chats(self, user_id):
            return [chat for chat in self.chats.values() if chat['user_id'] == user_id]
        
        def create_chat(self, user_id, title):
            chat_id = self.next_chat_id
            self.chats[chat_id] = {
                'id': chat_id,
                'user_id': user_id,
                'title': title,
                'created_at': datetime.now().isoformat()
            }
            self.messages[chat_id] = []
            self.next_chat_id += 1
            return chat_id
        
        def delete_chat(self, chat_id, user_id):
            if chat_id in self.chats and self.chats[chat_id]['user_id'] == user_id:
                del self.chats[chat_id]
                del self.messages[chat_id]
                return True
            return False
        
        def get_chat_messages(self, chat_id, user_id):
            if chat_id in self.chats and self.chats[chat_id]['user_id'] == user_id:
                return self.messages.get(chat_id, [])
            return []
        
        def add_message(self, chat_id, role, content, user_id):
            if chat_id in self.chats and self.chats[chat_id]['user_id'] == user_id:
                message_id = self.next_message_id
                message = {
                    'id': message_id,
                    'chat_id': chat_id,
                    'role': role,
                    'content': content,
                    'created_at': datetime.now().isoformat()
                }
                self.messages[chat_id].append(message)
                self.next_message_id += 1
                return message_id
            return None
    
    db = DemoDB()
    
    class DemoAuth:
        @staticmethod
        def requires_auth(f):
            return f
        
        @staticmethod
        def get_user():
            return {'sub': 'demo-user', 'name': 'Demo User', 'email': 'demo@example.com'}
    
    oauth = DemoAuth()
    requires_auth = oauth.requires_auth
    get_user = oauth.get_user
else:
    db = Database()
    oauth = init_auth(app)

# LangChain Clients Factory
def get_llm_client(model_name):
    if "nvidia" in model_name.lower() or "llama" in model_name.lower():
        return ChatNVIDIA(
            model=model_name,
            api_key=os.environ.get("NVIDIA_API_KEY"),
            temperature=0.7,
            top_p=0.9,
            max_tokens=1024,
        )
    elif "grok" in model_name.lower() or "xai" in model_name.lower():
        return ChatXAI(
            model=model_name,
            api_key=os.environ.get("XAI_API_KEY"),
            temperature=0.7,
            top_p=0.9,
            max_tokens=1024,
        )
    elif "deepseek" in model_name.lower():
        return ChatDeepSeek(
            model=model_name,
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            temperature=0.7,
            top_p=0.9,
            max_tokens=1024,
        )
    else:
        raise ValueError(f"Unsupported model: {model_name}")

# Raw OpenAI for vision
vision_client = OpenAI(
    base_url="https://api.nvcf.nvidia.com/v2/nvcf/",
    api_key=os.environ.get("NVIDIA_API_KEY")
)

# Grok-like system prompt
SYSTEM_PROMPT = """
You are Grok, created by xAI. Your role is to provide clear, accurate, and helpful answers to user questions. Use a friendly, conversational tone with a touch of wit. Adapt your response length and depth to the query: keep it concise for simple questions and provide detailed reasoning for complex ones. Use provided chat history or file content to inform your answers. If a file is uploaded, summarize or analyze its content to address the user's request. If you don't know the answer, admit it and suggest alternatives. Stay focused on the user's query and avoid irrelevant details.
"""

# Title generator (Runnable pipeline)
def get_title_chain(model_name):
    llm = get_llm_client(model_name)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize this message into a concise chat title (max 50 characters):"),
        ("human", "{input}")
    ])
    return prompt | llm | StrOutputParser()

def get_user_id():
    user = get_user()
    return user['sub'] if user and 'sub' in user else 'demo-user'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# File extraction functions
def extract_text_from_pdf(filepath):
    if not PDF_MINER_AVAILABLE:
        raise Exception("PDF processing requires pdfminer.six")
    try:
        rsrcmgr = PDFResourceManager()
        retstr = StringIO()
        laparams = LAParams()
        device = TextConverter(rsrcmgr, retstr, laparams=laparams)
        with open(filepath, 'rb') as fp:
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            for page in PDFPage.get_pages(fp):
                interpreter.process_page(page)
            text = retstr.getvalue()
        device.close()
        retstr.close()
        return text.strip()[:10000]  # Limit to 10k chars
    except Exception as e:
        logger.error(f"PDF processing error: {str(e)}")
        raise Exception(f"Failed to process PDF: {str(e)}")

def process_image_with_vision(file_content, filename):
    try:
        img_str = base64.b64encode(file_content).decode('utf-8')
        completion = vision_client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}},
                        {"type": "text", "text": "Extract text or describe the content of this image clearly and concisely."}
                    ]
                }
            ],
            temperature=0.2,
            top_p=0.1,
            max_tokens=1024
        )
        return completion.choices[0].message.content
    except OpenAIError as e:
        logger.error(f"Image processing error: {str(e)}")
        raise Exception(f"Failed to process image: {str(e)}")

def extract_text_with_vision_model(file_content, filename):
    if not PDF2IMAGE_AVAILABLE:
        raise Exception("Vision processing requires pdf2image")
    try:
        num_pages = len(list(PDFPage.get_pages(BytesIO(file_content))))
        images = convert_from_bytes(file_content, first_page=1, last_page=min(3, num_pages))
        if num_pages > 3:
            logger.warning(f"PDF has {num_pages} pages, processing only first 3.")
        extracted_texts = []
        for i, image in enumerate(images):
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            completion = vision_client.chat.completions.create(
                model="nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}},
                            {"type": "text", "text": "Extract all text from this document page. Return only the text."}
                        ]
                    }
                ],
                temperature=0.2,
                top_p=0.1,
                max_tokens=2048
            )
            extracted_texts.append(f"--- Page {i+1} ---\n{completion.choices[0].message.content}")
        return "\n\n".join(extracted_texts)
    except OpenAIError as e:
        logger.error(f"PDF vision processing error: {str(e)}")
        raise Exception(f"Failed to process PDF with vision model: {str(e)}")

def extract_text_from_file(file_content, filename, use_vision_model=False):
    file_extension = filename.rsplit('.', 1)[1].lower()
    if file_extension == 'txt':
        try:
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    return file_content.decode(encoding)[:10000]
                except UnicodeDecodeError:
                    continue
            raise Exception("Could not decode text file")
        except Exception as e:
            logger.error(f"Text file error: {str(e)}")
            raise Exception(f"Failed to process text file: {str(e)}")
    elif file_extension in ['png', 'jpg', 'jpeg']:
        return process_image_with_vision(file_content, filename)
    elif file_extension == 'pdf':
        if use_vision_model and PDF2IMAGE_AVAILABLE:
            try:
                return extract_text_with_vision_model(file_content, filename)
            except Exception as vision_error:
                logger.warning(f"Vision extraction failed: {vision_error}")
        if not PDF_MINER_AVAILABLE:
            raise Exception("PDF processing requires pdfminer.six")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        try:
            return extract_text_from_pdf(temp_path)
        finally:
            try:
                os.unlink(temp_path)
            except:
                logger.warning(f"Failed to delete temp file: {temp_path}")
    else:
        raise Exception(f"Unsupported file type: {file_extension}")

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def generate_llm_response(chat_id, user_id, messages, model_name):
    try:
        logger.debug(f"Sending LLM request with model: {model_name}, messages count: {len(messages)}")
        llm = get_llm_client(model_name)
        langchain_messages = [SystemMessage(content=SYSTEM_PROMPT)] + [
            HumanMessage(content=msg['content']) if msg['role'] == 'user' else SystemMessage(content=msg['content'])
            for msg in messages[-5:]
        ]
        full_response = ""
        if hasattr(llm, 'stream'):
            for chunk in llm.stream(langchain_messages):
                content = chunk.content if hasattr(chunk, 'content') else chunk
                if content:
                    full_response += content
                    yield f"data: {json.dumps({'content': content})}\n\n"
        else:
            response = llm.invoke(langchain_messages)
            content = response.content if hasattr(response, 'content') else response
            full_response += content
            yield f"data: {json.dumps({'content': content})}\n\n"
        logger.debug(f"Full LLM response: {full_response[:200]}...")  # Truncated log
        db.add_message(chat_id, 'assistant', full_response, user_id)
        yield f"data: {json.dumps({'done': True})}\n\n"
    except Exception as e:
        logger.error(f"LLM streaming error for {model_name}: {str(e)}")
        yield f"data: {json.dumps({'error': f'LLM error ({model_name}): {str(e)}'})}\n\n"

# Routes
@app.route('/')
def index():
    user = get_user()
    if not user:
        return redirect(url_for('landing_page'))
    return app.send_static_file('index.html')

@app.route('/landing_page')
def landing_page():
    return app.send_static_file('new_landing_page.html')

@app.route('/chat')
def chat():
    return app.send_static_file('index.html')

@app.route('/api/auth/user')
def auth_user():
    user = get_user()
    return jsonify({'authenticated': bool(user), 'user': user or {}})

@app.route('/api/auth/login')
def login():
    if not CUSTOM_MODULES_AVAILABLE:
        return jsonify({'error': 'Authentication not available in demo mode'}), 400
    redirect_uri = url_for('callback', _external=True)
    return oauth.auth0.authorize_redirect(redirect_uri)

@app.route('/api/auth/signup')
def signup():
    if not CUSTOM_MODULES_AVAILABLE:
        return jsonify({'error': 'Authentication not available in demo mode'}), 400
    redirect_uri = url_for('callback', _external=True)
    return oauth.auth0.authorize_redirect(redirect_uri, screen_hint='signup')

@app.route('/api/auth/callback')
def callback():
    if not CUSTOM_MODULES_AVAILABLE:
        return jsonify({'error': 'Authentication not available in demo mode'}), 400
    try:
        token = oauth.auth0.authorize_access_token()
        session['user'] = token['userinfo']
        return redirect('/chat')
    except Exception as e:
        logger.error(f"Auth callback error: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/auth/logout')
def logout():
    session.clear()
    if CUSTOM_MODULES_AVAILABLE:
        auth0_domain = os.environ.get('AUTH0_DOMAIN')
        return redirect(
            f'https://{auth0_domain}/v2/logout?' + 
            urlencode({
                'returnTo': url_for('index', _external=True),
                'client_id': os.environ.get('AUTH0_CLIENT_ID')
            }, quote_via=quote_plus)
        )
    return redirect(url_for('landing_page'))

@app.route('/api/chats', methods=['GET'])
@requires_auth
def get_chats():
    user_id = get_user_id()
    return jsonify(db.get_all_chats(user_id))

@app.route('/api/chats', methods=['POST'])
@requires_auth
def create_chat():
    user_id = get_user_id()
    data = request.get_json(silent=True) or {}
    title = data.get('title', 'New Chat')
    initial_message = data.get('initial_message')
    model_name = data.get('model', 'llama3-70b-instruct')  # From request
    if initial_message:
        try:
            title_gen = get_title_chain(model_name)
            title = title_gen.invoke({"input": initial_message})[:50]
        except Exception as e:
            logger.warning(f"Failed to generate chat title: {e}")
    chat_id = db.create_chat(user_id, title)
    return jsonify({'id': chat_id, 'title': title})

@app.route('/api/chats/<int:chat_id>', methods=['DELETE'])
@requires_auth
def delete_chat(chat_id):
    user_id = get_user_id()
    if db.delete_chat(chat_id, user_id):
        return jsonify({'success': True})
    return jsonify({'error': 'Chat not found or access denied'}), 403

@app.route('/api/chats/<int:chat_id>/messages', methods=['GET'])
@requires_auth
def get_messages(chat_id):
    user_id = get_user_id()
    return jsonify(db.get_chat_messages(chat_id, user_id))

@app.route('/api/chats/<int:chat_id>/messages', methods=['POST'])
@requires_auth
@limiter.limit("10 per minute")
def send_message(chat_id):
    user_id = get_user_id()
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    user_message = data.get('message')
    model_name = data.get('model', 'llama3-70b-instruct')  # From frontend dropdown
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    if not isinstance(user_message, str):
        return jsonify({'error': 'Message must be a string'}), 400
    if len(user_message) > 4000:
        return jsonify({'error': 'Message exceeds 4000 characters'}), 400
    message_id = db.add_message(chat_id, 'user', user_message, user_id)
    if not message_id:
        return jsonify({'error': 'Chat not found or access denied'}), 403
    chat_messages = db.get_chat_messages(chat_id, user_id)
    api_messages = [{'role': msg['role'], 'content': msg['content']} for msg in chat_messages]
    return Response(
        stream_with_context(generate_llm_response(chat_id, user_id, api_messages, model_name)),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
    )

@app.route('/api/chats/<int:chat_id>/upload', methods=['POST'])
@requires_auth
@limiter.limit("10 per minute")
def upload_file(chat_id):
    user_id = get_user_id()
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': f'Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    file_content = file.read()
    if len(file_content) > MAX_FILE_SIZE:
        return jsonify({'error': f'File too large (max {MAX_FILE_SIZE // (1024*1024)}MB)'}), 400
    secure_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    with open(secure_path, 'wb') as f:
        f.write(file_content)
    try:
        user_message = request.form.get('message', '').strip()
        use_vision_model = request.form.get('use_vision', 'false').lower() == 'true'
        model_name = request.form.get('model', 'llama3-70b-instruct')  # From form or default
        extracted_content = extract_text_from_file(file_content, file.filename, use_vision_model)
        if not extracted_content and not user_message:
            return jsonify({'error': 'No content extracted and no message provided'}), 400
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        combined_message = user_message or ""
        if extracted_content:
            if file_extension in ['png', 'jpg', 'jpeg']:
                combined_message += f"\n\nImage Analysis ({file.filename}): {extracted_content}"
            else:
                combined_message += f"\n\nDocument ({file.filename}): {extracted_content}"
        message_id = db.add_message(chat_id, 'user', combined_message, user_id)
        if not message_id:
            return jsonify({'error': 'Chat not found or access denied'}), 403
        chat_messages = db.get_chat_messages(chat_id, user_id)
        api_messages = [{'role': msg['role'], 'content': msg['content']} for msg in chat_messages]
        return Response(
            stream_with_context(generate_llm_response(chat_id, user_id, api_messages, model_name)),
            mimetype='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
        )
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    finally:
        if os.path.exists(secure_path):
            os.remove(secure_path)

@app.route('/api/models')
def get_models():
    return jsonify([
        {'id': 'llama3-70b-instruct', 'name': 'Llama 3 70B Instruct (NVIDIA)', 'description': 'Fast text model', 'type': 'text', 'provider': 'nvidia'},
        
        {'id': 'deepseek-coder', 'name': 'DeepSeek Coder', 'description': 'Code-focused model', 'type': 'text', 'provider': 'deepseek'},
        {'id': 'nvidia/llama-3.1-nemotron-nano-vl-8b-v1', 'name': 'Nemotron Vision 8B', 'description': 'Multimodal model', 'type': 'vision', 'provider': 'nvidia'}
    ])

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'mode': 'demo' if not CUSTOM_MODULES_AVAILABLE else 'production',
        'pdf_miner_available': PDF_MINER_AVAILABLE,
        'pdf2image_available': PDF2IMAGE_AVAILABLE,
        'langchain_providers': {
            'nvidia': bool(os.environ.get("NVIDIA_API_KEY")),
            'xai': bool(os.environ.get("XAI_API_KEY")),
            'deepseek': bool(os.environ.get("DEEPSEEK_API_KEY")),
        },
        'features': {
            'file_upload': True,
            'vision_processing': PDF2IMAGE_AVAILABLE,
            'streaming': True,
            'langchain': True,
            'authentication': CUSTOM_MODULES_AVAILABLE
        }
    })

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"404 error: {str(error)}")
    return jsonify({'error': 'Not Found', 'message': str(error)}), 404

@app.errorhandler(429)
def ratelimit_error(error):
    logger.warning("Rate limit exceeded")
    return jsonify({'error': 'Rate limit exceeded', 'message': 'Too many requests'}), 429

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {str(error)}")
    return jsonify({'error': 'Internal Server Error', 'message': str(error)}), 500

if __name__ == '__main__':
    logger.info("Starting AI Chat Application with LangChain Runnable API...")
    logger.info(f"Demo Mode: {not CUSTOM_MODULES_AVAILABLE}")
    logger.info(f"PDF Miner Available: {PDF_MINER_AVAILABLE}")
    logger.info(f"Vision Processing Available: {PDF2IMAGE_AVAILABLE}")
    app.run(host='0.0.0.0', port=5000, debug=True)