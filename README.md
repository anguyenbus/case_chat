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
│   ├── observability/      # MLflow tracing integration
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

Copy `.env.example` to `.env` and configure your API keys:

```bash
cp .env.example .env
# Edit .env and add your API keys
```

Required environment variables:
- `z_api_key`: Zhipu AI API key (get from https://open.bigmodel.cn/usercenter/apikeys)
- `MLFLOW_TRACKING_URI`: MLflow server endpoint (e.g., http://localhost:5000)
- `MLFLOW_EXPERIMENT_NAME`: MLflow experiment name (e.g., case-chat-agent)

### MLflow Tracing Setup

MLflow tracing provides automatic observability for agent interactions, including model calls, tool calls, RAG operations, and document uploads.

#### Start MLflow Server

```bash
# Start MLflow server with SQLite backend
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlflow-artifacts

# Server starts at http://localhost:5000
# MLflow UI: http://localhost:5000
```

#### Configure .env File

Add MLflow configuration to your `.env` file:

```bash
# MLflow Tracing Configuration
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=case-chat-agent
```

#### View Traces

After starting the application and interacting with agents:

1. Open MLflow UI: http://localhost:5000
2. Navigate to Experiments
3. Select "case-chat-agent" experiment
4. View traces for each agent interaction

#### Screenshots

Chat View (document uploaded: Learning The Ropes:  An Introductory Tax Return Case - Kevin E.Flynn et al.):
![Chat View](https://maas-log-prod.cn-wlcb.ufileos.com/anthropic/e63a42fe-0e43-4350-acea-9039c6439044/a5d4fb043598301c9db4532ad9a3e26a.png?UCloudPublicKey=TOKEN_e15ba47a-d098-4fbd-9afc-a0dcf0e4e621&Expires=1773964373&Signature=NIy+pGj6CRSsqsYPd6lI/+ahPKM=)

MLflow Tracing Demo:
![MLflow Demo](artifacts/mlflow-demo-small.gif)

Watch the full demo video: [MLflow Demo on YouTube](https://youtu.be/-wBxcHSWs8k)

#### Troubleshooting

**Server not running**
```bash
# Check if MLflow server is running
curl http://localhost:5000/health

# Start server if needed
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlflow-artifacts
```

**Incorrect URI**
- Verify `MLFLOW_TRACKING_URI` matches server address
- Ensure URI starts with `http://` or `https://`
- Check server is accessible: `curl <MLFLOW_TRACKING_URI>/health`

**No traces appearing**
- Verify MLflow server is running
- Check application logs for `[MLFLOW]` tagged messages
- Ensure experiment name matches in MLflow UI

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

Startup logs include MLflow tracing status:
```
[MLFLOW] Initializing MLflow tracing...
[MLFLOW] Tracking URI: http://localhost:5000
[MLFLOW] Experiment: case-chat-agent
[MLFLOW] View traces: http://localhost:5000/#/experiments/
[MLFLOW] Tracing scope: model calls, tools, RAG operations, document uploads
```

## Documentation

For detailed MLflow setup instructions, see [docs/guides/mlflow_setup.md](docs/guides/mlflow_setup.md).
