# Case Chat - Local Web UI

A simple, fully local web interface for interacting with your Case Chat agents.

## How to Use

### Step 1: Start the Backend

Open a terminal and start the AgentOS backend:

```bash
make test-agents
```

The backend will run on **http://localhost:7777**

### Step 2: Open the Local Web UI

**Option A: Open directly in browser** (Recommended)
```bash
make serve-ui
```
This will open `frontend/index.html` in your default browser.

**Option B: Serve via HTTP server**
```bash
make serve-ui-http
```
Then visit **http://localhost:8080** in your browser.

## Features

- ✅ **Fully Local** - No cloud dependencies, no data leaves your machine
- ✅ **Real-time Chat** - Interactive chat interface with the agent
- ✅ **Connection Status** - Shows whether backend is connected
- ✅ **Markdown Support** - Basic markdown rendering for agent responses
- ✅ **Session Persistence** - Maintains conversation context

## How It Works

```
┌─────────────────────────────────────────┐
│  Browser (frontend/index.html)          │
│  - HTML/CSS/JavaScript                  │
│  - Runs entirely in your browser       │
└──────────────┬──────────────────────────┘
               │
               │ Fetch API calls
               ▼
┌─────────────────────────────────────────┐
│  Local Backend (localhost:7777)         │
│  - Agent logic                          │
│  - GLM-5 model                          │
│  - SQLite database                      │
└─────────────────────────────────────────┘
```

**Everything happens on your machine!**

## Troubleshooting

### Shows "Disconnected" status

- Make sure the backend is running: `make test-agents`
- Check that port 7777 is not already in use
- Verify the backend started successfully

### Agent not responding

- Check the backend terminal for error messages
- Verify your `.env` file has a valid API key
- Try refreshing the page

### Connection errors

- Make sure you're accessing the page via HTTP, not HTTPS
- Check that your browser allows cross-origin requests to localhost
- Try using the HTTP server option: `make serve-ui-http`

## Architecture

The local UI is built with:
- **Vanilla HTML/CSS/JavaScript** - No frameworks required
- **Fetch API** - For communicating with the AgentOS backend
- **Responsive Design** - Works on desktop and mobile

## Customization

You can modify `frontend/index.html` to:
- Change the color scheme
- Add more features (e.g., export chat history)
- Customize the agent instructions
- Add multiple agents support

The UI calls the AgentOS API at:
- `POST /v1/agents/case-chat-assistant/chat` - Send message to agent
- `GET /health` - Check backend connection status

## Security Note

This local UI is designed for development and testing. It communicates with a local backend only and does not implement:
- Authentication
- Authorization
- Input sanitization (beyond basic HTML escaping)
- CSRF protection

For production use, consider implementing proper security measures.
