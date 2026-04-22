# Database for Conversation History: Aurora PostgreSQL vs OpenSearch

**Document Version**: 1.1.0
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

### If Semantic Search Required Without pgvector

If "find similar conversations" becomes a hard requirement but pgvector is not approved:

**Option A**: Add OpenSearch as secondary index via CDC
```
Chat Engine → Aurora (primary, writes only)
                 ↓
              CDC Stream
                 ↓
            OpenSearch (search index for conversations)
```
- Aurora remains source of truth
- OpenSearch handles semantic + full-text search
- Eventual consistency acceptable for search feature

**Option B**: Request pgvector approval
- pgvector is a well-established extension
- Used by many AWS Aurora customers
- Can be evaluated for security/compliance

These are **architectural shifts**, not feature additions.

| Trigger | What Changes | Action |
|---------|-------------|--------|
| **Architecture migrates to OpenSearch agents** | Chat Engine moves inside ml-commons | Re-evaluate ml-commons memory |
| **Conversations become authoritative sources** | System shifts to conversation-first | Semantic search may justify OpenSearch |
| **Message volume exceeds 10M** | pgvector HNSW degrades | Add OpenSearch as secondary via CDC |
| **Real-time analytics becomes core** | Dashboard is primary use case | Add OpenSearch analytics via CDC |

These are **architectural shifts**, not feature additions. If the fundamental nature doesn't change, Aurora remains correct.

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
| 1.1.0 | 2026-04-22 | Clarified that pgvector is optional — Aurora PostgreSQL (with or without pgvector) is the correct choice. Updated schema to comment out pgvector-specific elements, added tsvector as always-available alternative for keyword search, added section on "If Semantic Search Required Without pgvector" with CDC to OpenSearch as option B |
| 1.0.0 | 2026-04-22 | Consolidated from documents 15, 16, 17 — definitive Aurora recommendation for Case Chat conversation storage with technology comparison, OpenSearch ml-commons framework analysis, Case Chat decision rationale, implementation guidance, and scenarios where OpenSearch IS appropriate |
