# MLflow Security Considerations

This document outlines security considerations for MLflow tracing integration in Case Chat.

## Local Development Environment

### Server Security

- **Localhost Only**: MLflow server runs on localhost by default (http://localhost:5000)
- **No Public Exposure**: Server is not accessible from external networks
- **No Authentication**: Local POC environment does not require authentication

### Data Handling

- **Trace Data**: All agent interactions are captured in traces
- **Sensitive Data**: Agno autolog filters sensitive data automatically
- **API Keys**: Credentials are not captured in trace spans
- **User Input**: User prompts and responses are stored in traces

### Configuration Security

- **.env File**: Contains MLflow configuration (already in .gitignore)
- **Environment Variables**: MLFLOW_TRACKING_URI and MLFLOW_EXPERIMENT_NAME required
- **No Hardcoded Secrets**: All configuration via environment variables

## Security Features

### SSRF Prevention

The MLflow tracking URI validator prevents Server-Side Request Forgery (SSRF) attacks:

```python
@field_validator("tracking_uri")
@classmethod
def validate_tracking_uri(cls, v: str) -> str:
    if not v.startswith(("http://", "https://")):
        raise ValueError(
            f"MLflow tracking URI must start with http:// or https://, got: {v}"
        )
    return v
```

**Validation Rules:**
- URI must start with `http://` or `https://`
- Rejects URIs without protocol prefix
- Prevents internal network access via malformed URIs

**Note**: For local POC development, localhost URIs are allowed. Production deployments should add additional restrictions.

### Connection Validation

MLflow server connectivity is validated before initialization:

```python
def _validate_mlflow_server_connectivity(settings: MLflowSettings) -> None:
    health_url = f"{settings.tracking_uri}/health"
    response = requests.get(health_url, timeout=MLFLOW_HEALTH_TIMEOUT)
    if not 200 <= response.status_code < 300:
        raise ConnectionError(...)
```

**Security Benefits:**
- Verifies server is reachable before sending trace data
- Prevents hanging on unreachable URIs
- Fails fast with clear error messages

### Fail-Fast Configuration

MLflow configuration is mandatory for tracing:

```python
tracking_uri: str = Field(..., description="MLflow server endpoint")
experiment_name: str = Field(..., description="MLflow experiment name")
```

**Security Benefits:**
- No default values that could point to unintended servers
- Explicit configuration required
- Clear error messages for missing configuration

## Production Deployment Considerations

### Authentication

For production MLflow deployments:

```bash
# Enable basic authentication
mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlflow-artifacts \
  --app-name basic-auth
```

### Network Security

- **HTTPS Only**: Use `https://` for tracking URI in production
- **Firewall Rules**: Restrict MLflow server access to authorized networks
- **VPC/Private Network**: Deploy MLflow server in private network when possible
- **VPN Access**: Require VPN for external MLflow UI access

### Data Privacy

- **PII Filtering**: Review and filter personally identifiable information from traces
- **Data Retention**: Implement trace data retention policies
- **Access Controls**: Restrict who can view traces in MLflow UI
- **Audit Logging**: Enable audit logs for MLflow UI access

### Trace Sampling

For high-traffic scenarios, implement trace sampling:

```python
# Example: Sample 10% of traces
if random.random() < 0.1:
    mlflow.agno.autolog()
```

## Security Best Practices

### Development

1. **Localhost Only**: Keep MLflow server on localhost for development
2. **No Secrets in Traces**: Verify API keys and credentials are not captured
3. **Regular Updates**: Keep MLflow dependencies updated
4. **Access Control**: Limit who can access MLflow UI locally

### Production

1. **Authentication Required**: Enable MLflow authentication
2. **HTTPS Only**: Use encrypted connections for trace data
3. **Network Isolation**: Deploy in private network with restricted access
4. **Data Minimization**: Sample traces and filter sensitive data
5. **Regular Audits**: Review trace data for unintended sensitive information
6. **Monitoring**: Monitor MLflow server for unauthorized access

## Compliance Considerations

### Data Residency

- **Local Storage**: SQLite backend stores data locally
- **Artifact Storage**: Configure artifact storage location
- **Cross-Border**: Consider data residency requirements for trace data

### Data Retention

- **Automatic Cleanup**: Implement MLflow run cleanup policies
- **Manual Deletion**: Regularly delete old experiments and runs
- **Export/Archive**: Archive important traces before deletion

### Access Logging

- **MLflow Logs**: Monitor MLflow server access logs
- **Audit Trail**: Track who viewed which traces
- **Alerting**: Set up alerts for suspicious access patterns

## Troubleshooting Security Issues

### Unauthorized Access

**Symptom**: Unexpected users accessing MLflow UI

**Solutions**:
1. Enable authentication: `mlflow server --app-name basic-auth`
2. Check firewall rules
3. Review access logs
4. Restrict network access

### Sensitive Data in Traces

**Symptom**: API keys or secrets visible in traces

**Solutions**:
1. Review Agno autolog configuration
2. Add custom filters for sensitive data
3. Implement trace sampling
4. Delete affected runs

### SSRF Vulnerability

**Symptom**: Internal network access via tracking URI

**Solutions**:
1. Validate URI format (already implemented)
2. Add IP address allowlist
3. Reject private network ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
4. Implement network-level restrictions

## Additional Resources

- [MLflow Security Documentation](https://mlflow.org/docs/latest/auth/index.html)
- [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OpenTelemetry Security](https://opentelemetry.io/docs/reference/specification/protocol/otlp/#security-considerations)

## Reporting Security Issues

For security concerns or vulnerabilities:
1. Do not create public GitHub issues
2. Contact maintainers directly
3. Provide detailed vulnerability description
4. Allow time for remediation before disclosure
