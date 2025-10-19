# Quick Setup Guide

Follow these steps to get your secure AI chat app running for the Auth0 for AI Agents Challenge!

## Step 1: Set Up Auth0 (Free Account)

1. Go to **[auth0.com](https://auth0.com)** and create a free account
2. After logging in, click **Applications** → **Create Application**
3. Name it **"Secure AI Chat"**
4. Choose **"Regular Web Applications"**
5. Click **Create**

## Step 2: Configure Auth0 Application

In your new Auth0 application's **Settings** tab, scroll down and configure:

### Find These Values (You'll Need Them):
- **Domain**: Look like `dev-abc123.us.auth0.com`
- **Client ID**: Long string of letters and numbers
- **Client Secret**: Another long string (click to reveal)

### Set These URLs:

**Allowed Callback URLs:**
```
https://your-replit-url.repl.co/api/auth/callback
```
(Replace `your-replit-url` with your actual Replit URL - you can find it in the webview)

**Allowed Logout URLs:**
```
https://your-replit-url.repl.co/
```

**Allowed Web Origins:**
```
https://your-replit-url.repl.co
```

Click **Save Changes** at the bottom!

## Step 3: Add Secrets in Replit

1. In Replit, look for **"Tools"** in the left sidebar
2. Click **"Secrets"**
3. Add these 5 secrets:

| Secret Name | Where to Get It |
|------------|----------------|
| `AUTH0_DOMAIN` | From Auth0 Settings (like `dev-abc123.us.auth0.com`) |
| `AUTH0_CLIENT_ID` | From Auth0 Settings |
| `AUTH0_CLIENT_SECRET` | From Auth0 Settings (click to reveal) |
| `NVIDIA_API_KEY` | The key you provided earlier: `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` |
| `SECRET_KEY` | Any random string (e.g., `my-super-secret-key-12345`) |

## Step 4: Test the App!

1. The app should automatically restart after adding secrets
2. Click the green **"Run"** button if needed
3. Open the webview
4. You should see a login screen
5. Click **"Login with Auth0"**
6. Create an account or login
7. Start chatting with the AI!

## Troubleshooting

**If login doesn't work:**
- Make sure all 5 secrets are added
- Check that the Auth0 callback URLs match your Replit URL exactly
- Try refreshing the page

**If you see "Authorization error":**
- Make sure the `NVIDIA_API_KEY` secret is set correctly

**If the app won't start:**
- Check the console logs for any error messages
- Make sure all environment variables are set

## Testing for the Challenge

To test that user isolation is working:
1. Login with one account
2. Create a chat and send a message
3. Logout
4. Login with a different account (or create a new one)
5. You should see NO chats - each user only sees their own!

## Next Steps for Challenge Submission

Once everything is working:
1. Test the authentication flow thoroughly
2. Create a few example chats to show functionality
3. Take screenshots of the working app
4. Write your submission post on DEV.to using the challenge template
5. Include setup instructions and explain how you implemented the 3 security requirements

Good luck with the challenge! 🚀
