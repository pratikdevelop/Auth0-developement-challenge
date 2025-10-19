# Secure AI Chat Application - Auth0 for AI Agents Challenge

## Overview

A secure, authenticated AI chat application built for the Auth0 for AI Agents Challenge. This project demonstrates how to build AI agents with proper user authentication and authorization using Auth0, NVIDIA AI, and Flask.

**Key Features:**
- 🔐 Auth0 OAuth 2.0 authentication
- 🤖 NVIDIA AI integration (Meta Llama 3.2)
- 💬 Multi-chat conversations
- 👤 User-isolated chat history
- 🔄 Real-time streaming responses

## User Preferences

Preferred communication style: Simple, everyday language.

## Challenge Requirements Implementation

This application addresses all three security requirements from the Auth0 for AI Agents Challenge:

### 1. Authenticate the User
- All API endpoints protected with `@requires_auth` decorator
- Auth0 handles OAuth 2.0 flow (login, callback, logout)
- Session-based authentication with secure tokens
- No access to AI features without authentication

### 2. Control the Tools
- NVIDIA API key stored securely as environment variable
- Never exposed to frontend or client-side code
- Centralized API client configuration in backend
- Secure session management with Flask

### 3. Limit Knowledge
- User-specific chat isolation in database
- Each chat linked to Auth0 user ID (`sub`)
- Ownership checks on all CRUD operations
- Users can only access their own chats and messages
- 403 errors when attempting to access other users' data

## System Architecture

### Authentication & Authorization
- **Auth0 OAuth 2.0 Integration**: Complete authentication flow with login, callback, and logout
- **Session-based Authentication**: Flask session system with Auth0 userinfo tokens
- **User Isolation**: Database queries filtered by Auth0 user ID (sub claim)
- **Security Pattern**: `@requires_auth` decorator protects all sensitive endpoints

**Rationale**: Auth0 provides enterprise-grade authentication without custom auth implementation. User isolation ensures data privacy by design, preventing cross-user data access.

### Backend Architecture
- **Framework**: Flask (Python) with CORS support
- **API Structure**: RESTful endpoints under `/api/` prefix
  - `/api/auth/*`: Authentication endpoints (login, callback, logout, user)
  - `/api/chats`: Chat CRUD operations
  - `/api/chats/:id/messages`: Message operations
- **Streaming Responses**: Server-Sent Events for real-time AI responses
- **Modular Design**: 
  - `app.py`: Main application, routes, and AI integration
  - `auth.py`: Auth0 authentication logic and decorators
  - `database.py`: SQLite operations with user isolation

### Frontend Architecture
- **Technology Stack**: Vanilla JavaScript, HTML5, CSS3
- **Authentication Flow**: 
  - Check auth status on load
  - Show login screen if not authenticated
  - Redirect to Auth0 for login
  - Handle callback and establish session
- **UI Components**: Login screen, sidebar (chats list), main chat area
- **Security**: All API calls include credentials for session validation

### Data Storage
- **Database**: SQLite with user isolation
  - `chats`: (id, user_id, title, created_at)
  - `messages`: (id, chat_id, role, content, created_at)
- **Migration**: Automatic column addition for backward compatibility
- **Indexing**: user_id index for efficient queries
- **Isolation**: Every query filtered by authenticated user's ID

## External Dependencies

### Authentication Service
- **Auth0**: OAuth 2.0 authentication provider
  - Required: `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET`
  - Scopes: `openid profile email`
  - Library: `authlib` for OAuth client

### AI Service
- **NVIDIA API**: Meta Llama 3.2 3B Instruct
  - Base URL: `https://integrate.api.nvidia.com/v1`
  - Authentication: `NVIDIA_API_KEY` environment variable
  - Library: `openai` Python client (compatible)
  - Streaming: Token-by-token streaming responses

### Python Dependencies
- `flask`: Web framework
- `flask-cors`: Cross-origin resource sharing
- `authlib`: OAuth/OIDC client
- `openai`: AI model API client
- `requests`: HTTP library (authlib dependency)
- `python-dotenv`: Environment variable management

### Environment Variables Required
- `SECRET_KEY`: Flask session encryption (auto-generated if not set)
- `AUTH0_DOMAIN`: Your Auth0 tenant domain
- `AUTH0_CLIENT_ID`: Auth0 application client ID
- `AUTH0_CLIENT_SECRET`: Auth0 application client secret
- `NVIDIA_API_KEY`: NVIDIA API authentication key

## Security Implementation

### Authentication Security
- OAuth 2.0 standard flow via Auth0
- Secure session cookies with secret key
- HTTPS-only in production (Auth0 requirement)
- Proper CORS configuration with credentials

### Data Isolation Security
- User ID from Auth0 `sub` claim (unique identifier)
- All database queries scoped to authenticated user
- Ownership validation before any operation
- 401 Unauthorized for missing auth
- 403 Forbidden for unauthorized resource access

### API Key Security
- NVIDIA API key in environment variables only
- Never sent to frontend
- Never logged or exposed in errors
- Centralized client configuration

## Recent Changes

**October 19, 2025**: Added Auth0 authentication and user isolation
- Integrated Auth0 for OAuth 2.0 authentication
- Added user isolation to database schema
- Protected all API endpoints with authentication
- Created login/logout frontend flow
- Implemented secure session management
- Added ownership checks for all operations

## Setup Instructions

See README.md for detailed setup instructions including:
1. Creating Auth0 account and application
2. Configuring Auth0 settings
3. Setting up environment variables
4. Getting NVIDIA API key
5. Running the application

## Project Structure

```
├── app.py              # Main Flask app with Auth0 integration
├── auth.py             # Auth0 authentication logic
├── database.py         # SQLite operations with user isolation
├── static/
│   ├── index.html      # Frontend with login/chat UI
│   ├── style.css       # Styling
│   └── script.js       # Auth flow and chat logic
├── README.md           # Setup guide
└── replit.md           # This file
```

## Challenge Submission Notes

This project is ready for submission to the Auth0 for AI Agents Challenge.

**Deployment Requirements:**
- Set all environment variables in Replit Secrets
- Auth0 callback URLs configured for production domain
- NVIDIA API key active and valid

**Testing:**
- Create Auth0 account or use test credentials provided
- Login with Auth0
- Create chats and test AI responses
- Verify user isolation (different users see different chats)
