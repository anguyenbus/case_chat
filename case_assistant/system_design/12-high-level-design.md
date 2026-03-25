# High-Level AWS Design

## Table of Contents

- [1. Overview](#1-overview)
- [2. AWS Services by Layer](#2-aws-services-by-layer)
- [3. Service Selection Rationale](#3-service-selection-rationale)
- [4. Integration Patterns](#4-integration-patterns)
- [5. Cost Optimization Considerations](#5-cost-optimization-considerations)
- [6. Security Architecture](#6-security-architecture)
- [7. Related Documents](#7-related-documents)

---

## 1. Overview

The Case Assistant Chat system is deployed on AWS using a serverless-first architecture with containerized workloads for intensive processing. The design prioritizes **cost efficiency**, **scalability**, and **security** while supporting a sophisticated 6-index Retrieval-Augmented Generation (RAG) system for Australian tax law queries.

### Key Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Serverless-first** | Lambda for orchestrators, API Gateway for APIs, S3 for storage |
| **Kubernetes for workloads** | EKS for VLM+GPU processing, ingestion pipeline, stateful services |
| **Managed services** | OpenSearch Serverless, DynamoDB, Neptune to reduce operational overhead |
| **Event-driven scaling** | KEDA for Kubernetes pod autoscaling based on queue depth |
| **Security-first** | VPC isolation, WAF, IRSA for pod identity |
| **GitOps deployment** | ArgoCD for continuous delivery to EKS clusters |

---

## 2. AWS Services by Layer

### 2.1 Networking Layer

#### Amazon VPC (Virtual Private Cloud)
- **Purpose**: Network isolation for compute resources
- **Configuration**: Private subnets only, no public subnets for application workloads
- **Components**: ALB, EKS cluster, Lambda in private subnets
- **Connectivity**: VPC Link for API Gateway → ALB, PrivateLink for AWS services (phase 2+)

#### Application Load Balancer (ALB)
- **Purpose**: Internal traffic routing to Kubernetes services
- **Features**:
  - Path-based routing (/api/*, /ingest, /health)
  - Health checks for EKS pods
  - WebSocket support for real-time chat streaming
  - Sticky sessions for conversation continuity
- **Placement**: Internal VPC, behind API Gateway, accessed via VPC Link
- **Integration**: Ingress controller (AWS Load Balancer Controller) managing ALB via Ingress resources

#### VPC Link
- **Purpose**: Private connection from API Gateway to ALB
- **Type**: Regional VPC Link (NLB/ALB integration)
- **Benefit**: No internet gateway exposure for internal traffic

#### AWS PrivateLink (VPC Endpoints) - Phase 2+
- **Purpose**: Private connectivity to AWS services without internet gateway
- **Phase 1**: Use public endpoints (TLS-encrypted), pods in VPC use NAT Gateway or direct internet access
- **Phase 2**: Add PrivateLink when traffic exceeds 100 GB/month or compliance requires it
- **Endpoints** (when added):
  - S3 (gateway endpoint) - highest priority for document storage
  - DynamoDB (gateway endpoint) - citation and metadata indices
  - Bedrock (interface endpoint) - if compliance requires private ML access
  - OpenSearch Serverless (interface endpoint) - optional
- **Cost**: ~$7/month per gateway endpoint, ~$7/month per interface endpoint
- **ROI**: Cost-effective when exceeding NAT Gateway costs (~$32/month)

---

### 2.2 Security Layer

#### Azure Active Directory (Entra ID)
- **Purpose**: Identity and Access Management (IdP)
- **Protocol**: OAuth 2.0 / OIDC
- **Integration**: JWT tokens validated by API Gateway authorizer
- **User Store**: Managed externally, not in AWS

#### AWS WAF (Web Application Firewall)
- **Purpose**: Web exploit protection at edge
- **Attached to**: API Gateway
- **Rules**:
  - Rate limiting (100 req/min per IP)
  - Geo-blocking (Australia only)
  - Size restrictions (50MB upload max)
  - SQL injection, XSS protection (AWSManagedRulesCommonRuleSet)
  - Bot control
- **Cost**: ~$15-20/month

#### API Gateway JWT Authorizer
- **Purpose**: Token validation after WAF, before application logic
- **Validates**: Azure AD JWT signatures and claims
- **Performance**: Token caching to reduce validation overhead

---

### 2.3 Application Interface Layer

#### Amazon API Gateway
- **Purpose**: Public API entry point for all REST and WebSocket traffic
- **Features**:
  - REST API for document upload (/upload)
  - WebSocket API for chat streaming (/chat)
  - JWT authorizer integration
  - Request/response validation
  - Usage plans and throttling
- **Endpoints**:
  - `POST /api/documents/upload` - Document upload
  - `POST /api/chat/query` - Chat query
  - `WS /api/chat/stream` - WebSocket for streaming responses
- **Integration**: VPC Link to ALB for internal routing

---

### 2.4 Compute Layer

#### AWS Lambda (Orchestrators)
- **Purpose**: Event-driven orchestration and lightweight processing
- **Functions**:
  - `ingestion-trigger` - S3 PUT event handler, submits jobs to EKS
  - `session-cleanup` - Scheduled Lambda for TTL expiration
  - `adhoc-tasks` - Administrative and operational scripts
- **Runtime**: Python 3.11 with uv package manager
- **Memory**: 1-2 GB configs based on workload
- **Timeout**: Up to 15 minutes for ingestion orchestrator
- **Placement**: Outside VPC for phase 1 (simpler, faster cold starts)
- **Benefits**: Pay-per-invocation, auto-scaling, no idle costs

#### Amazon EKS (Elastic Kubernetes Service) - Primary Compute
- **Purpose**: Container orchestration for all application services
- **Version**: Kubernetes 1.28+ (managed by AWS)
- **Compute Options**:
  - **Fargate**: Serverless pods, pay-per-pod-hour, no node management
  - **Managed Node Groups**: EC2 instances for cost optimization at scale
- **Services Deployed**:
  - `chat-engine` - Conversation management, WebSocket handling
  - `ingestion-service` - Page processing, chunking, VLM routing
  - `query-orchestrator` - RAG retrieval coordination, 6-index querying
  - `session-manager` - Session state management
  - `api-gateway-helper` - JWT validation, rate limiting (pre-auth)
- **Pod Sizing**:
  - Chat Engine: 0.5-1 vCPU, 1-2 GB RAM (horizontal pod autoscaling)
  - Ingestion Service: 2-4 vCPU, 4-8 GB RAM (KEDA scaling based on SQS)
  - Query Orchestrator: 1-2 vCPU, 2-4 GB RAM (HPA based on CPU/memory)
  - Session Manager: 0.5 vCPU, 1 GB RAM (minimal footprint)
- **Scaling**:
  - **Horizontal Pod Autoscaler (HPA)**: Scale based on CPU/memory metrics
  - **KEDA (Kubernetes Event-driven Autoscaling)**: Scale based on SQS queue depth, Kafka lag, or other external metrics
  - **Karpenter**: Node autoscaling - right-size nodes automatically, provision Spot instances, consolidate nodes for efficiency
- **Ingress**: AWS Load Balancer Controller managing ALB via Ingress resources
- **Benefits**:
  - Kubernetes ecosystem and tooling
  - Declarative configuration via GitOps (ArgoCD)
  - Advanced networking (Istio service mesh, optional)
  - Pod-level resource isolation and limits
  - Mature observability (Prometheus, Grafana, OpenTelemetry)

#### IRSA (IAM Roles for Service Accounts)
- **Purpose**: Pod-level IAM permissions (no shared node credentials)
- **Usage**: Each service gets its own IAM role via service account annotation
- **Example**: `ingestion-service` pods assume role with S3, Textract, Bedrock permissions
- **Benefits**: Least privilege, auditability, no credential management in pods

---

### 2.5 Storage Layer

#### Amazon S3 (Simple Storage Service)
- **Purpose**: Raw document storage and ML artifacts
- **Buckets**:
  - `case-assistant-docs-raw` - Uploaded PDFs, DOCX files
  - `case-assistant-docs-processed` - Extracted text, chunks
  - `case-assistant-mlflow` - MLflow artifacts, model registry
  - `case-assistant-logs` - Application logs (if CloudWatch Logs insufficient)
- **Features**:
  - S3 Versioning for document history
  - S3 Event Notifications to trigger Lambda → SQS → EKS scaler
  - S3 Lifecycle policies for tiering to Glacier
- **Access**: Public endpoint (TLS) in phase 1, PrivateLink gateway endpoint in phase 2

---

### 2.6 Database & Search Layer

#### Amazon OpenSearch Serverless
- **Purpose**: Vector search and keyword search for RAG
- **Indices** (3 collections):
  - **Semantic Index**: Child chunks (300-500 tokens) with Titan embeddings
  - **Keyword Index**: BM25 index for tax-specific terms
  - **Context Index**: Parent chunks (1500-2500 tokens) for full context
- **Embedding Model**: Amazon Titan Embeddings v2 (1536 dimensions, 8192 token context)
- **Search Type**: Vector search (k-NN) + BM25 (keyword) hybrid
- **Capacity**: Pay-per-search, no provisioning needed
- **Access**: Public endpoint (TLS) in phase 1, VPC interface endpoint in phase 2

#### Amazon DynamoDB
- **Purpose**: NoSQL database for exact-match lookups
- **Tables**:
  - `legal-citation-index` - Section numbers, case citations (PK: citation)
  - `document-metadata` - Document attributes (PK: document_id)
  - `session-store` - Conversation history (PK: session_id, SK: timestamp)
  - `ingestion-status` - Document processing status (PK: document_id)
- **Capacity Mode**: On-demand (pay-per-request)
- **Features**:
  - Global Tables for multi-region (future)
  - TTL for automatic expiration (7-day inactivity)
  - PartiQL for SQL-like queries
- **Access**: Public endpoint (TLS) in phase 1, VPC gateway endpoint in phase 2

#### Amazon Neptune
- **Purpose**: Graph database for citation cross-references
- **Graph Model**:
  - Nodes: Citations (sections, cases, rulings), definitions, examples
  - Edges: `references`, `defines`, `cites`, `contradicts`
  - Traversals: Expand related citations during retrieval
- **Edition**: Neptune Serverless (pay-per-query)
- **Access**: Public endpoint (TLS) in phase 1, VPC interface endpoint in phase 2
- **Use Case**: Cross-reference expansion in retrieval step 8

---

### 2.7 Machine Learning Layer

#### Amazon Bedrock
- **Purpose**: Generative AI and embeddings
- **Models Used**:
  - **Claude Sonnet 4.6** - Response generation (high quality)
  - **Claude Haiku 4.5** - Reranking (fast, cost-efficient)
  - **Titan Embeddings v2** - 1536-dim vectors for OpenSearch
  - **Multimodal models** - Table extraction via VLM
- **Features**:
  - Serverless inference (no provisioning)
  - On-demand throughput
  - Guardrails for content filtering (optional)
- **Pricing**: Pay-per-token/input-output
- **Access**: Public endpoint (TLS) in phase 1, VPC interface endpoint in phase 2 if compliance requires

#### AWS Textract
- **Purpose**: OCR and document text extraction
- **Usage**: Text-only pages in document ingestion
- **Features**:
  - Document text extraction (PDF, images)
  - Form data extraction
  - Table detection (basic)
  - Async operations for large documents
- **Cost**: $1.50 per 1,000 pages (approx)
- **Alternative**: PyMuPDF for cost savings on simple PDFs

#### VLM + GPU (External Service)
- **Purpose**: Complex table extraction with structure preservation
- **Options**:
  - **LlamaParse** - Vision model for tables
  - **Bedrock Multimodal (Claude)** - Image-based table extraction
- **GPU**: Required for image processing of table pages
- **Routing**: Page-level detection before VLM processing
- **Cost**: ~60-70% cost savings vs. processing all pages with VLM

---

### 2.8 Integration & Events Layer

#### Amazon EventBridge
- **Purpose**: Event-driven architecture
- **Rules**:
  - S3 PUT event → Lambda ingestion orchestrator
  - Document status change → WebSocket notification
  - TTL expiration → Session cleanup Lambda
- **Benefits**: Decoupled services, async processing

#### Amazon SNS (Simple Notification Service)
- **Purpose**: Pub/sub messaging for notifications
- **Topics**:
  - `document-processing-complete` - Notify user on ready status
  - `system-alerts` - Operational alerts to DevOps
- **Subscribers**: WebSocket service, email alerts

---

### 2.9 Monitoring & Observability Layer

#### Amazon CloudWatch
- **Purpose**: Metrics, logs, and alarms
- **Components**:
  - **CloudWatch Logs** - Application logs from Lambda, EKS pods via Fluent Bit
  - **CloudWatch Metrics** - CPU, memory, request counts, latency, pod counts
  - **CloudWatch Alarms** - HPA/KEDA triggers, alerting, cluster health
- **Dashboards**:
  - System overview (requests/sec, error rate, latency)
  - Cost monitoring (per-service spend, pod costs)
  - RAG pipeline metrics (retrieval latency, index sizes)
  - Cluster health (node status, pod health, resource utilization)

#### AWS X-Ray
- **Purpose**: Distributed tracing for microservices
- **Tracing Flow**:
  - API Gateway → Lambda/EKS pods → DynamoDB/OpenSearch/Bedrock
  - End-to-end request latency breakdown
  - Performance bottleneck identification
  - Pod-to-service dependency mapping

---

### 2.10 Deployment & DevOps Layer

#### AWS ECR (Elastic Container Registry)
- **Purpose**: Docker image storage for EKS deployments
- **Repositories**:
  - `case-assistant-chat-engine`
  - `case-assistant-ingestion`
  - `case-assistant-query-orchestrator`
  - `case-assistant-session-manager`
- **Features**:
  - Image scanning for vulnerabilities (ECS scan leverages for EKS)
  - Lifecycle policies for old image cleanup
  - Immutable tags for production releases

#### AWS CloudFormation / Terraform
- **Purpose**: Infrastructure as Code (IaC)
- **Recommendation**: Terraform for multi-cloud support
- **State**: S3 backend for Terraform state with DynamoDB locking
- **Modules**: Reusable components per service layer
- **Kubernetes Tools**:
  - **Helm**: Package manager for EKS applications
  - **ArgoCD**: GitOps continuous delivery
  - **kubectl**: Direct cluster operations (debugging)

#### ArgoCD (GitOps)
- **Purpose**: Continuous delivery to EKS
- **Workflow**:
  1. Push Helm charts/manifests to Git repository
  2. ArgoCD detects changes and syncs to EKS
  3. Automated rollouts with health checks
  4. Rollback on failure
- **Benefits**: Declarative configuration, audit trail, self-healing

#### AWS CodePipeline / CodeBuild
- **Purpose**: CI/CD pipeline
- **Stages**:
  1. Source (Bitbucket/GitHub)
  2. Build (CodeBuild - tests, lint, Docker build)
  3. Deploy (CloudFormation/Terraform apply)
- **Environments**: Dev, Staging, Production

---

### 2.11 Content Delivery Layer (Optional)

#### Amazon CloudFront
- **Purpose**: CDN for global edge distribution
- **Use Case**: Static assets (React SPA), optional for API caching
- **Cache Behavior**:
  - `/static/*` - Cache static assets (CSS, JS, images)
  - `/api/*` - No caching (dynamic content)
- **WAF Integration**: Edge protection via WAF on CloudFront
- **Geo Restriction**: Australia-only access
- **Decision**: Optional for phase 1, add if global users needed

---

## 3. Service Selection Rationale

### 3.1 Why OpenSearch Serverless vs. Provisioned OpenSearch?

| Factor | Serverless | Provisioned |
|--------|------------|-------------|
| **Cost** | Pay per search/query | Fixed hourly cost per node |
| **Scaling** | Automatic | Manual |
| **Operations** | Zero management | Cluster maintenance |
| **Capacity Planning** | Not required | Required |
| **Use Case** | Variable workloads | Consistent high throughput |

**Decision**: **Serverless** for Case Assistant due to:
- Variable query patterns (user-driven)
- No capacity planning overhead
- Cost efficiency for sporadic workloads

### 3.2 Why DynamoDB On-Demand vs. Provisioned?

| Factor | On-Demand | Provisioned |
|--------|-----------|-------------|
| **Cost** | Pay-per-request | Fixed RCUs/WCUs |
| **Scaling** | Automatic | Manual limits |
| **Prediction** | No traffic prediction needed | Capacity planning required |
| **Use Case** | Unknown traffic patterns | Predictable throughput |

**Decision**: **On-Demand** for Case Assistant due to:
- Unpredictable query patterns
- No operational overhead
- Auto-scales to handle bursts

### 3.3 Why API Gateway + ALB vs. API Gateway Only?

| Factor | API Gateway + ALB | API Gateway Only |
|--------|-------------------|------------------|
| **WebSocket** | Native support | Limited support |
| **Health Checks** | Container-level | No health checks |
| **Path Routing** | Flexible | Limited to 300 paths |
| **Latency** | Slightly higher | Lower |
| **Operational Overhead** | Higher | Lower |

**Decision**: **API Gateway + ALB** for Case Assistant due to:
- Better WebSocket support for streaming chat
- Container health checks for reliability
- Path-based routing to microservices

### 3.4 Why EKS vs ECS?

| Factor | EKS | ECS Fargate |
|--------|-----|-------------|
| **Management** | Kubernetes control plane managed by AWS | Fully managed, no control plane |
| **Scaling** | HPA + KEDA for event-driven scaling | Service auto-scaling based on CPU/memory |
| **Ecosystem** | Rich Kubernetes ecosystem (Istio, Prometheus, etc.) | AWS-specific, limited ecosystem |
| **Portability** | Multi-cloud, runs anywhere | AWS-specific, lock-in |
| **Learning Curve** | Steeper (Kubernetes expertise required) | Easier, simpler model |
| **Cost** | Control plane: $72/month, plus compute | $0.005/vCPU-hour Fargate premium |
| **Complexity** | Higher (more moving parts) | Lower (simpler architecture) |
| **Maturity** | Kubernetes is industry standard | AWS-optimized, mature |

**Decision**: **EKS** for Case Assistant due to:
- Team has Kubernetes expertise (or willing to learn)
- Rich ecosystem for observability (OpenTelemetry, Prometheus, Grafana)
- Service mesh capability (Istio) for advanced traffic management
- KEDA for event-driven autoscaling (SQS queue depth → pod count)
- Future-proofing with standard Kubernetes skills
- Portability if multi-cloud strategy emerges

**When to choose ECS instead**:
- Team prefers simpler AWS-native approach
- No need for Kubernetes ecosystem
- Want lowest operational complexity
- Small team with limited Kubernetes experience

### 3.5 Why Karpenter vs Cluster Autoscaler?

| Factor | Karpenter | Cluster Autoscaler |
|--------|-----------|-------------------|
| **Node Provisioning** | Creates right-sized nodes for workload | Uses ASG to scale node groups |
| **Consolidation** | Actively consolidates underutilized nodes | Scales down when pods below threshold |
| **Spot Instances** | Native Spot support, automatic fallback | Manual Spot configuration |
| **Node Types** | Dynamically selects optimal instance types | Predefined node groups |
| **Graceful Shutdown** | Respects Pod Disruption Budgets | Basic cordon/drain |
| **Cost** | Open source, pay for EC2 only | Open source, pay for EC2 only |
| **Setup** | Provisioner + CRDs | Deployment per node group |

**Decision**: **Karpenter** for Case Assistant due to:
- Automatic instance type selection for optimal cost/performance
- Native Spot instance support with fallback to On-Demand
- Better node consolidation reduces waste
- Single deployment vs multiple Cluster Autoscaler deployments
- Future-proof with AWS-backed development

### 3.6 Why Neptune vs. DynamoDB Graph?

| Factor | Neptune | DynamoDB Graph |
|--------|---------|----------------|
| **Query Language** | Gremlin, openCypher | PartiQL (limited graph) |
| **Performance** | Optimized for graph queries | Adjacent list pattern (slow) |
| **Depth Traversal** | Fast for deep traversals | Performance degrades with depth |
| **Cost** | Higher | Lower |

**Decision**: **Neptune** for Case Assistant due to:
- Citation cross-references require multi-hop traversals
- Better performance for relationship queries
- Purpose-built for graph workloads

---

## 4. Integration Patterns

### 4.1 Synchronous Request/Response

```
User → API Gateway → ALB → EKS Pods → Bedrock
```

**Use Case**: Chat query requiring immediate response
**Services**: API Gateway, ALB, EKS (query-orchestrator pods), Bedrock
**Timeout**: 30 seconds (API Gateway limit)
**Latency**: 1-2 seconds end-to-end

### 4.2 Asynchronous Event-Driven

```
S3 Upload → EventBridge → Lambda → SQS → KEDA → EKS Pods (ingestion-service)
```

**Use Case**: Document ingestion (long-running process)
**Services**: S3, EventBridge, Lambda, SQS, KEDA scaler, EKS
**Benefits**: Decoupling, retry logic, no user wait, KEDA scales pods based on queue depth

### 4.3 VPC Link (Private Integration)

```
API Gateway → VPC Link → ALB → EKS Pods
```

**Use Case**: Public API to private VPC resources
**Benefits**: No internet gateway exposure, private network, security

### 4.4 PrivateLink (Private Service Access) - Phase 2

```
EKS Pods → VPC Endpoint → S3/DynamoDB/Bedrock
```

**Use Case**: Private access to AWS services when compliance requires
**Benefits**: No NAT gateway traffic, lower latency, enhanced security
**Phase**: Add in phase 2 when traffic exceeds 100 GB/month

---

## 5. Cost Optimization Considerations

### 5.1 Pay-Per-Use Services (No Idle Cost)

| Service | Pricing Model | Optimization |
|---------|---------------|--------------|
| **Lambda** | Per request + compute duration | Right-size memory, use provisioned concurrency sparingly |
| **API Gateway** | Per million requests + data transfer | Cache responses where possible |
| **OpenSearch Serverless** | Per search/query + data storage | Optimize chunk size, filter before search |
| **DynamoDB On-Demand** | Per read/write unit | Use GSIs wisely, filter with PK |
| **Neptune Serverless** | Per query | Cache graph traversals |

### 5.2 Fixed-Cost Services

| Service | Pricing Model | Optimization |
|---------|---------------|--------------|
| **ALB** | Per hour + LCU | Use path-based routing efficiently |
| **EKS Control Plane** | $72/month (fixed) | Shared across all clusters in region |
| **EKS Compute** | Per vCPU + GB per hour (Fargate) or EC2 pricing (managed nodes) | Right-size pod requests, use Spot for non-critical workloads |
| **PrivateLink** | Per endpoint hour + data transfer | Only for high-volume services (phase 2) |

### 5.3 Cost-Saving Strategies

1. **S3 Intelligent Tiering**: Automatically move old documents to Glacier
2. **DynamoDB TTL**: Auto-expire sessions and old data
3. **Lambda Reserved Concurrency**: Prevent runaway costs
4. **S3 Lifecycle Policies**: Delete processed raw documents after 30 days
5. **Bedrock On-Demand**: No provisioning, pay-per-token
6. **Karpenter Benefits**:
   - Right-size EKS nodes automatically (e.g., use m5.large instead of m5.xlarge when appropriate)
   - Use Spot instances for non-critical workloads (60-90% savings vs On-Demand)
   - Consolidate underutilized nodes to reduce waste
   - Eliminate over-provisioned node groups
7. **KEDA**: Scale ingestion pods to zero when idle, scale based on SQS queue depth
8. **HPA Right-Sizing**: Set appropriate pod resource requests/limits based on actual usage
9. **Fargate Spot** (if using Fargate): Up to 70% savings for fault-tolerant workloads

### 5.4 Estimated Monthly Costs (Phase 1, Moderate Traffic)

| Service | Estimate |
|---------|----------|
| **Lambda** | $50-100 |
| **API Gateway** | $30-50 |
| **ALB** | $20-30 |
| **EKS Control Plane** | $72 (fixed) |
| **EKS Compute** (Fargate or Managed Nodes) | $150-300 |
| **KEDA** | $0 (open source) |
| **OpenSearch Serverless** | $150-300 |
| **DynamoDB** | $50-100 |
| **Neptune Serverless** | $100-200 |
| **S3** | $20-50 |
| **Bedrock** | $200-500 |
| **Textract** | $50-100 |
| **WAF** | $15-20 |
| **CloudWatch** | $20-50 |
| **Other** (ECR, data transfer) | $50-100 |
| **Total** | **~$1,000-2,100/month** |

**Note**: EKS control plane ($72/month) is additional overhead vs ECS, but enables richer Kubernetes ecosystem

---

## 6. Security Architecture

### 6.1 Defense in Depth

```
User → Azure AD → WAF → API Gateway (JWT) → VPC → ALB → EKS Pods
                    ↓         ↓            ↓
                 Network   Application  Infrastructure
                  Layer      Layer        Layer
```

### 6.2 Network Security

- **VPC**: Private subnets only, no direct internet access for pods
- **Security Groups**: Restrictive rules, only allow necessary traffic (ALB → pods, pods → AWS services)
- **NACLs**: Additional network-level controls for subnet boundaries
- **VPC Endpoints**: Phase 1: Public endpoints with TLS. Phase 2: Private endpoints for S3, DynamoDB, Bedrock
- **WAF**: Web exploit protection at API Gateway
- **Network Policies**: Calico or Cilium for pod-to-pod traffic control (optional, phase 2)

### 6.3 Identity & Access Management

- **Azure AD**: External identity provider
- **JWT Tokens**: Validated by API Gateway authorizer
- **IRSA (IAM Roles for Service Accounts)**: Pod-level IAM permissions, no shared credentials
- **Service Account Annotations**: Each EKS service gets its own IAM role
- **Secrets Manager**: Store API keys, credentials, injected via CSI driver or environment variables
- **KMS**: Encryption at rest for sensitive data, EKS uses AWS-managed keys for etcd

### 6.4 Data Protection

- **Encryption at Rest**: S3, DynamoDB, OpenSearch, Neptune all encrypted
- **Encryption in Transit**: TLS 1.2+ for all connections
- **Data Classification**: Public (legislation), Internal (user queries), Confidential (user sessions)
- **PII Handling**: Strip user identifiers before logging
- **Retention Policies**: Automatic deletion after 7 days of inactivity

### 6.5 Compliance

- **Data Residency**: All data in AWS Sydney region (ap-southeast-2)
- **Audit Logging**: CloudTrail for API calls, CloudWatch for application logs
- **Access Controls**: Role-based access control (RBAC) for internal tools
- **Penetration Testing**: Authorized testing before production launch

---

## 7. Related Documents

### Architecture Diagrams
- **[01-High-Level-Infrastructure-Architecture](./diagrams/01-high-level-infrastructure-architecture.md)** - Visual overview of all AWS services
- **[02-Chat-Query-Flow-Architecture](./diagrams/02-chat-query-flow-architecture.md)** - RAG retrieval pipeline detailed flow
- **[03-Document-Ingestion-Flow-Architecture](./diagrams/03-document-ingestion-flow-architecture.md)** - Document processing pipeline flow
- **[04-Data-Architecture-Overview](./diagrams/04-data-architecture-overview.md)** - 6-index data model

### System Design Documents
- **[01-Chat-Architecture](./01-chat-architecture.md)** - High-level chat application architecture
- **[02-Document-Ingestion](./02-document-ingestion.md)** - Document processing pipeline with VLM+GPU
- **[03-Message-Routing](./03-message-routing.md)** - Orchestrator-based message routing
- **[04-Session-Lifecycle](./04-session-lifecycle.md)** - Session management and TTL
- **[11-Multi-Index-Strategy](./11-multi-index-strategy.md)** - 6-index RAG architecture specification
- **[10-Kubernetes-Deployment](./10-kubernetes-deployment.md)** - Kubernetes deployment details

### ADRs (Architecture Decision Records)
- **[07-Ingestion-Strategies-Comparison](./07-ingestion-strategies-comparison.md)** - Incremental vs. full refresh for ingestion
- **[08-Caching-Strategies-Discussion](./08-caching-strategies-discussion.md)** - Caching philosophy and strategies

---

## Appendix: AWS Service Icons Reference

| Service | Icon Color | Diagram Placement |
|---------|------------|-------------------|
| **API Gateway** | Purple | Entry point for all traffic |
| **ALB** | Blue/Grey | Internal VPC, behind API Gateway |
| **WAF** | Orange/Red | In front of API Gateway |
| **Lambda** | Orange | Event-driven orchestrators |
| **EKS** | Orange | Primary: Containerized services |
| **ECS** | Orange | Alternative: If simpler AWS-native approach preferred |
| **S3** | Green | Document storage |
| **DynamoDB** | Blue/Green | NoSQL database |
| **OpenSearch** | Orange/Blue | Vector and keyword search |
| **Neptune** | Blue/Green | Graph database |
| **Bedrock** | Pink/Purple | LLM and embeddings |
| **Textract** | Orange | OCR and text extraction |
| **EventBridge** | Pink/Green | Event bus |
| **CloudWatch** | Orange/Yellow | Monitoring and logging |
| **X-Ray** | Purple/Pink | Distributed tracing |
| **VPC** | Orange/Brown | Network isolation |
| **PrivateLink** | Orange/Brown | VPC endpoints (phase 2) |
| **CloudFront** | Orange/Grey | CDN (optional) |
| **ECR** | Orange | Container registry |
| **Karpenter** | Orange | Node autoscaling (Kubernetes) |
| **ArgoCD** | Purple | GitOps continuous delivery |

---

**Document Version**: 1.0.0
**Last Updated**: 2025-03-25
**Author**: Case Assistant Architecture Team
**Status**: Draft
