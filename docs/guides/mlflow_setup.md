# MLflow Setup Guide for Case Chat

This guide provides comprehensive instructions for setting up MLflow tracing with Case Chat agents.

## Overview

MLflow tracing provides automatic observability for all agent interactions:
- **LLM Model Calls**: Requests, responses, latency, token usage
- **Tool/Function Calls**: Inputs, outputs, execution time, errors
- **RAG Operations**: Vector searches, retrieval, ranking
- **Document Uploads**: Parsing, chunking, embedding, storage
- **Agent Steps**: Reasoning traces, decisions, context management

## Prerequisites

- Python 3.11+ installed
- Case Chat project dependencies installed
- SQLite (included with Python)

## Installation

### 1. Install MLflow Dependencies

MLflow dependencies are included in the project `pyproject.toml`:

```bash
cd /path/to/case_chat
uv sync --all-extras --dev
```

Dependencies installed:
- `mlflow>=2.18.0` - Core MLflow library
- `opentelemetry-exporter-otlp>=1.27.0` - OpenTelemetry OTLP exporter
- `openinference-instrumentation-agno>=0.1.0` - Agno instrumentation

### 2. Start MLflow Server

Start a local MLflow server with SQLite backend:

```bash
mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlflow-artifacts \
  --port 5000
```

**Server Output:**
```
INFO:werkzeug:Press CTRL+C to quit
INFO:werkzeug:* Running on http://127.0.0.1:5000
```

**Server Endpoints:**
- MLflow UI: http://localhost:5000
- Health Check: http://localhost:5000/health
- API: http://localhost:5000/api/2.0/mlflow/experiments

### 3. Configure Environment Variables

Add MLflow configuration to your `.env` file:

```bash
# MLflow Tracing Configuration
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=case-chat-agent
```

**Configuration Options:**
- `MLFLOW_TRACKING_URI`: MLflow server endpoint (required)
  - Local: `http://localhost:5000`
  - Remote: `http://<mlflow-server>:5000`
- `MLFLOW_EXPERIMENT_NAME`: Experiment name for grouping runs (required)
  - Example: `case-chat-agent`, `case-chat-prod`, `case-chat-dev`

### 4. Verify MLflow Server

Check server health:

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{"status":"ok"}
```

## Usage

### Starting the Application

Start the Case Chat AgentOS deployment:

```bash
uv run python examples/case_chat_agentos_deploy.py
```

**Startup Logs:**
```
=== Case Chat AgentOS Deployment ===
[SETUP] SessionManager initialized: db_path=tmp/case_chat.db
[MLFLOW] Initializing MLflow tracing...
[MLFLOW] Server connectivity validated: http://localhost:5000
[MLFLOW] Tracking URI configured: http://localhost:5000
[MLFLOW] Experiment configured: case-chat-agent
[MLFLOW] Tracing initialized successfully
[MLFLOW] View traces: http://localhost:5000/#/experiments/
[MLFLOW] Tracing scope: model calls, tools, RAG operations, document uploads
[AGENT] Created Case Chat Agent
=== AgentOS Ready ===
```

### Interacting with Agents

1. Open AgentOS Control Plane: http://localhost:7777
2. Chat with the Case Chat agent
3. Perform operations: upload documents, ask questions, run RAG searches

### Viewing Traces

1. Open MLflow UI: http://localhost:5000
2. Navigate to **Experiments**
3. Select `case-chat-agent` experiment
4. Click on a run to view detailed traces

**Trace Information:**
- **Model Calls**: LLM requests/responses with token counts
- **Tool Calls**: Function invocations with inputs/outputs
- **RAG Operations**: Vector database queries and results
- **Document Uploads**: Parsing and embedding operations
- **Agent Steps**: Reasoning traces and decisions

## Troubleshooting

### Server Not Running

**Symptom:** Connection refused errors

**Solution:**
```bash
# Check if MLflow server is running
ps aux | grep mlflow

# Start server
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlflow-artifacts
```

### Incorrect URI Configuration

**Symptom:** Failed to initialize MLflow tracing

**Solution:**
- Verify `MLFLOW_TRACKING_URI` in `.env` file
- Ensure URI starts with `http://` or `https://`
- Test connectivity: `curl <MLFLOW_TRACKING_URI>/health`

### No Traces Appearing

**Symptom:** MLflow UI shows no runs or traces

**Solutions:**

1. **Check Application Logs:**
   ```bash
   # Look for [MLFLOW] tagged logs
   grep "[MLFLOW]" logs/application.log
   ```

2. **Verify Experiment Name:**
   - Ensure `MLFLOW_EXPERIMENT_NAME` matches in MLflow UI
   - Check experiment exists: http://localhost:5000/#/experiments/

3. **Test Agent Interaction:**
   - Perform a test query in AgentOS control plane
   - Check if new run appears in MLflow UI

### Permission Errors

**Symptom:** Cannot write to artifact directory

**Solution:**
```bash
# Create artifact directory with permissions
mkdir -p ./mlflow-artifacts
chmod 755 ./mlflow-artifacts
```

### Port Already in Use

**Symptom:** Address already in use error

**Solution:**
```bash
# Find process using port 5000
lsof -i :5000

# Kill process or use different port
mlflow server --port 5001
```

## Verification

### 1. Server Health Check

```bash
curl http://localhost:5000/health
```

Expected: `{"status":"ok"}`

### 2. Application Startup Check

```bash
uv run python examples/case_chat_agentos_deploy.py
```

Expected: `[MLFLOW] Tracing initialized successfully`

### 3. Trace Capture Check

1. Open MLflow UI: http://localhost:5000
2. Navigate to Experiments
3. Perform agent interaction
4. Verify new run appears with trace data

## Advanced Configuration

### Custom Backend Store

Use PostgreSQL instead of SQLite:

```bash
mlflow server \
  --backend-store-uri postgresql://user:password@localhost/mlflow \
  --default-artifact-root ./mlflow-artifacts
```

### Remote MLflow Server

Configure remote MLflow server:

```bash
# .env configuration
MLFLOW_TRACKING_URI=http://mlflow.example.com:5000
MLFLOW_EXPERIMENT_NAME=case-chat-agent
```

### Artifact Storage

Configure S3-compatible artifact storage:

```bash
mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root s3://mlflow-artifacts \
  --default-artifact-root s3://my-bucket/mlflow-artifacts
```

## Security Considerations

### Local Development

- MLflow server runs on localhost only (no public exposure)
- No authentication required for local POC environment
- Traces may contain sensitive data (filter PII before sharing)

### Production Deployment

For production deployments:
- Enable MLflow authentication: `mlflow server --app-name basic-auth`
- Use HTTPS for tracking URI
- Configure artifact storage with appropriate access controls
- Implement trace sampling for high-traffic scenarios
- Review and filter sensitive data from traces

## Additional Resources

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Agno Documentation](https://github.com/agno-ai/agno)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [Case Chat Project](https://github.com/casechat/case-chat)

## Support

For issues or questions:
1. Check application logs for `[MLFLOW]` tagged messages
2. Verify MLflow server health: `curl http://localhost:5000/health`
3. Review troubleshooting section above
4. Check MLflow UI for experiment and run visibility
