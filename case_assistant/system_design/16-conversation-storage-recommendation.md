# Conversation Storage Recommendation: Case Chat

**Document Version**: 3.0.0
**Date**: 2026-04-22
**Author**: Principal AI Engineer
**Status**: Design Recommendation
**Related Documents**: [15-conversation-storage-analysis.md](./15-conversation-storage-analysis.md), [04-session-lifecycle.md](./04-session-lifecycle.md), [12-high-level-design.md](./12-high-level-design.md), [14-data-retention-and-governance.md](./14-data-retention-and-governance.md)

---

## Executive Summary

**Recommendation**: **Aurora PostgreSQL + pgvector as primary store** for conversation history. OpenSearch ml-commons conversational memory should **NOT** be used.

### Key Reasons

| Factor | Aurora | OpenSearch Memory | Why Aurora Wins |
|--------|--------|-------------------|-----------------|
| **Architecture fit** | EKS Chat Engine | Requires OpenSearch agents | Custom orchestration, not ml-commons |
| **Compliance** | ACID, PITR, 7-year retention | Eventually consistent, no PITR | ATO/government requirements |
| **Session model** | Indefinite persistence, 7-day doc TTL | Not designed for TTL patterns | Matches [04-session-lifecycle.md](./04-session-lifecycle.md) |
| **Cost** | ~$250/month | ~$430/month + Aurora for compliance | Single system vs dual |

---

## Architecture Decision

### Current Chat Engine Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EKS Cluster                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                     Chat Engine                             │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │ │
│  │  │ Orchestrator   │  │ Session Manager│  │ Doc Manager  │ │ │
│  │  └────────────────┘  └────────────────┘  └──────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Aurora PostgreSQL                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  • sessions (indefinite persistence)                       │ │
│  │  • messages (conversation history)                         │ │
│  │  • message_embeddings (pgvector for semantic search)       │ │
│  │  • documents (7-day TTL tracking)                          │ │
│  │  • audit_trail (compliance)                                │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OpenSearch (separate)                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  • 6-index RAG (document chunks, not conversations)        │ │
│  │  • Metadata index                                          │ │
│  │  • Citation index                                          │ │
│  │  • Semantic index                                          │ │
│  │  • Keyword index                                           │ │
│  │  • Context index                                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Why OpenSearch Conversational Memory Is Wrong Fit

| Requirement | OpenSearch Memory | Aurora | Notes |
|-------------|-------------------|--------|-------|
| **EKS-based orchestration** | ❌ Requires ml-commons agents | ✅ Works with any | Chat Engine is custom Python/Agno |
| **Session indefinite persistence** | ❌ Not designed for TTL | ✅ Native with UPDATE | Sessions persist, docs expire |
| **7-year compliance** | ❌ No PITR, eventual consistency | ✅ PITR, WAL replay | Government requirement |
| **Row-Level Security** | ❌ Not available | ✅ Native RLS | Multi-tenant isolation |
| **Soft-delete** | ❌ No native support | ✅ `deleted_at` column | Compliance audit trail |
| **Foreign key relationships** | ❌ No JOINs | ✅ Full relational | Sessions → Messages → Documents |
| **Cost** | 💰💰 + Aurora still needed | 💰 | Two systems vs one |

---

## Data Model

### Core Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector v0.8.2+, supports up to 2,000 dims for HNSW indexing
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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
    content_embedding vector(1536),
    model_id TEXT,
    tokens_used INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    deleted_at TIMESTAMPTZ
);

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

CREATE INDEX messages_session_created_idx ON messages(session_id, created_at ASC)
    WHERE deleted_at IS NULL;

CREATE INDEX messages_embedding_idx ON messages
    USING hnsw (content_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX sessions_user_updated_idx ON sessions(user_id, updated_at DESC);

CREATE INDEX documents_expiry_idx ON session_documents(expires_at)
    WHERE processing_status = 'active';

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

---

## Query Patterns

### 1. Sequential Conversation Retrieval (Primary Pattern)

```sql
-- Get conversation history for a session
SELECT message_id, role, content, created_at
FROM messages
WHERE session_id = $1
  AND deleted_at IS NULL
ORDER BY created_at ASC;
```

**Index**: `messages_session_created_idx` (B-tree)
**Latency**: <10ms for typical session (50-100 messages)

### 2. Semantic Search Over Conversations

```sql
-- Find similar conversations
SELECT m.session_id, m.content, m.created_at,
       m.content_embedding <=> $1 as distance
FROM messages m
WHERE m.deleted_at IS NULL
  AND m.content_embedding IS NOT NULL
ORDER BY m.content_embedding <=> $1
LIMIT 10;
```

**Index**: `messages_embedding_idx` (HNSW)
**Latency**: ~50-100ms for 1M messages

### 3. Session Activity Check (for TTL)

```sql
-- Check for inactive sessions (7-day TTL)
SELECT session_id, last_activity_at
FROM sessions
WHERE last_activity_at < NOW() - INTERVAL '7 days'
  AND status = 'active';
```

**Index**: `sessions_user_updated_idx`

### 4. Document Expiry (cleanup job)

```sql
-- Find expired documents for cleanup
SELECT doc_id, session_id, s3_key
FROM session_documents
WHERE expires_at < NOW()
  AND processing_status = 'active';
```

**Index**: `documents_expiry_idx`

---

---

## Rejection of OpenSearch Conversational Memory

### Statement

> **OpenSearch ml-commons conversational memory should NOT be used for Case Chat conversation history storage.**

### Research-Backed Rationale

Detailed analysis available in [15-conversation-storage-analysis.md](./15-conversation-storage-analysis.md), Sections 4–6.

| Criterion | Finding | Source | Impact |
|-----------|---------|--------|--------|
| **Architectural mismatch** | Chat Engine runs on EKS with custom orchestration, not OpenSearch agents. OpenSearch memory (via ml-commons) requires agents running inside the OpenSearch cluster. | [15-conversation-storage-analysis.md](./15-conversation-storage-analysis.md) Section 4, "Mode 2: Agent Framework" | Would require rewriting Chat Engine to use ml-commons agent framework — a fundamental architecture change |
| **Compliance gap** | No ACID (eventual consistency only), no point-in-time recovery, no soft-delete, no row-level security. OpenSearch memory stores data in internal system indices not designed for long-term retention. | [15-conversation-storage-analysis.md](./15-conversation-storage-analysis.md) Section 5, "What This IS vs ISN'T" | Cannot meet ATO/government requirements. Would still need Aurora for compliance — adding a system, not replacing one. |
| **Consistency risk** | OpenSearch is eventually consistent (~1 second refresh interval). During cluster events, writes may be lost. | [15-conversation-storage-analysis.md](./15-conversation-storage-analysis.md) Section 1, "Limitations" | Conversation messages could be lost during failover — unacceptable for compliance records |
| **TTL model mismatch** | Session lifecycle requires indefinite sessions + 7-day document TTL. OpenSearch memory has no per-resource TTL concept. | [04-session-lifecycle.md](./04-session-lifecycle.md) | Would require custom TTL logic outside OpenSearch memory |
| **No relational queries** | Cannot do `SELECT m.*, s.user_id FROM messages m JOIN sessions s ON m.session_id = s.session_id`. All relationships must be denormalised. | [15-conversation-storage-analysis.md](./15-conversation-storage-analysis.md) Section 1, "Limitations" | Audit queries across sessions, users, and messages require application-level joins |
| **Cost duplication** | Would still need Aurora for compliance (audit trail, soft-delete, RLS, PITR). Two conversation stores = 2× operational complexity. | Cost analysis above | ~$180/month additional effective cost with no functional benefit |
| **Schema opacity** | OpenSearch memory uses internal system indices managed by the ml-commons plugin. You cannot customise the schema, add columns, or create custom indexes. | [15-conversation-storage-analysis.md](./15-conversation-storage-analysis.md) Section 5, "Internal Architecture" | Cannot add `workspace_id`, `retention_until`, or compliance-specific fields to the memory model |

### When OpenSearch Memory Would Be Appropriate

| Scenario | Would Use | Case Chat Match? |
|----------|-----------|------------------|
| Building agent entirely within OpenSearch ml-commons | Yes | No — EKS Chat Engine |
| No compliance requirements (7-year retention, audit trails) | Yes | No — ATO government |
| Team wants OpenSearch-native agent workflow with built-in context management | Yes | No — custom orchestration |
| Need context management features (SlidingWindowManager, SummarizationManager) | Yes | No — would need to build in Chat Engine anyway |
| Full-text search over conversations is a core product feature | Yes (consider hybrid) | Partial — could revisit |
| Scale exceeds 100M messages | Yes (consider hybrid) | No — projected <1M |

**Case Chat does NOT match these scenarios.**

---

## When This Decision Would Change

This recommendation is based on:
1. **Domain**: Document-first RAG system, not conversation-centric
2. **Architecture**: External EKS Chat Engine, not OpenSearch ml-commons agents
3. **Requirements**: ATO compliance, 7-year retention, ACID, RLS
4. **Scale**: Projected <1M messages

**Reconsider only if fundamental assumptions change**:

| Trigger | What Changes | Action |
|---------|-------------|--------|
| **Architecture migrates to OpenSearch agents** | Chat Engine moves inside ml-commons | Re-evaluate using ml-commons memory as primary store |
| **Conversations become authoritative sources** | System shifts from document-first to conversation-first | Semantic search may justify OpenSearch |
| **Message volume exceeds 10M** | pgvector HNSW performance degrades | Add OpenSearch as secondary index via CDC |
| **Real-time analytics becomes core requirement** | Dashboard/analytics is primary use case | Add OpenSearch analytics index via CDC |

**These are architectural shifts, not feature additions.** If the fundamental nature of the system doesn't change, Aurora remains the correct choice.

| Trigger | What Changes | Action |
|---------|-------------|--------|
| **Chat Engine moves to OpenSearch agents** | Architecture becomes OpenSearch-native | Re-evaluate using ml-commons memory as primary store |
| **Full-text search over history becomes a core feature** | PostgreSQL full-text search may not be sufficient | Add OpenSearch as secondary index (CDC from Aurora), keep Aurora as source of truth |
| **Message volume exceeds 10M** | pgvector HNSW may slow down | Add OpenSearch for semantic search over conversations (hybrid pattern) |
| **Real-time analytics dashboard required** | PostgreSQL materialised views add latency | Add OpenSearch analytics index via CDC |
| **Compliance requirements removed** | No longer need ACID/PITR/RLS | OpenSearch-only becomes viable for non-compliant workloads |
| **Team adopts OpenSearch agent framework** | ml-commons Mode 2 becomes the orchestration | Use built-in memory + Aurora as compliance replica |

Detailed analysis of these scenarios: [15-conversation-storage-analysis.md](./15-conversation-storage-analysis.md) Section 6, "When OpenSearch IS the Right Choice for Conversation History".

---

## OpenSearch Role in Case Chat

OpenSearch **IS** used in Case Chat, but for a **different purpose**:

| OpenSearch Use | Purpose |
|----------------|---------|
| **6-index RAG** | Document chunk retrieval (Metadata, Citation, Semantic, Keyword, Context, Graph) |
| **Vector search** | Semantic search over uploaded tax documents |
| **Full-text search** | BM25 keyword search over document content |
| **Aggregations** | Document metadata analytics |

**OpenSearch does NOT store conversation history.**

---

## Cost Comparison

### Scenario: 100K users, 10M messages/year

| Component | Aurora-Only | OpenSearch Memory | Hybrid (Aurora + OS Memory) |
|-----------|-------------|-------------------|----------------------------|
| **Aurora Serverless v2** (db.r6g.large, multi-AZ) | $180/month | $180/month (still needed) | $180/month |
| **Aurora storage** (100GB + I/O) | $30/month | $30/month | $30/month |
| **Aurora backup/PITR** | $15/month | $15/month | $15/month |
| **OpenSearch** (3 data nodes, already running for RAG) | $0 (incremental) | $0 (no extra nodes needed) | $0 (no extra nodes needed) |
| **Sync/replication overhead** | $0 | $25/month (Lambda/DMS) | $25/month |
| **Operational overhead** (monitoring, backups, on-call) | 1 system | 2 systems | 2 systems |
| **Total hard cost** | **~$225/month** | **~$250/month** | **~$250/month** |
| **Effective total** (incl. team overhead) | **~$250/month** | **~$430/month** | **~$430/month** |

**Note**: OpenSearch is already running for the 6-index RAG pipeline. The $430/month "OpenSearch Memory" figure includes the cost of operational complexity — managing sync between two conversation stores, handling inconsistency incidents, and maintaining two backup/restore runbooks. The hard cost difference (~$25/month) is small; the real cost is engineering time.

**Savings**: Aurora-only saves ~$180/month in effective cost ($2,160/year) with no functional loss.

---

## Risk Assessment

### Aurora-Only Risks

| Risk | Mitigation |
|------|------------|
| Vector search at scale | HNSW handles <10M messages; add OpenSearch later via CDC |
| Analytics queries | Materialized views; add OpenSearch later if needed |
| Single point of failure | Multi-AZ deployment, read replicas, automated backups |

### OpenSearch Memory Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Architectural mismatch | High | Would require rewriting Chat Engine |
| Compliance gap | Critical | Still need Aurora for 7-year retention |
| Cost increase | Medium | $180/month additional with no benefit |
| Operational complexity | Medium | Two systems to sync and monitor |

---

## Recommendation Summary

### Decision

**Use Aurora PostgreSQL + pgvector as the primary and ONLY conversation history store for Case Chat.**

### Implementation Guidance

**Single-system architecture**:

1. Deploy Aurora PostgreSQL with pgvector
2. Implement core schema (sessions, messages, documents, audit_log)
3. Chat Engine writes directly to Aurora
4. Sequential retrieval via B-tree indexes
5. Keyword search via `tsvector` (for P2 session search)
6. Optional: pgvector embeddings if semantic search requested later

**No OpenSearch for conversations** — OpenSearch is used for 6-index RAG on documents only.

### Success Criteria

| Metric | Target |
|--------|--------|
| Sequential retrieval latency | <10ms (p95) |
| Semantic search latency | <100ms (p95) |
| Storage cost/month | <$300 |
| Operational overhead | Single DB team |

---

## Related Documents

- [15-conversation-storage-analysis.md](./15-conversation-storage-analysis.md) - Detailed technology comparison
- [04-session-lifecycle.md](./04-session-lifecycle.md) - Session persistence requirements
- [12-high-level-design.md](./12-high-level-design.md) - AWS services catalog
- [11-multi-index-strategy.md](./11-multi-index-strategy.md) - 6-index RAG architecture (OpenSearch for documents, not conversations)

---

## Appendix: When OpenSearch Conversational Memory IS the Right Choice

This section documents scenarios where OpenSearch's conversational memory (ml-commons plugin) IS the appropriate choice for conversation storage, based on official OpenSearch documentation and real-world use cases.

### Scenarios Where OpenSearch Memory Excels

| Scenario | Why OpenSearch Memory | Key Features Used |
|----------|----------------------|-------------------|
| **Customer service agents** | Multiple short interactions, need recent context only | SlidingWindowManager, ToolsOutputTruncateManager |
| **Research assistants with heavy tool usage** | Large tool outputs, need summarization | SummarizationManager, context compression |
| **Personalized chatbots** | Learning user preferences across sessions | USER_PREFERENCE strategy, long-term memory |
| **Agents running within OpenSearch ml-commons** | Native integration, no external orchestration | Built-in agent framework, auto-injection |
| **Long-running conversations** | Context window overflow risk | Context management hooks, sliding windows |

### Real-World Use Case: Customer Service Agent

**Source**: [OpenSearch Blog - "Solving context overflow"](https://opensearch.org/blog/solving-context-overflow-how-opensearch-agents-stay-smart-in-long-conversations/)

**Problem**: Customer service agents handle multiple short interactions. Context accumulates quickly, and large tool outputs overwhelm the context window.

**Solution**: OpenSearch context management with sliding window and output truncation:

```json
POST /_plugins/_ml/context_management/customer-service-optimizer
{
  "description": "Optimized context management for customer service interactions",
  "hooks": {
    "pre_llm": [
      {
        "type": "SlidingWindowManager",
        "config": {
          "max_messages": 6,
          "activation": { "message_count_exceed": 15 }
        }
      }
    ],
    "post_tool": [
      {
        "type": "ToolsOutputTruncateManager",
        "config": { "max_output_length": 50000 }
      }
    ]
  }
}
```

**Why this works**:
- Keeps only 6 most recent messages after 15 messages accumulated
- Truncates tool outputs to 50K characters
- Agent runs entirely within OpenSearch (no external orchestration needed)
- Memory stored in OpenSearch's internal indices (no separate DB)

### Real-World Use Case: Research Assistant

**Source**: [OpenSearch Blog - "Solving context overflow"](https://opensearch.org/blog/solving-context-overflow-how-opensearch-agents-stay-smart-in-long-conversations/)

**Problem**: Research agents use many tools and accumulate large context, leading to token overflow and performance degradation.

**Solution**: OpenSearch context management with summarization:

```json
POST /_plugins/_ml/context_management/research-assistant-optimizer
{
  "description": "Context management for research agents with extensive tool interactions",
  "hooks": {
    "pre_llm": [
      {
        "type": "SummarizationManager",
        "config": {
          "summary_ratio": 0.4,
          "preserve_recent_messages": 8,
          "activation": { "tokens_exceed": 150000 }
        }
      }
    ],
    "post_tool": [
      {
        "type": "ToolsOutputTruncateManager",
        "config": { "max_output_length": 80000 }
      }
    ]
  }
}
```

**Why this works**:
- Summarizes older messages to 40% of original size when tokens exceed 150K
- Preserves 8 most recent messages in full
- Limits tool outputs to 80K characters
- LLM-based summarization preserves key information

### Real-World Use Case: Personalized Chatbot

**Source**: [OpenSearch Agentic Memory Documentation](https://opensearch.org/docs/latest/ml-commons-plugin/agentic-memory/)

**Problem**: Chatbot needs to remember user preferences across multiple conversation sessions.

**Solution**: OpenSearch agentic memory with USER_PREFERENCE strategy:

```json
POST /_plugins/_ml/memory_containers/_create
{
  "name": "personalized-chatbot",
  "configuration": {
    "embedding_model_type": "TEXT_EMBEDDING",
    "embedding_model_id": "your-embedding-model-id",
    "llm_id": "your-llm-model-id",
    "strategies": [
      {
        "type": "USER_PREFERENCE",
        "namespace": ["user_id"]
      },
      {
        "type": "SUMMARY",
        "namespace": ["user_id", "session_id"]
      }
    ]
  }
}
```

**Why this works**:
- `sessions` memory: Manages conversation sessions and metadata
- `working` memory: Active conversation data and agent state
- `long-term` memory: Extracted user preferences persist across sessions
- `history` memory: Audit trail of all memory operations
- Namespaces isolate memories by user/session

### Comparison: OpenSearch Memory vs Aurora for These Scenarios

| Scenario | OpenSearch Memory | Aurora | Winner |
|----------|------------------|--------|--------|
| Customer service (OpenSearch-native agent) | Built-in sliding window, auto-injection | Need custom implementation | **OpenSearch** |
| Research assistant (OpenSearch-native agent) | Native summarization, context hooks | Need external LLM calls | **OpenSearch** |
| Personalized chatbot (OpenSearch-native agent) | USER_PREFERENCE strategy, namespaces | Custom schema needed | **OpenSearch** |
| Same scenarios (external orchestration) | Requires rewriting agent | Works with any orchestration | **Aurora** |

### Key Insight: Architecture Coupling

OpenSearch conversational memory is optimal **ONLY when**:
1. Your agent runs entirely within OpenSearch's ml-commons framework
2. You don't need external orchestration (EKS, Lambda, etc.)
3. Compliance requirements are minimal (no 7-year retention, no RLS)
4. You want built-in context management features

If you're running agents externally (EKS, custom Python, LangGraph, Agno):
- OpenSearch memory adds unnecessary coupling
- Aurora provides the same storage with more flexibility
- You'd need to build context management yourself anyway

### Migration Path: Aurora → OpenSearch Memory

If starting with Aurora and later moving to OpenSearch-native agents:

**Phase 1**: Aurora-only (current recommendation)
- External orchestration on EKS
- Custom context management if needed

**Phase 2**: Add OpenSearch for agent features (if adopting ml-commons agents)
- Keep Aurora for compliance/audit
- Use OpenSearch memory for runtime agent context
- Sync data as needed

**Phase 3**: Full migration to OpenSearch agents (if architecture aligns)
- Evaluate trade-offs: compliance vs convenience
- May still need Aurora for long-term retention

---

## Change History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-22 | Initial recommendation document for Case Chat conversation storage |
| 2.0.0 | 2026-04-22 | Updated cost analysis ($250/month with breakdown), strengthened OpenSearch rejection with research-backed evidence from doc 15, added "When to Revisit This Decision" section with 6 trigger conditions, improved schema (RLS policies, partitioning, retention_until, workspace_id, pgvector v0.8.2 note), added compliance references to doc 14 |
| 2.1.0 | 2026-04-22 | Added Appendix with research-backed scenarios where OpenSearch conversational memory IS appropriate (customer service, research assistant, personalized chatbot), real-world use cases from OpenSearch blog, key insight on architectural coupling requirement |
| 3.0.0 | 2026-04-22 | Removed phased approach language — definitive Aurora-only recommendation based on domain analysis (document-first, not conversation-first), clarified that reconsideration only applies if fundamental assumptions change (architecture shift to OpenSearch agents, or conversations become authoritative sources), updated implementation guidance to single-system approach |
