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
| **Containers for heavy workloads** | ECS/EKS for VLM+GPU processing, ingestion pipeline |
| **Managed services** | OpenSearch Serverless, DynamoDB, Neptune to reduce operational overhead |
| **Pay-per-use** | No always-on servers for variable workloads |
| **Security-first** | VPC isolation, WAF, private endpoints via PrivateLink |
| **Multi-region capability** | Infrastructure as Code enables regional replication |

---

## 2. AWS Services by Layer

### 2.1 Networking Layer

#### Amazon VPC (Virtual Private Cloud)
- **Purpose**: Network isolation for compute resources
- **Configuration**: Private subnets only, no public subnets for application workloads
- **Components**: ALB, ECS/EKS cluster, Lambda in private subnets
- **Connectivity**: VPC Link for API Gateway → ALB, PrivateLink for AWS services

#### Application Load Balancer (ALB)
- **Purpose**: Internal traffic routing to containerized services
- **Features**:
  - Path-based routing (/api/*, /ingest, /health)
  - Health checks for ECS/EKS pods
  - WebSocket support for real-time chat streaming
  - Sticky sessions for conversation continuity
- **Placement**: Internal VPC, behind API Gateway, accessed via VPC Link

#### VPC Link
- **Purpose**: Private connection from API Gateway to ALB
- **Type**: Regional VPC Link (NLB/ALB integration)
- **Benefit**: No internet gateway exposure for internal traffic

#### AWS PrivateLink (VPC Endpoints)
- **Purpose**: Private connectivity to AWS services without internet gateway
- **Endpoints**:
  - S3 (gateway endpoint) - document storage
  - DynamoDB (gateway endpoint) - citation and metadata indices
  - Bedrock (interface endpoint) - LLM and embeddings
  - OpenSearch Serverless (interface endpoint) - vector search
- **Cost**: ~$7.30/month per endpoint

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
  - `ingestion-orchestrator` - Triggered by S3 PUT, coordinates document processing
  - `query-orchestrator` - Coordinates 6-index retrieval pipeline
  - `session-cleanup` - Scheduled Lambda for TTL expiration
- **Runtime**: Python 3.11 with uv package manager
- **Memory**: 1-2 GB configs based on workload
- **Timeout**: Up to 15 minutes for ingestion orchestrator
- **Benefits**: Pay-per-invocation, auto-scaling, no idle costs

#### Amazon ECS (Elastic Container Service)
- **Purpose**: Container orchestration for stateful services
- **Engine**: Fargate (serverless containers)
- **Services**:
  - Chat Engine Service - Conversation management
  - Document Ingestion Service - Page processing, chunking
  - Orchestrator Service - RAG query coordination
  - Session Manager Service - Session lifecycle
- **Task Size**: 2-4 vCPU, 4-8 GB RAM per task
- **Scaling**: Auto-scaling based on CPU/memory or request count
- **Benefits**: No EC2 management, pay only for running tasks

#### Amazon EKS (Elastic Kubernetes Service) - Optional
- **Purpose**: Alternative to ECS for complex orchestration needs
- **Use Case**: If team has Kubernetes expertise, needs advanced features
- **Node Groups**: Managed node groups or Fargate profiles
- **Decision**: Start with ECS, migrate to EKS only if needed

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
  - S3 Event Notifications to trigger Lambda
  - S3 Lifecycle policies for tiering to Glacier
- **Access**: PrivateLink VPC endpoint (no internet gateway)

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
- **Access**: PrivateLink VPC endpoint

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
- **Access**: PrivateLink VPC endpoint

#### Amazon Neptune
- **Purpose**: Graph database for citation cross-references
- **Graph Model**:
  - Nodes: Citations (sections, cases, rulings), definitions, examples
  - Edges: `references`, `defines`, `cites`, `contradicts`
  - Traversals: Expand related citations during retrieval
- **Edition**: Neptune Serverless (pay-per-query)
- **Access**: PrivateLink VPC endpoint
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
- **Access**: PrivateLink VPC endpoint

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
  - **CloudWatch Logs** - Application logs from Lambda, ECS
  - **CloudWatch Metrics** - CPU, memory, request counts, latency
  - **CloudWatch Alarms** - Auto-scaling triggers, alerting
- **Dashboards**:
  - System overview (requests/sec, error rate, latency)
  - Cost monitoring (per-service spend)
  - RAG pipeline metrics (retrieval latency, index sizes)

#### AWS X-Ray
- **Purpose**: Distributed tracing for microservices
- **Tracing Flow**:
  - API Gateway → Lambda/ECS → DynamoDB/OpenSearch/Bedrock
  - End-to-end request latency breakdown
  - Performance bottleneck identification

---

### 2.10 Deployment & DevOps Layer

#### AWS ECR (Elastic Container Registry)
- **Purpose**: Docker image storage for ECS/EKS
- **Repositories**:
  - `case-assistant-chat-engine`
  - `case-assistant-ingestion`
  - `case-assistant-orchestrator`
- **Features**:
  - Image scanning for vulnerabilities
  - Lifecycle policies for old image cleanup

#### AWS CloudFormation / Terraform
- **Purpose**: Infrastructure as Code (IaC)
- **Recommendation**: Terraform for multi-cloud support
- **State**: S3 backend for Terraform state
- **Modules**: Reusable components per service layer

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

### 3.4 Why ECS Fargate vs. EC2?

| Factor | ECS Fargate | EC2 |
|--------|-------------|-----|
| **Management** | No server management | OS patching, maintenance |
| **Scaling** | Automatic task scaling | Manual ASG configuration |
| **Cost** | Pay-per-task, premium | Pay-per-instance |
| **Isolation** | Native container isolation | Shared instances |

**Decision**: **ECS Fargate** for Case Assistant due to:
- No EC2 management overhead
- Pay only for running tasks
- Automatic scaling based on demand

### 3.5 Why Neptune vs. DynamoDB Graph?

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
User → API Gateway → ALB → ECS → Bedrock
```

**Use Case**: Chat query requiring immediate response
**Services**: API Gateway, ALB, ECS, Bedrock
**Timeout**: 30 seconds (API Gateway limit)
**Latency**: 1-2 seconds end-to-end

### 4.2 Asynchronous Event-Driven

```
S3 Upload → EventBridge → Lambda → SQS → Lambda
```

**Use Case**: Document ingestion (long-running process)
**Services**: S3, EventBridge, Lambda, SQS
**Benefits**: Decoupling, retry logic, no user wait

### 4.3 VPC Link (Private Integration)

```
API Gateway → VPC Link → ALB → ECS
```

**Use Case**: Public API to private VPC resources
**Benefits**: No internet gateway, private network, security

### 4.4 PrivateLink (Private Service Access)

```
ECS → VPC Endpoint → S3/DynamoDB/Bedrock
```

**Use Case**: Private access to AWS services
**Benefits**: No NAT gateway, lower latency, enhanced security

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
| **ECS Fargate** | Per vCPU + GB per hour | Auto-scale to zero when idle |
| **PrivateLink** | Per endpoint hour + data transfer | Only for high-volume services |

### 5.3 Cost-Saving Strategies

1. **S3 Intelligent Tiering**: Automatically move old documents to Glacier
2. **DynamoDB TTL**: Auto-expire sessions and old data
3. **Lambda Reserved Concurrency**: Prevent runaway costs
4. **S3 Lifecycle Policies**: Delete processed raw documents after 30 days
5. **Bedroid On-Demand**: No provisioning, pay-per-token
6. **Spot Instances for EKS**: If using EKS, use Spot for non-critical workloads

### 5.4 Estimated Monthly Costs (Phase 1, Moderate Traffic)

| Service | Estimate |
|---------|----------|
| **Lambda** | $50-100 |
| **API Gateway** | $30-50 |
| **ALB** | $20-30 |
| **ECS Fargate** | $100-200 |
| **OpenSearch Serverless** | $150-300 |
| **DynamoDB** | $50-100 |
| **Neptune Serverless** | $100-200 |
| **S3** | $20-50 |
| **Bedrock** | $200-500 |
| **Textract** | $50-100 |
| **WAF** | $15-20 |
| **PrivateLink** | $30-50 |
| **CloudWatch** | $20-50 |
| **Other** | $50-100 |
| **Total** | **~$900-2,000/month** |

---

## 6. Security Architecture

### 6.1 Defense in Depth

```
User → Azure AD → WAF → API Gateway (JWT) → VPC → ALB → ECS
                    ↓         ↓            ↓
                 Network   Application  Infrastructure
                  Layer      Layer        Layer
```

### 6.2 Network Security

- **VPC**: Private subnets only, no direct internet access
- **Security Groups**: Restrictive rules, only allow necessary traffic
- **NACLs**: Additional network-level controls
- **VPC Endpoints**: Private access to AWS services (no NAT gateway)
- **WAF**: Web exploit protection at API Gateway

### 6.3 Identity & Access Management

- **Azure AD**: External identity provider
- **JWT Tokens**: Validated by API Gateway authorizer
- **IAM Roles**: Least privilege for Lambda, ECS, Bedrock access
- **Secrets Manager**: Store API keys, credentials
- **KMS**: Encryption at rest for sensitive data

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
| **ECS** | Orange | Containerized services |
| **EKS** | Orange | Alternative to ECS |
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
| **PrivateLink** | Orange/Brown | VPC endpoints |
| **CloudFront** | Orange/Grey | CDN (optional) |
| **ECR** | Orange | Container registry |
| **WAF** | Orange/Red | Web application firewall |

---

**Document Version**: 1.0.0
**Last Updated**: 2025-03-25
**Author**: Case Assistant Architecture Team
**Status**: Draft
