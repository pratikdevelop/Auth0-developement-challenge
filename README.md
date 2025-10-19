# Secure AI Chat - Auth0 for AI Agents Challenge

A secure, authenticated AI chat application built with Flask, Auth0, and NVIDIA AI models. This project demonstrates how to build secure AI agents that require user authentication before accessing AI capabilities.

## Features

- **🔐 Auth0 Authentication**: Secure user login and session management
- **🤖 NVIDIA AI Integration**: Powered by Meta's Llama 3.2 model via NVIDIA API
- **💬 Multi-Chat Support**: Create and manage multiple chat conversations
- **📝 Chat History**: All conversations are persisted in SQLite database
- **🔄 Real-time Streaming**: AI responses stream in real-time
- **👤 User-specific Chats**: Each user has their own isolated chat history

## Auth0 for AI Agents Implementation

This application addresses the three key security requirements from the Auth0 for AI Agents Challenge:

1. **Authenticate the User**: All API endpoints require Auth0 authentication before allowing access to the AI agent
2. **Control the Tools**: The NVIDIA API key is securely stored as an environment variable, never exposed to users
3. **Limit Knowledge**: User sessions are isolated - each user can only access their own chat history

## Tech Stack

- **Backend**: Flask (Python)
- **Authentication**: Auth0 (OAuth 2.0)
- **AI Model**: Meta Llama 3.2 via NVIDIA API
- **Database**: SQLite
- **Frontend**: Vanilla JavaScript, HTML5, CSS3

## Setup Instructions

### 1. Create an Auth0 Account

1. Go to [auth0.com](https://auth0.com) and create a free account
2. Create a new Application:
   - Go to Applications → Create Application
   - Choose "Regular Web Applications"
   - Name it "Secure AI Chat"

### 2. Configure Auth0 Application

In your Auth0 application settings:

**Allowed Callback URLs**:
```
https://your-replit-url.repl.co/api/auth/callback
```

**Allowed Logout URLs**:
```
https://your-replit-url.repl.co/
```

**Allowed Web Origins**:
```
https://your-replit-url.repl.co
```

### 3. Set Up Environment Variables

You need to add the following secrets in Replit:

1. **AUTH0_CLIENT_ID**: Your Auth0 Application Client ID
2. **AUTH0_CLIENT_SECRET**: Your Auth0 Application Client Secret  
3. **AUTH0_DOMAIN**: Your Auth0 Domain (e.g., `your-tenant.us.auth0.com`)
4. **NVIDIA_API_KEY**: Your NVIDIA API Key
5. **SECRET_KEY**: A random string for Flask session management (you can generate one)

To add secrets in Replit:
1. Click on "Tools" in the left sidebar
2. Select "Secrets"
3. Add each environment variable with its value

### 4. Get NVIDIA API Key

1. Go to [NVIDIA AI Playground](https://build.nvidia.com)
2. Sign up/Login
3. Generate an API key for Meta Llama 3.2 model

## Running the Application

Once all environment variables are set:

1. The app will automatically start
2. Click "Run" if needed
3. Open the web view
4. Click "Login with Auth0"
5. After logging in, you can create chats and talk to the AI

## Project Structure

```
├── app.py              # Main Flask application
├── auth.py             # Auth0 authentication logic
├── database.py         # SQLite database operations
├── static/
│   ├── index.html      # Frontend HTML
│   ├── style.css       # Styling
│   └── script.js       # Frontend JavaScript
└── README.md           # This file
```

## Security Features

- **Session-based Authentication**: Flask sessions secured with secret key
- **Protected API Endpoints**: All chat operations require authentication
- **Secure Token Storage**: Auth0 handles token management
- **Environment Variables**: Sensitive credentials never hardcoded
- **CORS Configuration**: Properly configured for secure cross-origin requests

## How It Works

1. User clicks "Login with Auth0"
2. Auth0 handles the authentication flow
3. User is redirected back with a secure session
4. Authenticated users can create chats and send messages
5. Messages are sent to NVIDIA AI API for responses
6. AI responses stream back in real-time
7. All chats and messages are saved to the database
8. Logout clears the session

## Testing Credentials

For judges testing this application:

- Create your own Auth0 account to test, or
- Contact me for test credentials

## Challenge Submission

This project is submitted for the **Auth0 for AI Agents Challenge** on DEV.to.

**Key Auth0 Integration Points**:
- User authentication before AI agent access
- Secure session management
- Protected API endpoints  
- Proper logout flow
- Environment-based configuration

## Future Enhancements

- User-specific chat history (currently global)
- Role-based access control
- Token scopes for fine-grained permissions
- Multi-factor authentication
- Chat sharing between users

## License

MIT License

## Author

Built with ❤️ for the Auth0 for AI Agents Challenge
