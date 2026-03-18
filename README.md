# Case Chat

Tax Law Case Analysis with AI Agents

## Quick Start

```bash
# Install dependencies
make install

# Run tests
make test

# Start AgentOS control plane
make test-agents
```

## Development

### Project Structure

```
case_chat/
├── src/case_chat/          # Source code
│   ├── agents/             # Agent definitions
│   ├── config.py           # Configuration
│   └── main.py             # FastAPI app
├── tests/                  # Tests
├── examples/               # Deployment examples
├── tmp/                    # Local database storage
├── pyproject.toml          # Project configuration
├── Makefile                # Development commands
└── .env.example            # Environment variables template
```

### Configuration

Copy `.env.example` to `.env` and configure your API key:

```bash
cp .env.example .env
# Edit .env and add your API key
```

### Makefile Commands

- `make install` - Install dependencies
- `make test` - Run tests
- `make lint` - Lint code
- `make format` - Format code
- `make clean` - Clean cache files
- `make test-agents` - Start AgentOS control plane

### AgentOS Control Plane

When you run `make test-agents`, the AgentOS control plane starts at:
- Control Plane: http://localhost:7777
- API Docs: http://localhost:7777/docs
- Health Check: http://localhost:7777/health
