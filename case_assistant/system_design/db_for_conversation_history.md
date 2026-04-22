# Database for Conversation History: Aurora PostgreSQL vs OpenSearch

**Document Version**: 2.1.0
**Date**: 2026-04-22
**Author**: Principal AI Engineer
**Status**: Design Recommendation
**Audience**: Architecture, Engineering, Product

---

## Executive Summary

**Recommendation**: Use **Aurora PostgreSQL** as the primary and ONLY conversation history store for Case Chat. OpenSearch ml-commons conversational memory should NOT be used.

**Note on pgvector**: If pgvector is not permitted in your environment, Aurora PostgreSQL remains the correct choice. Semantic search over conversations is **optional** and not a core requirement. Sequential retrieval and keyword search (via `tsvector`) cover all stated needs.

### Definitive Answer

| Factor | Aurora | OpenSearch Memory | Why Aurora Wins |
|--------|--------|-------------------|-----------------|
| **Architecture fit** | EKS Chat Engine | Requires OpenSearch agents | Custom orchestration, not ml-commons |
| **Compliance** | ACID, PITR, 7-year retention | Eventually consistent, no PITR | ATO/government requirements |
| **Session model** | Indefinite persistence, 7-day doc TTL | Not designed for TTL patterns | Matches session lifecycle |
| **Cost** | ~$250/month | ~$430/month + Aurora for compliance | Single system vs dual |
| **Semantic search** | Optional (pgvector if approved) | Built-in | Not a core requirement |

**Aurora PostgreSQL is the correct technical choice** — with or without pgvector.

---

## Table of Contents

1. [Technology Comparison](#technology-comparison)
2. [OpenSearch ML-Commons Framework](#opensearch-ml-commons-framework)
3. [Case Chat Decision Analysis](#case-chat-decision-analysis)
4. [Implementation Guidance](#implementation-guidance)
5. [When OpenSearch IS the Right Choice](#when-opensearch-is-the-right-choice)
6. [Related Documents](#related-documents)

---

## Technology Comparison

### Aurora PostgreSQL

| Capability | Specification |
|------------|----------------|
| **Vector Support** (optional) | pgvector extension if approved; up to 16,000 dimensions |
| **Full-Text Search** | Native `tsvector`/`tsquery` with GIN indexes |
| **ACID Compliance** | Full - WAL replication, point-in-time recovery |
| **Relational** | JOINs, foreign keys, constraints, row-level security |
| **Scalability** | Vertical scaling, read replicas, partitioning |
| **Storage Cost** | ~50-70% cheaper than OpenSearch |
| **Query Latency** | <10ms sequential, <100ms keyword search |

**Strengths**:
- Strong consistency guarantees
- Mature tooling and operational expertise
- Complex relational queries (JOINs, foreign keys)
- Point-in-time recovery for compliance
- Lower total cost of ownership
- Native full-text search (`tsvector`) covers keyword search needs

**Limitations**:
- Semantic search requires pgvector (if approved)
- Vector search throughput lower than OpenSearch at extreme scale (>10M messages)
- Analytics queries require materialized views

### OpenSearch with k-NN

| Capability | Specification |
|------------|----------------|
| **Vector Support** | Up to 16,000 dimensions, byte and binary vectors |
| **Index Types** | HNSW (Lucene, Faiss, NMSLIB), IVF (Faiss) |
| **Distance Functions** | L2, inner product, cosine, L1 |
| **Scalability** | Horizontal scaling, tens of billions of vectors |
| **Storage Cost** | Higher due to index overhead and replication |

**Strengths**:
- Excellent semantic search at scale
- Native aggregations and analytics
- Powerful full-text search with analyzers
- Horizontal scaling capabilities

**Limitations**:
- Eventual consistency (~1 sec refresh)
- Higher operational complexity
- No ACID guarantees or foreign key relationships
- Higher storage costs

---

## OpenSearch ML-Commons Framework

### What Is ml-commons?

**ml-commons** is OpenSearch's plugin that turns your cluster into an AI/ML execution platform — running models, building agents, and managing conversational memory entirely *inside* OpenSearch.

**Critical Insight**: OpenSearch's conversational memory is NOT a general-purpose database API — it is a capability *of* the ml-commons **agent framework**. Using it means buying into the framework.

### Two Modes of Operation

#### Mode 1: Model Hosting (embedding inference only)

Your application calls OpenSearch for ML tasks:

```
Application → POST /_plugins/_ml/_predict/text_embedding
OpenSearch → Returns embedding vector
```

**Case Chat uses this mode** for document embeddings.

#### Mode 2: Agent Framework (OpenSearch runs entire AI pipeline)

```
User Question → POST /_plugins/_ml/agents/{agent_id}/_execute
OpenSearch Agent Framework:
  1. Retrieve conversation history from Memory
  2. Run VectorDBTool (k-NN search)
  3. Run MLModelTool (call LLM)
  4. Save interaction to Memory (auto)
  5. Return response
```

**Case Chat does NOT use this mode** — Chat Engine orchestrates externally on EKS.

### OpenSearch Conversational Memory

| Feature | Description |
|---------|-------------|
| **Legacy Memory** | Memory → Messages (conversation_index) |
| **Agentic Memory** | Container → Session → Memory entries |
| **Context Management** | SlidingWindowManager, SummarizationManager, ToolsOutputTruncateManager |

### What It IS vs ISN'T

| What It IS | What It ISN'T |
|-------------|---------------|
| Runtime memory for OpenSearch agents | Not a general-purpose conversation DB |
| Multi-turn conversation management | Not designed for compliance retention |
| Auto-injects chat history into prompts | No Row-Level Security, soft-delete |
| Co-located with vector search | No ACID guarantees, no JOINs |
| Perfect for RAG within OpenSearch | Not designed for 7-year retention |

### When OpenSearch Memory Works

| Scenario | Verdict |
|----------|---------|
| Building RAG chatbot entirely within OpenSearch ml-commons | Use it |
| Agent orchestrates via OpenSearch agent framework | Use it |
| Need runtime context management for long conversations | Use it |
| Government compliance requiring 7-year retention | Aurora required |
| Custom orchestration running on EKS | Aurora required |
| Soft-delete, point-in-time recovery, ACID | Aurora required |

---

## Case Chat Decision Analysis

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EKS Cluster                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                     Chat Engine                             │ │
│  │  (Custom Python/Agno Orchestration)                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Aurora PostgreSQL                             │
│  • sessions (indefinite persistence)                           │
│  • messages (conversation history)                             │
│  • message_embeddings (pgvector for optional semantic search)  │
│  • documents (7-day TTL tracking)                              │
│  • audit_trail (compliance)                                    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OpenSearch (separate)                        │
│  • 6-index RAG (document chunks, NOT conversations)            │
│  • Vector search over tax documents                            │
│  • BM25 keyword search                                         │
│  • Document metadata analytics                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Why Aurora Wins for Case Chat

#### 1. Domain: Document-First, Not Conversation-First

Case Chat exists to help ATO professionals query authoritative tax documents (ITAA, rulings, cases). The value proposition is **RAG over documents**, not conversation as knowledge artifact.

| Knowledge Source | Authority | Searchable? |
|------------------|-----------|-------------|
| ITAA 1936/1997, GST Act, FBTAA | Statutory law | ✅ Primary (OpenSearch) |
| ATO Public Rulings | ATO position | ✅ Primary (OpenSearch) |
| AAT/Federal Court cases | Case law | ✅ Primary (OpenSearch) |
| ATO Practice Statements | Internal guidance | ✅ Primary (OpenSearch) |
| AI conversation about above | Derivative | ❌ Secondary (Aurora) |

Searching conversations is searching **derivations** of authoritative sources. Risks:
- Stale interpretations (law changes, new rulings)
- Hallucination echo chamber (AI citing AI)
- Misattribution (conversation ≠ ATO position)

#### 2. Architectural Incompatibility

| Option | Cost | Benefit |
|--------|------|---------|
| Keep Aurora | $0 | Meets requirements |
| Add OpenSearch alongside | +$300-800/mo + ops | Semantic search |
| Migrate to ml-commons | Major rewrite | Semantic search |

Rewriting Chat Engine to fit OpenSearch's framework is **architectural inversion** — the tail wagging the dog.

#### 3. PostgreSQL Capabilities Sufficient

"Search Sessions" is P2. PostgreSQL covers the requirement:

```sql
-- Metadata search
SELECT * FROM sessions
WHERE user_id = ? AND created_at > ?
ORDER BY created_at DESC;

-- Keyword search (covers "what did I ask about X?")
SELECT DISTINCT s.* FROM sessions s
JOIN messages m ON m.session_id = s.id
WHERE s.user_id = ?
AND m.content_tsvector @@ plainto_tsquery('english', ?)
ORDER BY s.created_at DESC;
```

This is **sufficient** for finding "that conversation about FBT from last month."

#### 4. ATO Governance: Authoritative Sources Preferred

ATO professionals cite primary sources. "The Practice Statement says X" carries weight. "The AI told me X in a previous session" does not.

Enabling semantic search over conversations could encourage reliance on secondary sources — contrary to ATO culture and risky for audit decisions.

#### 5. Operational Complexity

Running two databases for what PostgreSQL can do alone:
- Dual monitoring, alerting, patching
- Data sync between systems (eventual consistency bugs)
- Two failure modes
- Team must maintain expertise in both

### Rejection of OpenSearch Conversational Memory

| Criterion | Finding | Impact |
|-----------|---------|--------|
| **Architectural mismatch** | Chat Engine on EKS, not OpenSearch agents | Would require major rewrite |
| **Compliance gap** | No ACID, no PITR, no soft-delete, no RLS | Cannot meet ATO requirements |
| **Consistency risk** | Eventually consistent, potential data loss | Unacceptable for compliance records |
| **TTL model mismatch** | No per-resource TTL concept | Custom TTL logic required |
| **No relational queries** | No JOINs across sessions/users | Audit queries suffer |
| **Cost duplication** | Aurora still needed for compliance | Two conversation stores = 2× complexity |
| **Schema opacity** | Internal indices, not extensible | Cannot add compliance fields |

### When This Decision Would Change

**Reconsider only if fundamental assumptions change**:

| Trigger | What Changes | Action |
|---------|-------------|--------|
| **Semantic search becomes hard requirement** | Users need "find similar conversations" | Option A: Get pgvector approved<br>Option B: Add OpenSearch as secondary via CDC |
| **Architecture migrates to OpenSearch agents** | Chat Engine moves inside ml-commons | Re-evaluate ml-commons memory |
| **Conversations become authoritative sources** | System shifts to conversation-first | Semantic search may justify OpenSearch |
| **Message volume exceeds 10M** | PostgreSQL performance degrades | Add OpenSearch as secondary via CDC |
| **Real-time analytics becomes core** | Dashboard is primary use case | Add OpenSearch analytics via CDC |

## When Semantic Search Becomes Required

### Trigger Criteria

Semantic search over conversations should only be added when:

| Criteria | Threshold | Rationale |
|----------|-----------|-----------|
| **User demand** | Explicit requests for "find similar conversations" | Not speculative |
| **Usage frequency** | >20% of session searches require semantic | Validates need |
| **Keyword insufficient** | Users report keyword search fails >30% of time | tsvector not enough |
| **Business value proven** | Measurable productivity impact | ROI positive |

### Decision Framework: pgvector vs OpenSearch

If semantic search is approved, compare approaches:

| Dimension | Aurora + pgvector (if approved) | Aurora → OpenSearch (CDC) |
|-----------|-------------------------------|---------------------------|
| **Approval Required** | pgvector extension | Infrastructure change |
| **Complexity** | Low — single system | Medium — CDC pipeline |
| **Latency** | ~50-100ms (same DB) | ~100-200ms (network hop) |
| **Consistency** | Strong (ACID) | Eventual (~1-5 second lag) |
| **Scale Limit** | ~10M messages | Unlimited (horizontal) |
| **Monthly Cost** | $0 (if approved) | +$50-150 (Lambda/DMS) |
| **Ops Overhead** | Single system | Two systems + sync monitoring |
| **Full-text search** | Basic (tsvector) | Advanced (analysers, aggregations) |
| **Analytics** | Separate implementation | Built-in aggregations |

### Recommendation

| Scenario | Recommended Approach |
|----------|---------------------|
| **pgvector approved, <10M messages** | Aurora + pgvector (simpler) |
| **pgvector NOT approved** | Aurora → OpenSearch via CDC |
| **Projected >10M messages** | Aurora → OpenSearch via CDC |
| **Analytics also required** | Aurora → OpenSearch via CDC |

---

## CDC Implementation: Aurora to OpenSearch

> **Important**: CDC is a **Phase 4 concern**. It is NOT needed for MVP. This section exists so the team knows exactly what to do if semantic search or analytics becomes a hard requirement at scale. Skip this entire section unless you have hit one of the triggers in the "When This Decision Would Change" table above.

### What Is CDC?

**CDC (Change Data Capture)** is a pattern for automatically copying every database change (INSERT, UPDATE, DELETE) from one system to another. In our case:

```
Aurora PostgreSQL  ──── CDC ────>  OpenSearch
(source of truth)     (stream)     (search/analytics replica)
```

Every time a message is written to Aurora, CDC copies it to OpenSearch — automatically, in near-real-time, without any changes to the Chat Engine code.

### Why Would You Need CDC?

Aurora is the source of truth for conversation history (compliance, ACID, audit). But Aurora is not ideal for:
- **Semantic vector search** across millions of messages (OpenSearch k-NN is faster)
- **Full-text search with analyzers** (stemming, synonyms, fuzzy matching)
- **Real-time analytics dashboards** (aggregations, date histograms)

CDC lets you keep Aurora as source of truth while also having an OpenSearch replica for search-heavy workloads.

### What Flows Through CDC?

| What | Aurora (source) | Transformed? | OpenSearch (target) |
|------|----------------|-------------|---------------------|
| Message text | `content TEXT` | Analysed with English analyzer | `content` field (full-text searchable) |
| Message metadata | `role`, `created_at`, `session_id` | Copied as-is | Keyword/date fields |
| Embedding vector | Not stored (unless pgvector approved) | **Generated by Bedrock** during CDC | `content_embedding` (k-NN searchable) |
| Soft deletes | `deleted_at IS NOT NULL` | Filtered out | Document removed from index |
| Session info | `sessions` table | Joined via SQL | Denormalised into message document |

### When Do You Need CDC?

| Phase | CDC Needed? | Why |
|-------|------------|-----|
| **Phase 1 (MVP)** | **No** | Session list + keyword search via Aurora `tsvector` |
| **Phase 2 (keyword search)** | **No** | Aurora `tsvector` + GIN index handles this |
| **Phase 3 (semantic search)** | **Only if pgvector NOT approved** | pgvector on Aurora avoids CDC entirely |
| **Phase 4 (scale/analytics)** | **Yes** | >1M messages OR real-time dashboards required |

### Data Flow Diagram

```
                    ┌─────────────────────────────────┐
                    │         Chat Engine (EKS)        │
                    │   Writes messages to Aurora only │
                    └──────────────┬──────────────────┘
                                   │
                                   ▼ WRITE
                    ┌─────────────────────────────────┐
                    │       Aurora PostgreSQL          │
                    │       (source of truth)          │
                    │                                  │
                    │  sessions ──────────────────┐    │
                    │  messages ─────────────────┤│    │
                    │  session_documents          ││    │
                    │  audit_log                  ││    │
                    │                             ││    │
                    │  WAL (write-ahead log) ─────┘│    │
                    │  Every INSERT/UPDATE/DELETE   │    │
                    └──────────────┬───────────────┘    │
                                   │                    │
                                   ▼ CDC STREAM         │
                    ┌─────────────────────────────────┐
                    │         CDC Pipeline             │
                    │                                  │
                    │  Reads WAL changes               │
                    │  Transforms data:                │
                    │    • Adds English analyzer       │
                    │    • Generates embedding (Bedrock)│
                    │    • Denormalises session info    │
                    │    • Filters soft-deleted rows    │
                    │  Batches and indexes              │
                    └──────────────┬──────────────────┘
                                   │
                                   ▼ INDEX
                    ┌─────────────────────────────────┐
                    │       OpenSearch (replica)       │
                    │                                  │
                    │  conversations index:            │
                    │    • content (full-text)         │
                    │    • content_embedding (k-NN)    │
                    │    • user_id, workspace_id       │
                    │    • session_title, created_at   │
                    │                                  │
                    │  Used for:                       │
                    │    • Semantic search              │
                    │    • Advanced full-text search    │
                    │    • Analytics dashboards         │
                    └─────────────────────────────────┘

READ PATTERN:
  Sequential conversation  → Aurora (source of truth)
  Keyword search           → Aurora tsvector (Phase 2) OR OpenSearch (Phase 4)
  Semantic search          → OpenSearch k-NN (Phase 4 only)
  Analytics                → OpenSearch aggregations (Phase 4 only)
```

### Key Concept: Aurora Remains Source of Truth

```
Chat Engine ALWAYS writes to Aurora first.
  │
  ├── Write path:  Chat Engine → Aurora (synchronous, ACID)
  ├── CDC path:    Aurora → CDC Pipeline → OpenSearch (async, ~1-5 second lag)
  └── Read path:   Sequential reads → Aurora
                   Search reads → OpenSearch (when available)
```

If OpenSearch is down, the Chat Engine still works — conversations are saved to Aurora. If CDC falls behind, search results may be slightly stale but no data is lost.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Chat Engine                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Write Operations (sessions, messages)                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼ (Write)
┌─────────────────────────────────────────────────────────────────┐
│                    Aurora PostgreSQL                             │
│  • Source of truth                                             │
│  • ACID, PITR, RLS                                             │
│  • 7-year retention                                            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼ (CDC Stream)
┌─────────────────────────────────────────────────────────────────┐
│                      CDC Pipeline                                │
│  Option A: AWS DMS (Managed)                                   │
│  Option B: Logical Replication + Custom Handler                │
│  Option C: Lambda + Aurora PGAdapter                           │
│  Option D: Third-party (Airbyte, Fivetran)                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼ (Index)
┌─────────────────────────────────────────────────────────────────┐
│                      OpenSearch                                  │
│  • conversations index (semantic + full-text)                  │
│  • embeddings (k-NN search)                                     │
│  • aggregations (analytics)                                     │
└─────────────────────────────────────────────────────────────────┘
                            ▲
                            │ (Search Query)
┌─────────────────────────────────────────────────────────────────┐
│                      Chat Engine                                 │
│  • Search API calls OpenSearch directly                        │
│  • Detail fetch from Aurora if needed                          │
└─────────────────────────────────────────────────────────────────┘
```

---

### Option A: AWS DMS (Database Migration Service)

#### Overview

AWS DMS provides managed CDC from Aurora to OpenSearch. Change Data Capture reads Aurora's transaction log and streams changes to OpenSearch in near real-time.

#### Architecture

```
Aurora PostgreSQL
    ↓ (WAL logs via CDC)
AWS DMS Replication Instance
    ↓ (OpenSearch endpoint)
OpenSearch Domain
```

#### Configuration

**1. Create DMS Replication Instance:**

```json
{
  "ReplicationInstanceIdentifier": "case-chat-dms",
  "ReplicationInstanceClass": "dms.r5.large",
  "EngineVersion": "3.5.2",
  "MultiAZ": false,
  "PubliclyAccessible": false,
  "VpcSecurityGroupIds": ["sg-xxxxxxxx"],
  "PreferredMaintenanceWindow": "sun:02:00-sun:03:00"
}
```

**Cost**: ~$0.10/hour = ~$72/month for t3.medium, ~$180/month for r5.large

**2. Create Source Endpoint (Aurora):**

```json
{
  "EndpointIdentifier": "aurora-source",
  "EndpointType": "source",
  "EngineName": "postgresql",
  "ServerName": "case-chat.cluster-xxxxx.ap-southeast-2.rds.amazonaws.com",
  "Port": 5432,
  "Username": "dms_user",
  "DatabaseName": "casedb",
  "SslMode": "require"
}
```

**3. Create Target Endpoint (OpenSearch):**

```json
{
  "EndpointIdentifier": "opensearch-target",
  "EndpointType": "target",
  "EngineName": "opensearch",
  "ServerName": "search-case-chat-xxxxx.ap-southeast-2.es.amazonaws.com",
  "Port": 443,
  "Username": "admin",
  "SslMode": "require"
}
```

**4. Create Task (CDC):**

```json
{
  "ReplicationTaskIdentifier": "aurora-to-opensearch-cdc",
  "SourceEndpointArn": "arn:aws:dms:ap-southeast-2:xxxxx:endpoint/aurora-source",
  "TargetEndpointArn": "arn:aws:dms:ap-southeast-2:xxxxx:endpoint/opensearch-target",
  "ReplicationTaskSettings": {
    "TargetMetadata": {
      "TargetSchemaSelectionMode": "guided",
      "DocumentId": "message_id",
      "DocsToInvestigate": "1000"
    },
    "FullLoadSettings": {
      "TargetTablePrepMode": "DO_NOTHING"
    },
    "CDCSettings": {
      "BatchApplyPolicy": " BatchApply: Enabled"
    }
  },
  "MigrationType": "cdc",
  "TableMappings": "{
    \"rules\": [
      {
        \"rule-type\": \"selection\",
        \"rule-id\": \"1\",
        \"object-locator\": {
          \"schema-name\": \"public\",
          \"table-name\": \"messages\"
        },
        \"rule-action\": \"include\"
      }
    ]
  }"
}
```

**5. OpenSearch Index Template:**

```json
PUT _index_template/conversations-template
{
  "index_patterns": ["conversations*"],
  "template": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 2,
      "refresh_interval": "5s"
    },
    "mappings": {
      "properties": {
        "message_id": {"type": "keyword"},
        "session_id": {"type": "keyword"},
        "user_id": {"type": "keyword"},
        "workspace_id": {"type": "keyword"},
        "role": {"type": "keyword"},
        "content": {"type": "text", "analyzer": "english"},
        "content_embedding": {
          "type": "knn_vector",
          "dimension": 1536,
          "method": {
            "name": "hnsw",
            "space_type": "cosinesimil",
            "engine": "nmslib",
            "parameters": {
              "ef_construction": 64,
              "m": 16
            }
          }
        },
        "created_at": {"type": "date"},
        "metadata": {"type": "object"}
      }
    }
  }
}
```

#### Pros

| Pro | Description |
|-----|-------------|
| **Managed service** | No infrastructure to maintain |
| **No custom code** | Configuration-based setup |
| **Automatic failover** | Built-in high availability |
| **Transformation support** | Basic data mapping in UI |
| **Monitoring** | CloudWatch metrics integration |

#### Cons

| Con | Mitigation |
|-----|------------|
| **Cost** | ~$72-180/month | Use t3.medium for lower cost |
| **Transformation limits** | Limited mapping capabilities | Use Lambda for complex transforms |
| **Latency** | 1-5 second delay | Acceptable for search use case |
| **OpenSearch version lock** | Requires specific versions | Check compatibility matrix |

#### When to Use

- Team has no DMS experience
- Need quick implementation
- Budget allows ~$100/month overhead
- Simple 1:1 table-to-index mapping

---

### Option B: Logical Replication + Custom Handler

#### Overview

Use PostgreSQL's logical replication to capture changes, then a custom handler processes and indexes to OpenSearch.

#### Architecture

```
Aurora PostgreSQL
    ↓ (Publication)
Logical Replication Slot
    ↓ (Wal2Json)
Custom Handler (EKS Service)
    ↓ (Bulk API)
OpenSearch Domain
```

#### Configuration

**1. Enable Logical Replication in Aurora:**

```sql
-- Set parameter group (requires cluster restart)
ALTER SYSTEM SET wal_level = logical;
ALTER SYSTEM SET max_replication_slots = 10;
ALTER SYSTEM SET max_wal_senders = 10;

-- Create publication
CREATE PUBLICATION conversations_pub FOR TABLE messages;
```

**Parameter Group Settings:**

```
rds.logical_replication = 1
max_replication_slots = 10
max_wal_senders = 10
```

**2. Create Custom Handler (Python):**

```python
import asyncio
import json
import os
import asyncpg
from opensearchpy import AsyncOpenSearch

class CDCConsumer:
    """
    Consumes changes from Aurora logical replication slot
    and indexes them to OpenSearch.

    NOTE: In production, use psycopg2/3 with logical replication
    protocol support, or a library like 'pg_stream' that handles
    WAL decoding. This is simplified for illustration.
    """

    def __init__(self, dsn: str, opensearch: AsyncOpenSearch):
        self.dsn = dsn
        self.opensearch = opensearch

    async def index_changes(self, changes: list[dict]):
        if not changes:
            return

        bulk_body = []
        for change in changes:
            op = change["op"]
            doc_id = change["id"]

            if op == "insert":
                bulk_body.extend([
                    {"index": {"_index": "conversations", "_id": doc_id}},
                    change["data"]
                ])
            elif op == "update":
                bulk_body.extend([
                    {"update": {"_index": "conversations", "_id": doc_id}},
                    {"doc": change["data"]}
                ])
            elif op == "delete":
                bulk_body.append(
                    {"delete": {"_index": "conversations", "_id": doc_id}}
                )

        if bulk_body:
            await self.opensearch.bulk(body=bulk_body)

async def main():
    opensearch = AsyncOpenSearch(
        hosts=[os.getenv("OPENSEARCH_ENDPOINT")],
        http_auth=("admin", os.getenv("OPENSEARCH_PASSWORD")),
        use_ssl=True,
    )

    consumer = CDCConsumer(
        dsn=os.getenv("DATABASE_URL"),
        opensearch=opensearch,
    )

    buffer = []
    buffer_size = 100
    flush_interval = 5

    async def flush():
        if buffer:
            await consumer.index_changes(buffer)
            buffer.clear()

    # In production: connect to logical replication slot here
    # and decode WAL messages into `changes` dicts
    # Libraries: pg_stream, debezium-embedded, or raw pgoutput protocol
    async for change in consume_replication_slot():
        buffer.append(change)
        if len(buffer) >= buffer_size:
            await flush()

if __name__ == "__main__":
    asyncio.run(main())
```

**3. Kubernetes Deployment:**

```yaml
# cdc-consumer-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cdc-consumer
  namespace: case-chat
spec:
  replicas: 2  # HA with leader election
  selector:
    matchLabels:
      app: cdc-consumer
  template:
    metadata:
      labels:
        app: cdc-consumer
    spec:
      containers:
      - name: consumer
        image: case-chat/cdc-consumer:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: aurora-secret
              key: url
        - name: OPENSEARCH_PASSWORD
          valueFrom:
            secretKeyRef:
              name: opensearch-secret
              key: password
        livenessProbe:
          exec:
            command:
            - /app/healthcheck.sh
          initialDelaySeconds: 30
          periodSeconds: 60
        readinessProbe:
          exec:
            command:
            - /app/healthcheck.sh
          initialDelaySeconds: 10
          periodSeconds: 10
```

**4. Add Embedding Generation:**

```python
# Add to the handler
class SlotConsumer:
    def __init__(self, ..., embedding_client):
        self.bedrock = boto3.client('bedrock-runtime')

    async def _add_embedding(self, message: dict) -> dict:
        """Generate embedding for message content"""
        if message.get('role') == 'system':
            return message  # Skip system messages

        response = self.bedrock.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({'inputText': message['content']})
        )

        embedding = json.loads(response['body'].read())['embedding']
        message['content_embedding'] = embedding
        return message
```

#### Pros

| Pro | Description |
|-----|-------------|
| **Full control** | Custom transformation logic |
| **Lower cost** | No DMS instance (~$20/month for EKS) |
| **Embedding generation** | Can add enrichment pipeline |
| **Lower latency** | Bypass DMS overhead |
| **Observability** | Custom metrics, logging |

#### Cons

| Con | Mitigation |
|-----|------------|
| **Custom code** | Development time ~40-80 hours | Use existing libraries |
| **Operational overhead** | Must monitor service | Add alerts, health checks |
| **HA complexity** | Leader election required | Use Kubernetes leader election |
| **WAL retention** | Need to manage slot lag | Monitoring + alerting |

#### When to Use

- Need custom transformations (e.g., embedding generation)
- Want to minimize operational cost
- Team has Kubernetes/Python expertise
- Need fine-grained control over indexing

---

### Option C: Lambda Polling (Not True CDC)

> **Note**: This is NOT Change Data Capture. It is scheduled polling. It is simpler but has a 5-minute delay. Included here because it's the simplest "good enough" option.

#### Overview

A Lambda function runs every 5 minutes, queries Aurora for recent changes, and indexes them to OpenSearch. No WAL, no replication slots, no streaming.

#### Architecture

```
EventBridge (rate(5 minutes))
     │
     ▼
Lambda Function
     │
     ├── Query Aurora: "What messages were created in last 5 minutes?"
     ├── Generate embeddings via Bedrock
     └── Bulk index to OpenSearch

Aurora PostgreSQL ──(query)──> Lambda ──(bulk API)──> OpenSearch
```

#### Configuration

**1. Aurora Serverless v2 Data API:**

```bash
# Enable Data API
aws rds modify-db-cluster \
  --db-cluster-identifier case-chat \
  --enable-http-true \
  --apply-immediately
```

**2. Lambda Function:**

```python
# cdc_lambda.py
import os
import boto3
import psycopg3
from opensearchpy import OpenSearch
from datetime import datetime, timedelta

def lambda_handler(event, context):
    # Connect via Data API
    conn = psycopg3.connect(
        host=os.getenv('AURORA_HOST'),
        database=os.getenv('AURORA_DB'),
        user=os.getenv('AURORA_USER'),
        password=os.getenv('AURORA_PASSWORD'),
        port=5432
    )

    # Find recently modified messages (last 5 minutes)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT message_id, session_id, user_id, workspace_id,
               role, content, created_at, metadata
        FROM messages
        WHERE created_at > NOW() - INTERVAL '5 minutes'
          AND deleted_at IS NULL
        ORDER BY created_at
    """)

    messages = []
    for row in cursor.fetchall():
        message = {
            'message_id': str(row[0]),
            'session_id': str(row[1]),
            'user_id': str(row[2]),
            'workspace_id': str(row[3]),
            'role': row[4],
            'content': row[5],
            'created_at': row[6].isoformat(),
            'metadata': row[7]
        }

        # Add embedding (call Bedrock)
        message['content_embedding'] = _generate_embedding(row[5])
        messages.append(message)

    # Bulk index to OpenSearch
    if messages:
        opensearch = OpenSearch(
            hosts=[os.getenv('OPENSEARCH_ENDPOINT')],
            http_auth=('admin', os.getenv('OPENSEARCH_PASSWORD')),
            use_ssl=True
        )

        bulk_body = []
        for msg in messages:
            bulk_body.extend([
                {"index": {"_index": "conversations", "_id": msg['message_id']}},
                msg
            ])

        opensearch.bulk(body=bulk_body)

    conn.close()
    return {'indexed': len(messages)}

def _generate_embedding(text: str) -> list[float]:
    bedrock = boto3.client('bedrock-runtime')
    response = bedrock.invoke_model(
        modelId='amazon.titan-embed-text-v1',
        body=json.dumps({'inputText': text})
    )
    return json.loads(response['body'].read())['embedding']
```

**3. Scheduled Event (EventBridge):**

```json
{
  "Rule": "cdc-scheduler-rule",
  "ScheduleExpression": "rate(5 minutes)",
  "Targets": [{
    "Arn": "arn:aws:lambda:ap-southeast-2:xxxxx:function:case-chat-cdc",
    "Id": "cdc-target"
  }]
}
```

**4. Lambda Configuration:**

```yaml
# lambda-config.yaml
Type: AWS::Serverless::Function
Properties:
  FunctionName: case-chat-cdc
  Runtime: python3.11
  Handler: cdc_lambda.lambda_handler
  Timeout: 300
  MemorySize: 512
  ReservedConcurrentExecutions: 1
  Environment:
    Variables:
      AURORA_HOST: !Ref AuroraCluster.Endpoint.Address
      AURORA_DB: casedb
      AURORA_USER: !Sub '{{resolve:secretsmanager:AuroraSecret:username}}'
      AURORA_PASSWORD: !Sub '{{resolve:secretsmanager:AuroraSecret:password}}'
      OPENSEARCH_ENDPOINT: !GetAtt OpenSearchDomain.Endpoint
```

#### Pros

| Pro | Description |
|-----|-------------|
| **Simplest deployment** | No custom infrastructure |
| **Managed scaling** | Lambda handles concurrency |
| **Cost-effective** | Pay per execution |
| **Easy to modify** | Deploy new code instantly |

#### Cons

| Con | Mitigation |
|-----|------------|
| **5-minute lag** | Polling-based, not real-time | Acceptable for search |
| **RPO window** | Data loss if Lambda fails | Checkpoint in DynamoDB |
| **Cold starts** | First run slower | Provisioned concurrency |
| **Embedding cost** | Bedrock API calls | Budget ~$20/month |

#### When to Use

- Simpler than custom CDC service
- 5-minute delay is acceptable
- Want minimal operational overhead
- Low message volume (<10K/day)

---

### Option D: Third-Party CDC Tools

#### Airbyte (Open Source)

```
Aurora PostgreSQL → Airbyte (Docker/K8s) → OpenSearch
```

**Configuration:**

```yaml
# airbyte-config.yaml
connections:
  - source:
      type: postgres
      host: aurora-cluster.xxx.ap-southeast-2.rds.amazonaws.com
      port: 5432
      database: casedb
      replication_method: CDC
      publications: ['conversations_pub']

    destination:
      type: opensearch
      host: search-case-chat.ap-southeast-2.es.amazonaws.com
      port: 443
      index_name: conversations

    schedule:
      type: basic
      units: 5
      time_unit: minutes
```

**Pros**: Open source, pre-built connectors, UI configuration
**Cons**: Additional infrastructure to operate, ~40 hours setup

#### Fivetran (Managed)

```
Aurora PostgreSQL → Fivetran → OpenSearch
```

**Pricing**: ~$1/GB transferred + connector fee
**Pros**: Fully managed, excellent support
**Cons**: Expensive, vendor lock-in

---

### Comparison: CDC Options

| Option | Complexity | Cost | Latency | Embedding Support | Best For |
|--------|-----------|------|--------|------------------|----------|
| **AWS DMS** | Low | $72-180/mo | 1-5s | Limited (Lambda transform) | Quick implementation, simple 1:1 sync |
| **Logical Replication** | High | $20-50/mo | <1s | Full control | Custom pipelines, embeddings |
| **Lambda Polling** | Low | $5-20/mo | ~5min | Full control | Low volume, simple use cases, **recommended starting point** |
| **Airbyte** | Medium | Infrastructure cost | 5-15min | Requires extension | Open source preference |
| **Fivetran** | Low | $100+/mo | 1-5min | Limited | Managed service preference |

---

### Hybrid Read Pattern

Once OpenSearch has conversation data, route reads based on query type:

```python
class MessageRepository:
    def __init__(self, db: AsyncConnection, opensearch: AsyncOpenSearch):
        self.db = db
        self.opensearch = opensearch

    async def get_conversation(self, session_id: str) -> list[Message]:
        """Sequential reads from Aurora (source of truth)"""
        async with self.db.transaction():
            messages = await self.db.query("""
                SELECT message_id, role, content, created_at
                FROM messages
                WHERE session_id = $1 AND deleted_at IS NULL
                ORDER BY created_at ASC
            """, session_id)
        return messages

    async def keyword_search(self, user_id: str, query: str, limit: int = 10):
        """Keyword search: Aurora tsvector OR OpenSearch (your choice)"""
        # Option A: Use Aurora (source of truth)
        async with self.db.transaction():
            results = await self.db.query("""
                SELECT DISTINCT s.session_id, s.title, m.content, m.created_at
                FROM sessions s
                JOIN messages m ON m.session_id = s.id
                WHERE s.user_id = $1
                  AND m.content_tsvector @@ plainto_tsquery('english', $2)
                  AND s.deleted_at IS NULL
                ORDER BY m.created_at DESC
                LIMIT $3
            """, user_id, query, limit)
        return results

        # Option B: Use OpenSearch (more features)
        results = await self.opensearch.search(
            index='conversations',
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"user_id": user_id}},
                            {"match": {"content": query}}
                        ]
                    }
                },
                "highlight": {"fields": {"content": {}}},
                "size": limit
            }
        )
        return results

    async def semantic_search(self, query_embedding: list[float], limit: int = 10):
        """Semantic search: OpenSearch only (Aurora can't do this without pgvector)"""
        results = await self.opensearch.search(
            index='conversations',
            body={
                "query": {
                    "knn": {
                        "field": "content_embedding",
                        "query_vector": query_embedding,
                        "k": limit,
                        "num_candidates": 100
                    }
                },
                "size": limit
            }
        )
        return results

    async def aggregate_by_date(self, days: int = 30):
        """Analytics: OpenSearch only"""
        results = await self.opensearch.search(
            index='conversations',
            body={
                "size": 0,
                "query": {
                    "range": {
                        "created_at": {
                            "gte": f"now-{days}d/d"
                        }
                    }
                },
                "aggs": {
                    "messages_per_day": {
                        "date_histogram": {
                            "field": "created_at",
                            "calendar_interval": "day"
                        }
                    }
                }
            }
        )
        return results
```

---

### Failure Handling

**What happens when CDC fails?**

| Failure Mode | Impact | Mitigation |
|--------------|--------|------------|
| **Lambda crashes** | 5-min data gap in OpenSearch | Next Lambda run recovers |
| **Logical replication lag** | OpenSearch stale | Alert on WAL lag >100MB |
| **OpenSearch down** | Aurora unaffected | Queue changes, retry |
| **Network partition** | CDC stops | Auto-retry with exponential backoff |
| **Schema change** | Mapping breaks | Version index templates |

**Monitoring Setup:**

```python
# CloudWatch metrics
metrics = [
    {'Namespace': 'AWS/DMS', 'MetricName': 'CDCLatency', 'Threshold': 300000},
    {'Namespace': 'AWS/Lambda', 'MetricName': 'Errors', 'Threshold': 5},
    {'Namespace': 'Custom/OpenSearch', 'MetricName': 'IndexLagSeconds', 'Threshold': 600},
    {'Namespace': 'AWS/RDS', 'MetricName': 'ReplicationSlotDiskUsage', 'Threshold': 1024},
]
```

---

### Summary: Recommended Approach

| Scenario | Recommended CDC Option |
|----------|----------------------|
| **Quick start, simple sync** | AWS DMS |
| **Need embeddings, custom logic** | Logical Replication + Custom Handler |
| **Low volume, low ops** | Lambda Polling |
| **Open source preference** | Airbyte |
| **Managed service preference** | Fivetran (if budget allows) |

**For Case Chat**: Start with **Lambda Polling** (simplest, cheapest). If semantic search becomes P0/P1 with high volume, migrate to **Logical Replication + Custom Handler**.

---

## When This Decision Would Change

Revisit only if fundamental assumptions change:

| Trigger | What Changes | Action |
|---------|-------------|--------|
| **Semantic search becomes hard requirement AND pgvector NOT approved** | Cannot use pgvector on Aurora | Implement CDC to OpenSearch (start with Lambda Polling, Option C) |
| **Chat Engine migrates to OpenSearch agents** | Architecture becomes ml-commons Mode 2 | Re-evaluate ml-commons built-in memory as primary store |
| **Message volume exceeds 10M** | pgvector HNSW may slow down | Migrate from Lambda Polling to Logical Replication (Option B) for lower latency CDC |
| **Real-time analytics dashboard required** | PostgreSQL materialised views too slow | Add OpenSearch analytics index via CDC |
| **Full-text search quality insufficient** | `tsvector` cannot handle user needs (fuzzy, synonyms, stemming) | Add OpenSearch as secondary full-text index via CDC |
| **pgvector gets approved** | Semantic search possible on Aurora | No CDC needed for semantic search. CDC only for analytics/scale. |

---

## Implementation Guidance

### Core Schema

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Optional: Only if pgvector is approved
-- CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    workspace_id UUID,
    title VARCHAR(500),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'deleted')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,
    retention_until TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 years'),
    metadata JSONB DEFAULT '{}'
) PARTITION BY RANGE (created_at);

CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    -- Optional: Only if pgvector is approved
    -- content_embedding vector(1536),
    model_id TEXT,
    tokens_used INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    deleted_at TIMESTAMPTZ
);

-- Full-text search (always available)
ALTER TABLE messages ADD COLUMN content_tsvector TSVECTOR
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE TABLE session_documents (
    doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    s3_key TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    processing_status TEXT DEFAULT 'pending'
);

CREATE TABLE audit_log (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(session_id),
    event_type TEXT NOT NULL,
    actor_id UUID NOT NULL,
    event_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX messages_session_created_idx ON messages(session_id, created_at ASC)
    WHERE deleted_at IS NULL;

-- Full-text search index (always available)
CREATE INDEX messages_content_tsvector_idx ON messages
    USING GIN (content_tsvector) WHERE deleted_at IS NULL;

-- Optional: Semantic search index (only if pgvector is approved)
-- CREATE INDEX messages_embedding_idx ON messages
--     USING hnsw (content_embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);

CREATE INDEX sessions_user_updated_idx ON sessions(user_id, updated_at DESC);

CREATE INDEX documents_expiry_idx ON session_documents(expires_at)
    WHERE processing_status = 'active';

-- Row-Level Security
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY workspace_isolation ON sessions
    USING (workspace_id = current_setting('app.workspace_id')::UUID);

CREATE POLICY workspace_isolation ON messages
    USING (session_id IN (
        SELECT session_id FROM sessions
        WHERE workspace_id = current_setting('app.workspace_id')::UUID
    ));
```

### Query Patterns

#### 1. Sequential Conversation Retrieval (Primary)

```sql
-- Get conversation history for a session
SELECT message_id, role, content, created_at
FROM messages
WHERE session_id = $1
  AND deleted_at IS NULL
ORDER BY created_at ASC;
```

**Index**: B-tree on `(session_id, created_at)`
**Latency**: <10ms for typical session (50-100 messages)

#### 2. Keyword Search (P2 Feature)

```sql
-- Full-text search via tsvector
SELECT DISTINCT s.* FROM sessions s
JOIN messages m ON m.session_id = s.id
WHERE s.user_id = $1
AND m.content_tsvector @@ plainto_tsquery('english', $2)
ORDER BY s.created_at DESC;
```

**Add tsvector column**:
```sql
ALTER TABLE messages ADD COLUMN content_tsvector TSVECTOR
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX messages_content_tsvector_idx ON messages
    USING GIN (content_tsvector) WHERE deleted_at IS NULL;
```

#### 3. Semantic Search (Optional - Requires pgvector)

```sql
-- Find similar conversations via pgvector
-- NOTE: Only available if pgvector extension is approved
SELECT m.session_id, m.content, m.created_at,
       m.content_embedding <=> $1 as distance
FROM messages m
WHERE m.deleted_at IS NULL
  AND m.content_embedding IS NOT NULL
ORDER BY m.content_embedding <=> $1
LIMIT 10;
```

**Index**: HNSW on `content_embedding` (if pgvector approved)
**Latency**: ~50-100ms for 1M messages
**Status**: Optional — not required for core functionality

#### 4. Session Activity Check (TTL)

```sql
-- Check for inactive sessions (7-day TTL)
SELECT session_id, last_activity_at
FROM sessions
WHERE last_activity_at < NOW() - INTERVAL '7 days'
  AND status = 'active';
```

#### 5. Document Expiry (Cleanup Job)

```sql
-- Find expired documents for cleanup
SELECT doc_id, session_id, s3_key
FROM session_documents
WHERE expires_at < NOW()
  AND processing_status = 'active';
```

### Python Implementation Examples

```python
# Sequential retrieval
async def get_conversation(session_id: str) -> list[Message]:
    async with db.transaction():
        messages = await db.query("""
            SELECT message_id, role, content, created_at
            FROM messages
            WHERE session_id = $1 AND deleted_at IS NULL
            ORDER BY created_at ASC
        """, session_id)
    return messages

# Keyword search
async def search_messages(user_id: str, query: str, limit: int = 10):
    async with db.transaction():
        results = await db.query("""
            SELECT DISTINCT s.session_id, s.title, m.content, m.created_at
            FROM sessions s
            JOIN messages m ON m.session_id = s.id
            WHERE s.user_id = $1
              AND m.content_tsvector @@ plainto_tsquery('english', $2)
              AND s.deleted_at IS NULL
            ORDER BY m.created_at DESC
            LIMIT $3
        """, user_id, query, limit)
    return results

# Semantic search (optional - requires pgvector)
# If pgvector is not approved, this feature is unavailable
async def search_similar(query_embedding: list[float], limit: int = 10):
    async with db.transaction():
        results = await db.query("""
            SELECT m.session_id, m.content, m.created_at,
                   m.content_embedding <=> $1 as distance
            FROM messages m
            WHERE m.deleted_at IS NULL
              AND m.content_embedding IS NOT NULL
            ORDER BY m.content_embedding <=> $1
            LIMIT $2
        """, query_embedding, limit)
    return results
```

---

## When OpenSearch IS the Right Choice

This section provides counter-research — scenarios where OpenSearch IS the correct choice for conversation storage.

### Scenario 1: OpenSearch-Native Agentic RAG

When you want OpenSearch to be the entire AI platform:

- Zero integration code — memory, retrieval, LLM managed by agent framework
- Built-in context management (SlidingWindowManager, SummarizationManager)
- Conversation history co-located with vector index
- Tool traces automatically stored

**Trade-off**: Must still replicate to Aurora/DynamoDB for compliance.

### Scenario 2: Full-Text Search Is Core Feature

When users search conversations by keywords, phrases, topics:

- Powerful analysers (tokenisation, stemming, n-grams, synonyms)
- Built-in hit highlighting
- Aggregations (facets, histograms, significant terms)
- Fuzzy matching, BM25 scoring

**PostgreSQL alternative**: `plainto_tsquery()` + GIN index works but requires manual implementation.

### Scenario 3: Massive Scale (>100M Messages)

When volume exceeds PostgreSQL's horizontal scaling capability:

- Add nodes to scale — no application-level sharding
- Data streams + ISM policies for automated lifecycle
- Index-level partitioning native
- Cross-cluster replication

**PostgreSQL alternative**: Citus or pg_partman for partitioning — adds complexity.

### Scenario 4: Real-Time Analytics Dashboard

When live dashboards on conversation patterns are critical:

- Native aggregations at query time
- OpenSearch Dashboards integration
- Near-real-time (~1 second refresh)
- No ETL required

**PostgreSQL alternative**: Materialized views, separate analytics pipeline — adds latency.

### Decision Matrix

| Scenario | OpenSearch Advantage | Applicability to Case Chat |
|----------|---------------------|----------------------------|
| OpenSearch-native agentic RAG | Zero integration, built-in memory | **Low** — uses EKS Chat Engine |
| Full-text search over conversations | Analysers, highlighting, aggregations | **Medium** — tsvector sufficient for now |
| Massive scale (>100M messages) | Native horizontal scaling | **Low** — projected <1M |
| Real-time analytics dashboard | Native aggregations + Dashboards | **Medium** — could add later |
| Multi-tenant with DLS | Document-level security | **Low** — Aurora RLS equally good |
| Append-only with ISM lifecycle | Automated tier management | **Low** — Aurora partitioning sufficient |

### Conclusion

For Case Chat's requirements (EKS Chat Engine, ATO compliance, ACID, PITR, 7-year retention, RLS), **none of these scenarios override the Aurora recommendation**.

---

## Cost Comparison

### Scenario: 100K users, 10M messages/year

| Component | Aurora-Only | OpenSearch Memory | Hybrid |
|-----------|-------------|-------------------|--------|
| Aurora Serverless v2 (db.r6g.large) | $180/month | $180/month (still needed) | $180/month |
| Aurora storage + I/O | $45/month | $45/month | $45/month |
| OpenSearch (already running for RAG) | $0 incremental | $0 incremental | $0 incremental |
| Sync/replication overhead | $0 | $25/month (Lambda/DMS) | $25/month |
| Operational overhead | 1 system | 2 systems | 2 systems |
| **Total hard cost** | **~$225/month** | **~$250/month** | **~$250/month** |
| **Effective total** (incl. team overhead) | **~$250/month** | **~$430/month** | **~$430/month** |

**Savings**: Aurora-only saves ~$180/month in effective cost ($2,160/year) with no functional loss.

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Sequential retrieval latency | <10ms (p95) |
| Keyword search latency | <100ms (p95) |
| Semantic search latency (if added) | <100ms (p95) |
| Storage cost/month | <$300 |
| Operational overhead | Single DB team |

---

## External Research Evidence

This section documents research findings about OpenSearch usage patterns for chat/conversation storage in production environments.

### Research Scope

**Question**: Are there public case studies of organizations using OpenSearch (or Elasticsearch) specifically for chat history/conversation storage?

**Method**: Web searches across:
- OpenSearch and AWS official blogs/documentation
- GitHub repositories
- StackOverflow architecture discussions
- General web search for production deployments

**Date**: April 2026

### Findings Summary

| Source Type | Result |
|-------------|--------|
| **OpenSearch Blog** | Found agentic memory articles — specific to ml-commons agents |
| **AWS Case Studies** | Found agentic AI for observability — not chat history |
| **GitHub Repositories** | No results for "opensearch chat history conversation storage" |
| **StackOverflow** | Rate-limited — unable to query architecture discussions |
| **General Web** | No public case studies of OpenSearch for general chat storage |

### Key Finding: OpenSearch Targets Agentic AI, Not General Chat Storage

**Source**: [OpenSearch Blog](https://opensearch.org/blog/) — December 2025

> **"OpenSearch as an agentic memory solution: Building context-aware agents using persistent memory"**

**What this means**:
- OpenSearch's conversational memory features are **tightly coupled to ml-commons agent framework**
- This is NOT a general-purpose chat history database API
- Using it requires buying into the entire OpenSearch agent architecture

**Implication for Case Chat**:
- Case Chat uses EKS-based Chat Engine with custom orchestration
- Moving orchestration into OpenSearch ml-commons would be **architectural inversion**
- OpenSearch conversational memory is **not designed** for external chat engines

### Key Finding: AWS Marketing Targets Agentic AI Workflows

**Source**: [AWS Big Data Blog](https://aws.amazon.com/blogs/big-data/) — April 2026

> **"Agentic AI for observability and troubleshooting with Amazon OpenSearch Service"**

**What this means**:
- AWS is marketing OpenSearch for **agentic AI** use cases
- Not positioning it as general-purpose chat history storage
- Focus is on agents running inside OpenSearch, not external chat applications

### Key Finding: No Public Case Studies for General Chat Storage

**Web Search Results** (April 2026):

| Search Query | Result |
|--------------|--------|
| `"opensearch chat history conversation storage"` | Empty |
| `"elasticsearch chat message storage architecture production 2024"` | Empty |
| `"chat history" elasticsearch opensearch database choice` | Empty |
| `site:github.com opensearch chat history` | Empty |
| `site:stackoverflow.com opensearch chat storage` | Rate-limited |

**Interpretation**:
- Either (1) organizations are NOT using OpenSearch for general chat history storage, OR
- (2) Those that are have not published their architectures

**Either way**: No evidence of OpenSearch being standard/best practice for chat history storage.

### What This Means for Architecture Decisions

| Claim | Evidence |
|-------|----------|
| "OpenSearch is standard for chat history" | **NO PUBLIC EVIDICE** — searches returned empty |
| "OpenSearch ml-commons memory is for general chat" | **FALSE** — requires agents running inside OpenSearch |
| "Production deployments use OpenSearch for chat" | **NO PUBLIC CASE STUDIES** found |
| "AWS recommends OpenSearch for chat storage" | **FALSE** — AWS recommends it for agentic AI workflows |

### For Political Environments

If you need to justify NOT using OpenSearch for chat history:

1. **No public case studies** demonstrate OpenSearch as standard choice for general chat history storage
2. **OpenSearch's own documentation** positions conversational memory as part of ml-commons **agent framework** — not a standalone feature
3. **AWS marketing** targets agentic AI workflows, not general chat applications
4. **Architectural mismatch**: Using OpenSearch conversational memory requires moving orchestration INSIDE OpenSearch — major rewrite for Case Chat

### Sources

- [OpenSearch Blog - Agentic Memory](https://opensearch.org/blog/) (accessed April 2026)
- [AWS Big Data Blog - Agentic AI](https://aws.amazon.com/blogs/big-data/) (accessed April 2026)
- Web search attempts: 15+ queries across multiple domains (April 2026)

---

## Related Documents

- [04-session-lifecycle.md](./04-session-lifecycle.md) - Session persistence requirements
- [09-user-stories.md](./09-user-stories.md) - Product requirements and user stories
- [11-multi-index-strategy.md](./11-multi-index-strategy.md) - 6-index RAG architecture
- [12-high-level-design.md](./12-high-level-design.md) - AWS services catalog
- [14-data-retention-and-governance.md](./14-data-retention-and-governance.md) - Compliance requirements

---

## Change History

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | 2026-04-22 | Added "External Research Evidence" section documenting web search findings: OpenSearch Blog agentic memory article, AWS Big Data Blog agentic AI content, 15+ web search queries that returned NO public case studies of OpenSearch for general chat history storage. Key finding: OpenSearch conversational memory is tightly coupled to ml-commons agent framework, NOT a general-purpose chat storage API. Provides evidence for political environments defending Aurora choice. |
| 2.0.0 | 2026-04-22 | Major CDC section overhaul: added plain-English explanation of CDC (what/why/when), data flow diagram showing exactly what flows from Aurora to OpenSearch, clear Phase 4 framing (CDC not needed for MVP), fixed Option C (renamed from CDC to Polling), fixed Option B (removed broken wal2json import, simplified code), filled empty "When This Decision Would Change" section with 6 trigger conditions, added "recommended starting point" to Lambda Polling in comparison table |
| 1.1.0 | 2026-04-22 | Clarified that pgvector is optional — Aurora PostgreSQL (with or without pgvector) is the correct choice. Updated schema to comment out pgvector-specific elements, added tsvector as always-available alternative for keyword search, added section on "If Semantic Search Required Without pgvector" with CDC to OpenSearch as option B |
| 1.0.0 | 2026-04-22 | Consolidated from documents 15, 16, 17 — definitive Aurora recommendation for Case Chat conversation storage with technology comparison, OpenSearch ml-commons framework analysis, Case Chat decision rationale, implementation guidance, and scenarios where OpenSearch IS appropriate |
