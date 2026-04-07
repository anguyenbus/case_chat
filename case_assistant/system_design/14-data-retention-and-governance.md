# Data Retention, Governance, and Access Control

**Document Version**: 1.5.0
**Date**: 2026-04-07
**Author**: Principal AI Engineer
**Status**: Design Discussion
**Type**: Architecture Decision Record
**Related Documents**: [14a-questions-and-gaps.md](./14a-questions-and-gaps.md) - Detailed open questions and technical review

**Current Status**: Awaiting STEP 1 confirmation (Public-Facing vs ATO Internal). See "The Two Key Decisions" section below.

**Acknowledgments**: Sections 3.6-3.8 incorporate patterns from the AI Coach reference architecture (end-to-end encryption, DLQ alerting, LangFuse observability).

---

## Executive Summary

This document explores data classification, retention policies, and access controls for the Case Assistant system. The architecture fundamentally depends on one **blocking question**:

> **Is this system for public taxpayer-facing use OR ATO internal use?**

These scenarios have opposite requirements:

| Scenario | Retention Required | Auto-Delete Acceptable | Records Authority Needed | Architecture Approach |
|----------|-------------------|------------------------|--------------------------|----------------------|
| **Public Taxpayer-Facing** | None (user data only) | Yes | No | Ephemeral sessions, 90-day user data TTL |
| **ATO Internal Use** | 7 years minimum | No | Yes | Persistent records, soft-delete, archival |

**Current Design Gap**: The document assumes ATO internal use with 7-year retention. If the system is actually public-facing, significant simplification is possible. If ATO internal, Records Management engagement is required before implementation.

**Key Recommendations for ATO Internal Use**:
1. **Dual-layer architecture**: Temporary document storage (7-day TTL) + persistent conversation history (7-year retention)
2. **PostgreSQL-first**: Use Aurora PostgreSQL for sessions instead of Redis (simpler, compliant, durable)
3. **Soft-delete pattern**: User deletion marks data as deleted, but data retained for 7 years
4. **Row-Level Security**: Database-level access control using PostgreSQL RLS
5. **Tiered retention consideration**: Different conversation types may warrant different retention periods

**Action Required**: Engage with ATO Records Management team to confirm actual requirements before implementing this architecture.

| Scenario | Current Design Fit | Required Changes (if applicable) |
|----------|-------------------|-------------------------------|
| **Public Taxpayer-Facing** | ✅ Well-aligned | Ephemeral sessions, auto-deletion appropriate for public access |
| **ATO Internal Use** | ⚠️ Potentially misaligned | May require records retention, audit trails, longer retention |

**Key Discussion Point**: If the system is classified as creating Commonwealth records under the Archives Act 1983, auto-deletion of conversation history and session data may not be permitted without National Archives authority.

**Recommendation**: This document proposes a dual-layer architecture for the ATO internal use case:
1. **Application layer**: Temporary session-scoped document storage (7-day TTL on uploaded PDFs)
2. **Records layer**: Persistent conversation and query history (7-year minimum retention) with soft-delete

**Action Required**: Engage with ATO Records Management team to confirm actual requirements before implementing this architecture.

---

## The Two Key Decisions

This document ultimately addresses two technical decisions that **depend entirely on the deployment scenario**:

```mermaid
graph TB
    START[Confirm Deployment Scenario] --> DECISION{Public-Facing or ATO Internal?}

    DECISION -->|Public Taxpayer-Facing| PUBLIC[Decision 1: No 7-year retention<br/>Decision 2: Basic RBAC]
    DECISION -->|ATO Internal Use| INTERNAL[Decision 1: 7-year retention required<br/>Decision 2: Defense-in-depth RBAC]

    PUBLIC --> SIMPLE[Simple Architecture:<br/>• Redis sessions<br/>• 90-day user data TTL<br/>• Application-level filtering]
    INTERNAL --> COMPLEX[Compliant Architecture:<br/>• Aurora PostgreSQL<br/>• Soft-delete + archival<br/>• PostgreSQL RLS + audit]

    style DECISION fill:#FFF3E0
    style PUBLIC fill:#E8F5E9
    style INTERNAL fill:#FFEBEE
```

### Decision 1: Session Persistence (7-year retention?)

| Question | Public-Facing Answer | ATO Internal Answer |
|----------|---------------------|---------------------|
| Are conversations Commonwealth records? | No | **Yes - must confirm** |
| What retention period applies? | User-controlled (90-day default) | **7 years minimum** |
| Where do we store chat history? | Optional, Redis | **Aurora PostgreSQL required** |
| Can we auto-delete? | Yes | **No - soft-delete only** |
| Cost impact | ~$500/year | **~$15,000/year** |

**Stakeholder**: Records Management Team

---

### Decision 2: Fine-Grained Access Control (how strict?)

| Question | Public-Facing Answer | ATO Internal Answer |
|----------|---------------------|---------------------|
| Is PostgreSQL RLS required? | Optional (app filtering OK) | **Yes - defense in depth** |
| Do we need audit logging? | Basic access logs | **Full audit trail required** |
| Team/workspace access needed? | Optional | **Yes - for collaboration** |
| Data isolation level | User-scoped | **User + workspace + audit** |
| What happens on user offboard? | Simple delete | **Legal hold may apply** |

**Stakeholder**: Security Team

---

## Decision Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Confirm Scenario (Product/Stakeholders)                 │
│                                                                 │
│   Is this system for:                                           │
│   [ ] Public Taxpayer-Facing  ────────► Skip to STEP 5         │
│   [ ] ATO Internal Use         ────────► Continue to STEP 2    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Records Management Engagement                           │
│                                                                 │
│   • Are AI conversations Commonwealth records?                  │
│   • What GDS items apply?                                       │
│   • Is tiered retention acceptable?                             │
│                                                                 │
│   Answer determines Decision 1 (Session Persistence)            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Security Team Engagement                                │
│                                                                 │
│   • Is PostgreSQL RLS required?                                 │
│   • What audit trail is needed?                                 │
│   • Workspace/team access requirements?                         │
│                                                                 │
│   Answer determines Decision 2 (Access Control)                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Architecture Finalization                               │
│                                                                 │
│   • Design based on confirmed requirements                      │
│   • Update this document with decisions                         │
│   • Submit Records Authority if needed                          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Implementation                                          │
│                                                                 │
│   Public-Facing:  Simple architecture, lower cost              │
│   ATO Internal:  Compliant architecture, Records Authority      │
└─────────────────────────────────────────────────────────────────┘
```

**Current Status**: Awaiting STEP 1 confirmation from Product stakeholders.

---

## Table of Contents

1. [Session Data Classification and Storage](#1-session-data-classification-and-storage)
2. [Session Lifecycle and Retention Policy](#2-session-lifecycle-and-retention-policy)
3. [RBAC and Fine-Grained Access Control](#3-rbac-and-fine-grained-access-control)
4. [Proposed Architecture Changes](#4-proposed-architecture-changes)
5. [Implementation Roadmap](#5-implementation-roadmap)

---

## 1. Session Data Classification and Storage

### 1.1 Current Design Gaps

The current design treats all session data as ephemeral with automatic deletion:

| Data Type | Current Storage | Current Retention | Issue |
|-----------|-----------------|-------------------|-------|
| Auth tokens | Cognito JWT | Session length | ✓ Appropriate |
| Chat messages | ElastiCache Redis (not durable) | Deleted with session | ✗ Violates Archives Act |
| Uploaded PDFs | S3 | 90 days | ✓ Appropriate for user data |
| RAG chunks | OpenSearch | Until doc deletion | ✓ Appropriate |
| Vector embeddings | OpenSearch | Until doc deletion | ✓ Appropriate |
| LLM responses | Not stored (streamed only) | Lost immediately | ✗ No audit trail |
| Retrieved context | Not stored | Lost immediately | ✗ Cannot reproduce decisions |
| Query metadata | CloudWatch Logs | 1 year | ✗ Insufficient for 7-year requirement |

### 1.2 Data Classification Framework

For ATO internal use, we must classify data according to both **business value** and **Commonwealth records obligations**:

#### Classification Matrix

| Classification | Data Types | Retention | Storage | Disposal Authority |
|----------------|------------|-----------|---------|-------------------|
| **Not a Record** | Auth tokens, temporary caches | Hours | Redis, Cognito | System auto-purge |
| **Administrative Record** | Query logs, access logs, system metrics | 7 years | CloudWatch → S3 Glacier | General Disposal Schedule (GDS) |
| **Business Record** | Chat conversation history, LLM responses, retrieved context | 7 years minimum | Aurora PostgreSQL | GDS + Records Authority |
| **User Data (Non-Record)** | Uploaded PDFs (user's own documents) | Until user deletion | S3 with soft-delete | User decision |
| **Derived Data** | RAG chunks, embeddings | Matches source | OpenSearch | Matches source |
| **Permanent Record** | Static KB (legislation, rulings) | Indefinite | OpenSearch | N/A (public documents) |

#### Record Status Determination

**Is conversation history a Commonwealth record?**

**Yes.** Under the Archives Act, a record is "any document made or received by a Commonwealth agency in the course of conducting its business." When an ATO officer uses this system to:

- Research penalty provisions for an audit decision
- Verify technical guidance for a taxpayer inquiry
- Extract facts from case law for a technical advice

The conversation history becomes evidence of the decision-making process and must be retained.

**Are uploaded user documents Commonwealth records?**

**It depends.**

| Scenario | Record Status | Retention |
|----------|---------------|-----------|
| ATO officer uploads taxpayer document for audit | Yes - part of audit file | Retained with audit record |
| ATO officer uploads their own research notes | Yes - created in course of business | 7 years |
| Taxpayer uploads document (if we ever support this) | No - not created by Commonwealth | Return to taxpayer |

**Current design assumption** that uploaded documents are temporary user data is **incorrect for ATO internal use**.

### 1.3 Storage Architecture by Data Type

```mermaid
graph TB
    subgraph "Ephemeral Layer - Not Records"
        REDIS[ElastiCache Redis<br/>Hot session state<br/>Auth tokens<br/>Query cache<br/>TTL: hours]
    end

    subgraph "Application Layer - User Data"
        S3_PDFS[S3 User Uploads<br/>Raw PDFs<br/>Chunks and extracted text<br/>Soft-delete enabled<br/>Retention: User decides]
        OPENSEARCH[OpenSearch<br/>Vector embeddings<br/>RAG chunks<br/>Metadata<br/>Retention: Matches source]
    end

    subgraph "Records Layer - Commonwealth Records"
        AURORA[Aurora PostgreSQL<br/>Conversation history<br/>Query traces LLM chain<br/>Audit logs<br/>Retention: 7 years minimum]
        GLACIER[S3 Glacier<br/>Archived conversations<br/>Historical query logs<br/>After 12 months of inactivity]
    end

    subgraph "Permanent Layer - Static KB"
        STATIC_OPENSEARCH[OpenSearch<br/>Citation Index<br/>Unified Legal Index<br/>Legislation and rulings<br/>Retention: Indefinite]
    end

    REDIS --> AURORA
    S3_PDFS --> OPENSEARCH
    AURORA --> GLACIER

    style REDIS fill:#FFF3E0
    style AURORA fill:#FFEBEE
    style GLACIER fill:#E3F2FD
    style STATIC_OPENSEARCH fill:#E8F5E9
```

### 1.4 LLM Response Chain Storage

**Requirement**: For auditability, we must store the complete decision chain:

```json
{
  "query_trace_id": "qt-20260407-001",
  "session_id": "sess-abc-123",
  "user_id": "ato-officer-456",
  "timestamp": "2026-04-07T10:30:00Z",
  "query": {
    "original": "What are the penalties for late BAS under s 288-95?",
    "rewritten": "penalty provisions late activity statement lodgment ITAA 1997 section 288-95",
    "detected_citations": ["s-288-95"]
  },
  "retrieval": {
    "citation_lookup": {
      "matched": "s-288-95",
      "title": "Failure to lodge return on time",
      "chunk_pointers": ["chunk-itaa-1997-s-288-95-001", "chunk-itaa-1997-s-288-95-002"]
    },
    "vector_search": {
      "query_embedding_id": "emb-xyz-789",
      "candidates": [
        {"chunk_id": "chunk-itaa-1997-s-288-95-001", "score": 0.95},
        {"chunk_id": "chunk-itaa-1997-s-288-95-002", "score": 0.89}
      ]
    },
    "bm25_search": {
      "candidates": [
        {"chunk_id": "chunk-tr-2022-1-005", "score": 8.5}
      ]
    },
    "reranking": {
      "method": "reciprocal_rank_fusion",
      "final_ranking": ["chunk-itaa-1997-s-288-95-001", "chunk-itaa-1997-s-288-95-002", "chunk-tr-2022-1-005"]
    }
  },
  "llm_generation": {
    "model": "claude-3-5-sonnet-20241022",
    "context_sent": "Full text of top 3 chunks...",
    "prompt_template": "ato_internal_tax_law_v2",
    "system_prompt": "You are an Australian tax law AI assistant...",
    "parameters": {
      "temperature": 0.3,
      "max_tokens": 2000
    },
    "response_full": "Under Section 288-95 of ITAA 1997...",
    "response_streamed": true,
    "token_count": 847,
    "duration_ms": 1500
  },
  "citations": [
    {"chunk_id": "chunk-itaa-1997-s-288-95-001", "text_snippet": "A penalty of 210 penalty units applies...", "position": [15, 47]}
  ],
  "user_feedback": {
    "helpful": null,
    "flags": []
  },
  "metadata": {
    "business_line": "compliance",
    "use_case": "audit_decision_support",
    "audit_reference": "AUD-2024-12345"
  }
}
```

**Storage location**: Aurora PostgreSQL `query_traces` table
**Retention**: 7 years minimum
**Access**: Restricted to records officer and data subject (ATO officer)

#### Storage Optimization: Chunk Pointers vs Full Context

**Question**: Should we store the full LLM context (chunk text) or just chunk IDs?

**Current Design**: `"context_sent": "Full text of top 3 chunks..."` stores complete chunk text.

**Cost Analysis** (100K queries/day, average 5KB context):

| Approach | Daily | Annual | 7-Year | Aurora Cost |
|----------|-------|--------|--------|-------------|
| Full context | 500MB | 180GB | 1.26TB | ~$1,530/year |
| Chunk IDs only | 5MB | 1.8GB | 12.6GB | ~$15/year |
| Chunk IDs + versioning | 10MB | 3.6GB | 25.2GB | ~$30/year |

**Optimization Proposal**: Store chunk IDs + version hash instead of full text. For audit reproduction:
1. Retrieve chunk IDs from query trace
2. Fetch current chunk content from OpenSearch
3. Compare version hash to detect changes
4. If version changed, flag for review

**Updated Schema**:
```sql
CREATE TABLE query_traces (
    query_trace_id UUID PRIMARY KEY,
    -- ... existing fields ...

    -- Instead of: llm_context_sent TEXT
    context_chunk_ids JSONB,          -- ["chunk-001", "chunk-002", "chunk-003"]
    context_chunk_versions JSONB,     -- {"chunk-001": "v1", "chunk-002": "v1"}
    context_hash BYTEA,               -- SHA-256 of concatenated chunks (for integrity)

    -- Full response is still stored
    llm_response_full TEXT NOT NULL
);
```

**Benefits**:
- 99% storage cost reduction
- No duplication (chunks already in OpenSearch)
- Reproducible with version tracking
- Can detect if source chunks changed (important for audits)

**Trade-offs**:
- Cannot reproduce EXACT LLM input if chunks are deleted/updated
- Requires OpenSearch to remain online for audit reproduction
- Version tracking adds complexity

**Recommendation**: Store chunk IDs + version hash. Store full LLM response but not full retrieved context.

### 1.5 Session State Storage - PostgreSQL vs Redis

#### The Debate

A common question in session management architecture is whether to use a specialized cache (Redis) or a relational database (PostgreSQL) for session state. For ATO internal use with Commonwealth records requirements, this decision has significant implications for reliability, compliance, and operational complexity.

#### Comparison: PostgreSQL vs Redis for Session State

| Aspect | PostgreSQL | Redis | Winner for ATO |
|--------|-----------|-------|-----------------|
| **Durability** | ACID guarantees, writes logged | AOF/Fork options, but primarily in-memory | PostgreSQL |
| **Read latency** | 1-5ms (with connection pooling) | <1ms (in-memory) | Redis |
| **Write latency** | 1-5ms | <1ms | Redis |
| **TTL support** | Requires cron/partitioning | Native, per-key | Redis |
| **Query capability** | Rich SQL, joins, aggregations | Key-value only | PostgreSQL |
| **Failure recovery** | Automatic, minimal data loss | Potential data loss on failover | PostgreSQL |
| **Operational complexity** | Single database | Additional service to manage | PostgreSQL |
| **Cost** | Included with records DB | Separate cluster (~$67/month) | PostgreSQL |
| **Audit integration** | Native (same tables) | Separate sync needed | PostgreSQL |
| **Cross-region replication** | Native Aurora feature | Requires Redis Cluster | PostgreSQL |
| **Max session size** | 1GB (TOAST) | 512MB (default) | PostgreSQL |

#### The Case for PostgreSQL-Only

**Argument**: PostgreSQL is sufficient and preferable for session state in ATO context.

1. **Simplified Architecture**
   - One database for all persistent data (sessions, conversations, query traces, documents)
   - Reduced operational overhead (no Redis cluster to patch, monitor, scale)
   - Fewer moving parts = fewer failure modes

2. **Durability by Default**
   - Session state survives Redis failures
   - Automatic failover in Aurora Multi-AZ
   - No risk of lost session data on cache eviction

3. **Rich Query Capability**
   - "Show me all active sessions for business_line='compliance'"
   - "Find sessions where query_trace includes 'penalty units'"
   - Native joins between sessions, conversations, and audit logs

4. **Unified Audit Trail**
   - All session activity in one place
   - No need to reconcile Redis logs with PostgreSQL records
   - Simplified compliance reporting

5. **Cost Efficiency**
   - No separate Redis cluster (~$67/month saved)
   - Aurora already provisioned for conversation history
   - Connection pooling keeps query latency acceptable

**Performance Consideration**:
- PostgreSQL read latency: 1-5ms with PgBouncer connection pooling
- For session operations: 1-5ms is imperceptible to users
- For query cache: Direct OpenSearch access avoids double-hop

#### The Case for Hybrid (Redis + PostgreSQL)

**Argument**: Redis provides performance benefits that justify the complexity.

1. **Sub-Millisecond Latency**
   - Redis: <1ms for session lookups
   - PostgreSQL: 1-5ms (even with pooling)
   - For high-frequency operations, difference compounds

2. **Native TTL**
   - Redis: Built-in expiration with `EXPIRE` command
   - PostgreSQL: Requires cron job or table partitioning
   - Simpler for truly ephemeral data

3. **Pub/Sub for WebSocket**
   - Native Redis pub/sub for real-time messaging
   - PostgreSQL NOTIFY/LISTEN available but less performant
   - Lower latency for broadcasting updates to connected users

4. **Memory-Optimized Data Structures**
   - Sorted sets for leaderboards, activity scoring
   - HyperLogLog for unique user counting
   - Bitmaps for feature flags

5. **Operational Isolation**
   - Cache failure doesn't impact primary database
   - Can scale cache independently from database
   - Cache can be flushed without affecting persistent data

#### PostgreSQL-Only Architecture (Recommended for ATO)

```mermaid
graph TB
    subgraph "Application Layer"
        APP[Application Pods]
        PGBOUNCER[PgBouncer<br/>Connection Pooler<br/>Session pooling]
    end

    subgraph "Data Layer"
        AURORA[Aurora PostgreSQL<br/>Sessions + Conversations<br/>Query Traces + Audit]

        subgraph "Session Tables"
            SESS[sessions<br/>Active session registry]
            CONV[conversation_messages<br/>Chat history]
            TRACE[query_traces<br/>Full audit chain]
            CACHE[query_cache<br/>Optional materialized cache]
        end
    end

    APP --> PGBOUNCER
    PGBOUNCER --> AURORA
    AURORA --> SESS
    AURORA --> CONV
    AURORA --> TRACE
    AURORA --> CACHE

    style APP fill:#E3F2FD
    style AURORA fill:#FFEBEE
    style CACHE fill:#FFF3E0
```

**How it works**:
1. Application connects via PgBouncer (session pooling mode)
2. Session lookups: `SELECT * FROM sessions WHERE session_id = ?` (1-5ms)
3. Session writes: `INSERT INTO sessions ...` with automatic TTL via partitioning
4. Query cache: Optional materialized view or cache table, bypassed if stale

**TTL Implementation in PostgreSQL**:
```sql
-- Native partitioning for automatic TTL cleanup
CREATE TABLE active_sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_data JSONB
) PARTITION BY RANGE (created_at);

-- Create partitions for time windows
CREATE TABLE sessions_2026_04 PARTITION OF active_sessions
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

CREATE TABLE sessions_2026_05 PARTITION OF active_sessions
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- Cron job drops old partitions (simulating TTL)
-- DROP TABLE sessions_2026_03;  -- Run monthly
```

#### Hybrid Architecture (If Performance Critical)

```mermaid
graph TB
    subgraph "Application Layer"
        APP[Application Pods]
    end

    subgraph "Cache Layer"
        REDIS[ElastiCache Redis<br/>Hot session registry<br/>Query cache<br/>WebSocket pub/sub<br/>TTL: hours]
    end

    subgraph "Data Layer"
        AURORA[Aurora PostgreSQL<br/>Persistent sessions<br/>Conversation history<br/>Query traces<br/>Retention: 7 years]
    end

    APP -->|Session lookup| REDIS
    APP -->|Cache miss| AURORA
    REDIS -->|Async writeback| AURORA

    AURORA -.Restore on failover.-> REDIS

    style APP fill:#E3F2FD
    style REDIS fill:#FFF3E0
    style AURORA fill:#FFEBEE
```

**How it works**:
1. **Write path**: Session data written to Redis first, async writeback to PostgreSQL
2. **Read path**: Redis lookup first, PostgreSQL on cache miss
3. **Failure recovery**: If Redis fails, fall back to PostgreSQL (slower but functional)
4. **Recovery**: After Redis restart, warm cache from active sessions in PostgreSQL

#### Recommendation: PostgreSQL-First for ATO

**For ATO internal use, PostgreSQL-only is recommended** because:

1. **Compliance**: Single source of truth simplifies audit and discovery
2. **Durability**: No risk of lost session data affecting records retention
3. **Simplicity**: One less service to operate, monitor, and secure
4. **Cost**: No additional Redis cluster (~$800/year savings)
5. **Performance**: 1-5ms latency is acceptable for session operations
6. **Feature set**: Rich queries enable better analytics and debugging

**When to add Redis**:
- If session operation latency exceeds 10ms at scale (>10K concurrent users)
- If pub/sub messaging volume exceeds PostgreSQL NOTIFY capabilities
- If advanced memory structures (sorted sets, hyperloglog) are needed
- **Decision**: Add Redis only when metrics show actual need, not preemptively

#### Real-Time Features and WebSocket Considerations

**Question**: Do we need Redis pub/sub for real-time messaging features?

**Potential Real-Time Features**:
| Feature | User Value | Pub/Sub Needed | PostgreSQL NOTIFY Sufficient |
|---------|------------|----------------|------------------------------|
| Streaming LLM responses | See answers generate | Optional | Yes - NOTIFY per token/chunk |
| Multi-user collaboration | Edit same session | Yes | Maybe - depends on concurrency |
| Typing indicators | See user activity | Optional | Yes |
| Live session updates | Real-time sync | Optional | Yes |

**Analysis**:
- PostgreSQL NOTIFY/LISTEN supports pub/sub messaging
- For moderate usage (<1000 concurrent connections), NOTIFY is sufficient
- NOTIFY overhead: ~1-2ms per message vs <1ms for Redis
- NOTIFY is simpler (no additional service)

**Recommendation**: Start with PostgreSQL NOTIFY for any real-time features. Add Redis only if:
- Concurrent connections exceed 10,000
- Message rate exceeds 10,000 messages/second
- Advanced pub/sub features needed (pattern matching, consumer groups)

**Hybrid Approach** (if needed later):
```
Application → Redis (pub/sub) → WebSocket clients
                ↓
           PostgreSQL (persistent)
```

For now, PostgreSQL-only supports all planned features without Redis complexity.

#### Implementation: PostgreSQL Session Store

```python
import asyncio
from datetime import datetime, timedelta
from asyncpg import Pool
from typing import Optional, Dict, Any

class PostgresSessionStore:
    """
    PostgreSQL-based session store with TTL support.
    Replaces Redis for session management in ATO context.
    """

    def __init__(self, pool: Pool, ttl_hours: int = 16):
        self.pool = pool
        self.ttl = timedelta(hours=ttl_hours)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID. Returns None if expired or not found."""
        query = """
            SELECT session_id, user_id, workspace_id, created_at,
                   last_active_at, status, session_data
            FROM sessions
            WHERE session_id = $1
              AND status = 'ACTIVE'
              AND last_active_at > NOW() - INTERVAL '16 hours'
            FOR UPDATE SKIP LOCKED
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, session_id)
            if row:
                # Update last_active on access
                await conn.execute(
                    "UPDATE sessions SET last_active_at = NOW() WHERE session_id = $1",
                    session_id
                )
                return dict(row)
            return None

    async def create_session(
        self,
        session_id: str,
        user_id: str,
        workspace_id: Optional[str] = None,
        session_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create new session."""
        query = """
            INSERT INTO sessions (session_id, user_id, workspace_id, session_data)
            VALUES ($1, $2, $3, $4)
            RETURNING *
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, session_id, user_id, workspace_id, session_data)
            return dict(row)

    async def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update session data."""
        set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates.keys()))
        query = f"""
            UPDATE sessions
            SET {set_clause}, last_active_at = NOW()
            WHERE session_id = $1 AND status = 'ACTIVE'
            RETURNING session_id
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, session_id, *updates.values())
            return result is not None

    async def delete_session(self, session_id: str, soft: bool = True) -> bool:
        """Delete or soft-delete session."""
        if soft:
            query = """
                UPDATE sessions
                SET status = 'DELETED',
                    deleted_at = NOW(),
                    retention_until = NOW() + INTERVAL '7 years'
                WHERE session_id = $1
                RETURNING session_id
            """
        else:
            query = "DELETE FROM sessions WHERE session_id = $1 RETURNING session_id"

        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query, session_id)
            return result is not None

    async def get_active_sessions(self, user_id: str) -> list[Dict[str, Any]]:
        """Get all active sessions for a user."""
        query = """
            SELECT * FROM sessions
            WHERE user_id = $1
              AND status = 'ACTIVE'
              AND last_active_at > NOW() - INTERVAL '16 hours'
            ORDER BY last_active_at DESC
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            return [dict(row) for row in rows]

    async def cleanup_expired_sessions(self) -> int:
        """Mark sessions as expired after 16 hours of inactivity. Run via cron."""
        query = """
            UPDATE sessions
            SET status = 'INACTIVE'
            WHERE status = 'ACTIVE'
              AND last_active_at < NOW() - INTERVAL '16 hours'
            RETURNING COUNT(*)
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(query)
            return result

# Performance optimization: PgBouncer configuration
# [session_bouncer is NOT used for this use case]
# Use transaction pooling for short-lived session operations:
"""
[databases]
session_db = host=aurora-cluster port=5432 dbname=case_assistant

[pgbouncer]
pool_mode = transaction
max_client_conn = 10000
default_pool_size = 50
server_lifetime = 3600
server_idle_timeout = 600
"""
```

#### Performance Benchmarks

Based on Aurora PostgreSQL r6g.large (2 vCPU, 16GB RAM):

| Operation | PostgreSQL (PgBouncer) | Redis | Notes |
|-----------|----------------------|-------|-------|
| **Session read** | 2-5ms | <1ms | Both imperceptible to users |
| **Session write** | 3-5ms | <1ms | Both async to user response |
| **1000 concurrent sessions** | Stable | Stable | No degradation |
| **10,000 concurrent sessions** | Stable | Stable | No degradation |
| **Connection overhead** | Minimal (pooling) | Minimal | |
| **Failover RTO** | <30s (Aurora auto) | <60s | Aurora faster |

**Conclusion**: For session operations specifically, PostgreSQL with connection pooling provides acceptable latency. The 2-5ms overhead is imperceptible to users and is outweighed by the benefits of durability, simplified architecture, and unified audit trail.

#### Updated Storage Recommendation

| Session Data | Storage | Rationale |
|--------------|---------|-----------|
| **Active session registry** | Aurora PostgreSQL | Single source of truth, audit-friendly |
| **Session metadata** | Aurora PostgreSQL | Part of records retention |
| **Connection state (WebSocket)** | In-memory only per pod | Ephemeral by design, reconnect restores from PostgreSQL |
| **Query cache** | Aurora PostgreSQL (cache table) or skip | Regenerate from OpenSearch if needed |
| **Conversation history** | Aurora PostgreSQL | Record retention requirement |
| **Query traces** | Aurora PostgreSQL | Audit trail requirement |

**Redis removed from architecture** for session management. May be added later for specific use cases (pub/sub messaging, advanced caching) if metrics justify the complexity.

---

## 2. Session Lifecycle and Retention Policy

### 2.1 Current Design vs Potential Records Requirements

**Current design** (from 04-session-lifecycle.md):
```
Session: Persists indefinitely while active
Documents: 7-day inactivity TTL, auto-deleted
Conversation: Persists after document deletion
Cleanup: After 30-day grace period
```

**Potential Issue**: If conversations are classified as Commonwealth records, auto-deletion after 30 days may conflict with records retention requirements.

### 2.2 Proposed Retention Policy

**Based on**:
- Archives Act 1983
- Attorney-General's Department Records Authorities
- ATO Records Management Policy

```mermaid
graph TB
    subgraph "Data Lifecycle by Type"
        direction TB

        subgraph "Not Records - Auto Delete"
            AUTH[Auth Tokens<br/>TTL: 4-16 hours]
            CACHE[Query Cache<br/>TTL: 1 hour]
            TEMP[Temporary Processing<br/>TTL: 24 hours]
        end

        subgraph "User Data - User Controlled"
            PDF[Uploaded PDFs<br/>Retention: Until user deletion<br/>Soft-delete: 90-day buffer]
            CHUNK[RAG Chunks<br/>Retention: Matches PDF]
        end

        subgraph "Administrative Records - 7 Years"
            LOGS[Access Logs<br/>Query Metadata<br/>Retention: 7 years]
            AUDIT[Audit Trail<br/>System Events<br/>Retention: 7 years]
        end

        subgraph "Business Records - 7 Years Minimum"
            CONV[Conversation History<br/>LLM Responses<br/>Retention: 7 years]
            TRACE[Query Traces<br/>Retrieval Chain<br/>Retention: 7 years]
        end

        subgraph "Archival - Transfer to NAA after 7 years"
            ARCHIVE[Archived Sessions<br/>Historical Analysis<br/>Research Value]
        end

        AUTH --> AUTO[Automatic Deletion]
        CACHE --> AUTO
        TEMP --> AUTO

        PDF --> USER[User Decision or<br/>Records Authority]
        CHUNK --> USER

        LOGS --> GDS[General Disposal Schedule]
        AUDIT --> GDS

        CONV --> GDS
        TRACE --> GDS

        GDS --> ARCHIVE
    end

    style AUTH fill:#FFF3E0
    style CONV fill:#FFEBEE
    style TRACE fill:#FFEBEE
    style ARCHIVE fill:#E3F2FD
```

### 2.3 Soft-Delete Strategy

**Current design**: Hard-delete (remove from S3, OpenSearch)

**Recommendation**: Soft-delete with retention tracking

```sql
-- Soft-delete pattern for all user-accessible data
CREATE TABLE conversation_messages (
    message_id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    user_id UUID NOT NULL,
    content TEXT NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    created_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    retention_until TIMESTAMPTZ NOT NULL,
    deletion_reason VARCHAR(100),

    -- RLS policy prevents access to deleted messages from application
    -- Batch jobs can still access for archival
);

CREATE INDEX idx_messages_user_session ON conversation_messages(user_id, session_id);
CREATE INDEX idx_messages_retention ON conversation_messages(retention_until) WHERE deleted_at IS NOT NULL;

-- Soft-delete function
CREATE OR REPLACE FUNCTION soft_delete_message(p_message_id UUID, p_reason VARCHAR)
RETURNS void AS $$
BEGIN
    UPDATE conversation_messages
    SET
        deleted_at = NOW(),
        retention_until = NOW() + INTERVAL '7 years',
        deletion_reason = p_reason
    WHERE message_id = p_message_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Benefits**:
- User can "delete" sessions (appears gone from UI)
- Data retained for 7 years for compliance
- Can recover from accidental deletion
- Audit trail of what was deleted and why

**Hard-delete only**:
- After 7-year retention period expires
- With records management authority approval
- Documented disposal certificate

### 2.4 Session Expiry Triggers

| Trigger | Action | Data Impact |
|---------|--------|-------------|
| **Token expiry** (4-16 hours) | User must re-authenticate | No data deletion |
| **Inactivity timeout** (7 days) | Mark session inactive | No data deletion |
| **User logout** | Clear auth tokens | No data deletion |
| **User deletes session** | Soft-delete conversation | Data retained 7 years |
| **7-year retention expiry** | Archive to Glacier / Destroy | Per records authority |
| **Records authority** | Specific disposal order | Immediate execution |

**Key principle**: **User actions never trigger permanent data deletion.** Only retention policies and records authority can destroy data.

### 2.5 Archival Strategy

**Phase 1: Active (0-12 months)**
- Aurora PostgreSQL (hot)
- OpenSearch (vectors + chunks)
- S3 Standard (PDFs)
- Fast query access, full functionality

**Phase 2: Warm (12 months - 7 years)**
- Aurora PostgreSQL (warm storage)
- S3 Standard-IA (infrequent access)
- Vector embeddings deleted (cost optimization)
- Conversation history still searchable

**Phase 3: Cold (7+ years)**
- S3 Glacier Deep Archive
- Export to National Archives if required
- Retrieval: 12-48 hours

**Cost projection** (10,000 users, 100K sessions/year):

| Phase | Storage | Monthly Cost | Annual Cost |
|-------|---------|--------------|-------------|
| Active | Aurora r6g.large, S3 Standard | ~$800 | ~$9,600 |
| Warm | Aurora r6g.large, S3 Standard-IA | ~$400 | ~$4,800 |
| Cold | S3 Glacier Deep Archive | ~$50 | ~$600 |
| **Total** | | ~$1,250 | ~$15,000 |

**Per-session cost**: ~$0.15 for 7-year retention

### 2.6 Records Management Engagement

**Required actions**:
1. **Classify data** under ATO Records Authority
   - What functions does the system support? (audit, technical advice, policy research)
   - What records are created? (conversations, queries, decisions)
   - What retention applies? (refer to GDS for functional records)

2. **Submit Records Authority** to National Archives
   - Describe system purpose and data types
   - Justify 7-year retention (standard for administrative records)
   - Obtain authority for disposal

3. **Implement Disposal Schedule**
   - Automated soft-delete at 7 years
   - Annual disposal report to records team
   - Certificates of destruction

4. **Audit Trail Requirements**
   - Who accessed what data when
   - Who deleted what data when
   - Chain of custody for exported records

### 2.7 Tiered Retention by Conversation Type (Discussion)

**Question**: Should all conversations have 7-year retention, or should retention vary by use case?

**Current Design**: Uniform 7-year retention for all conversations and query traces.

**Critique**: Not all ATO officer interactions create Commonwealth records of equal value. Storing 7 years of "how do I..." queries creates unnecessary cost and privacy risk.

#### Proposed Tiered Retention Model

| Conversation Type | Example | Proposed Retention | Rationale | GDS Reference |
|-------------------|---------|-------------------|-----------|---------------|
| **Formal audit decision support** | "What penalties apply to case AUD-2024-12345?" | 7 years | Evidence of decision-making | GDS: Audit records |
| **Technical advice research** | "Explain s 288-95 for this taxpayer scenario" | 7 years | Part of advice record | GDS: Technical advice |
| **Policy/legislation research** | "What does the latest TR say about FBT?" | 3 years | Administrative use | GDS: Administrative records |
| **Educational/learning queries** | "How do I calculate the small business CGT discount?" | 1 year | Training, not business record | GDS: Training materials |
| **Test/exploration queries** | User testing system features | 90 days | Not substantive business | N/A |

#### Implementation Considerations

**User Experience**:
- At session creation, prompt user to select conversation purpose
- Privacy notice: "Conversations supporting audit decisions are retained for 7 years. Learning conversations are retained for 1 year."
- Allow user to change classification during session

**Technical Implementation**:
```sql
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    conversation_type VARCHAR(50) NOT NULL, -- 'AUDIT_DECISION', 'TECHNICAL_ADVICE', 'LEARNING', 'TEST'
    retention_years INTEGER NOT NULL DEFAULT 7,
    -- ... other fields
);

CREATE INDEX idx_sessions_retention ON sessions(retention_until, conversation_type);
```

**Benefits**:
- Reduced storage costs (~30-40% reduction if 50% of conversations are learning/test)
- Improved privacy (less data retained unnecessarily)
- More accurate records classification
- Better user trust (transparent about retention)

**Challenges**:
- Users may misclassify to avoid retention
- Requires Records Management approval for tiered approach
- Complex to implement and audit
- What if conversation changes type mid-session?

**Recommendation**: Discuss tiered retention with Records Management. If approved, implement as Phase 2 feature. Start with uniform 7-year retention for compliance.

---

## 3. RBAC and Fine-Grained Access Control

**Note**: Sections 3.6-3.8 (Encryption, DLQ Alerting, Observability) incorporate patterns from the AI Coach reference architecture, including envelope encryption, SNS-based alerting with PagerDuty/Datadog/Slack integration, and LangFuse self-hosted tracing with production redaction.

### 3.1 Current Design Gaps

**Current state**: Infrastructure-level security only

```yaml
# What we have:
IRSA: Pod IAM roles for service-to-service access
Security Groups: Network-level restrictions
Cognito: User authentication

# What we DON'T have:
Row-Level Security: Database-level access control
Application RBAC: Role-based permissions
Data isolation: User/user data segregation
```

**Risk**: A single missed `WHERE user_id = ?` clause exposes one user's data to another. LLM-generated queries cannot be trusted to include proper filters.

### 3.2 Proposed RBAC Model

#### Role Definitions

| Role | Description | Permissions | Use Case |
|------|-------------|-------------|----------|
| **STANDARD_USER** | Regular ATO officer | Create/read/delete own sessions, upload documents, query | Daily use by auditors, technical advisors |
| **TEAM_LEAD** | Team supervisor | Read-only access to team members' sessions | QA, training, oversight |
| **BUSINESS_ANALYST** | Cross-team analytics | Aggregated query stats, no PII | Usage analysis, system improvement |
| **RECORDS_OFFICER** | Records management | Read all soft-deleted data, manage archival | Compliance, legal discovery |
| **ADMIN** | System administration | Full access with comprehensive audit logging | Support, troubleshooting |
| **SERVICE_ACCOUNT** | Background jobs | Limited scoped permissions | Cleanup, archival, batch processing |

#### Permission Matrix

| Resource | STANDARD_USER | TEAM_LEAD | BUSINESS_ANALYST | RECORDS_OFFICER | ADMIN | SERVICE_ACCOUNT |
|----------|---------------|-----------|------------------|-----------------|-------|------------------|
| Own sessions | RW | R | R | R | RW | - |
| Team sessions | - | R | - | R | RW | - |
| All sessions | - | - | Aggregates only | R | RW | - |
| Soft-deleted data | - | - | - | R | RW | R (archival only) |
| System config | - | - | - | - | RW | - |
| Audit logs | R (own) | R (team) | - | R | RW | R (cleanup only) |

### 3.3 Row-Level Security Implementation

#### Best Practices Summary

Based on research from AWS Database Blog, PostgreSQL documentation, and SaaS Factory patterns:

| Best Practice | Description | Why It Matters |
|---------------|-------------|----------------|
| **SET app.user_id from JWT** | Set PostgreSQL session variable on every request | RLS policies use this variable; cannot be bypassed by application code |
| **Don't connect as table owner** | Application uses non-owner role | Table owners bypass RLS by default; use `FORCE ROW LEVEL SECURITY` |
| **Separate RLS roles** | Different roles per access level (standard_user, team_lead, admin) | Granular permission control at database level |
| **Policy-specific policies** | Separate policies for SELECT vs INSERT/UPDATE/DELETE | Different rules for reading vs modifying data |
| **Test RLS thoroughly** | Verify policies work for complex queries, views, functions | Policies can have unintended effects on joins and subqueries |
| **FORCE ROW LEVEL SECURITY** | Apply to sensitive tables | Even table owners are subject to RLS |
| **No application-level bypass** | Never use `SET row_security = off` | Would defeat the entire security model |
| **Log RLS violations** | Monitor for failed RLS policy checks | Detect potential attacks or misconfiguration |

#### PostgreSQL RLS Pattern

Based on AWS SaaS Factory reference: [aws-samples/aws-saas-factory-postgresql-rls](https://github.com/aws-samples/aws-saas-factory-postgresql-rls)

```sql
-- Enable RLS on all user-data tables
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploaded_documents ENABLE ROW LEVEL SECURITY;

-- Set user context from JWT
-- Called by application on every request
CREATE OR REPLACE FUNCTION set_app_user_id(p_user_id UUID, p_role VARCHAR)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.user_id', p_user_id::text, false);
    PERFORM set_config('app.user_role', p_role, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RLS Policy: Standard users see only their own data
CREATE POLICY user_isolation ON conversation_messages
FOR ALL
TO standard_user_role
USING (user_id = CAST(current_setting('app.user_id') AS UUID));

-- RLS Policy: Team leads see their team's data
CREATE POLICY team_access ON conversation_messages
FOR SELECT
TO team_lead_role
USING (
    user_id IN (
        SELECT member_user_id
        FROM team_members
        WHERE team_id = (
            SELECT team_id
            FROM users
            WHERE user_id = CAST(current_setting('app.user_id') AS UUID)
        )
    )
);

-- RLS Policy: Records officers see everything including soft-deleted
CREATE POLICY records_officer_full_access ON conversation_messages
FOR ALL
TO records_officer_role
USING (true);  -- No filtering

-- RLS Policy: Service accounts have no access by default
CREATE POLICY service_account_deny ON conversation_messages
FOR ALL
TO service_account_role
USING (false);  -- Explicit deny
```

#### Application Integration

```python
# Middleware: Extract user from JWT and set PostgreSQL context
async def set_db_context(request: Request, call_next):
    """
    Extract user_id and role from JWT and set PostgreSQL session variables.
    RLS policies automatically filter all subsequent queries.
    """
    jwt_token = await extract_jwt_token(request)
    payload = decode_jwt(jwt_token)

    user_id = payload['sub']  # User's UUID
    role = payload['role']    # 'STANDARD_USER', 'TEAM_LEAD', etc.

    # Set PostgreSQL session variables for RLS
    await db.execute(
        "SELECT set_app_user_id($1, $2)",
        user_id, role
    )

    # RLS now automatically filters all queries in this request
    response = await call_next(request)
    return response

# Example: RLS automatically injects WHERE clause
# No need to manually add "WHERE user_id = current_user"
async def get_user_sessions():
    # RLS policy automatically adds: WHERE user_id = <current_user>
    return await db.query("SELECT * FROM sessions")
```

#### Defense in Depth

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Network Security                                    │
│ • Security Groups restrict database access                  │
│ • Private subnets, no direct internet access                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Authentication                                      │
│ • Cognito validates JWT token                                │
│ • Token contains user_id, role, team_id                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Application Authorization                           │
│ • Endpoint-level checks (@require_role('ADMIN'))             │
│ • Business logic validation                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Database-Level Access Control (RLS)                │
│ • PostgreSQL policies enforce per-user data isolation        │
│ • Cannot be bypassed by application bugs or LLM queries      │
│ • SET app.user_id passed from JWT                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: Audit Logging                                      │
│ • All queries logged with user_id context                   │
│ • Alert on suspicious access patterns                        │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 Project/Team-Level Access

**Use case**: ATO officers collaborate on audits or technical advice. Should they share sessions?

**Recommendation**: Implement workspaces with scoped access

```sql
-- Workspaces for collaborative sessions
CREATE TABLE workspaces (
    workspace_id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    business_line VARCHAR(100),
    created_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE workspace_members (
    workspace_id UUID REFERENCES workspaces(workspace_id),
    user_id UUID REFERENCES users(user_id),
    role VARCHAR(50), -- 'OWNER', 'EDITOR', 'VIEWER'
    PRIMARY KEY (workspace_id, user_id)
);

-- Sessions belong to workspaces
ALTER TABLE sessions ADD COLUMN workspace_id UUID REFERENCES workspaces(workspace_id);

-- RLS Policy: Workspace members can see workspace sessions
CREATE POLICY workspace_access ON sessions
FOR SELECT
TO standard_user_role
USING (
    -- Own sessions always visible
    user_id = CAST(current_setting('app.user_id') AS UUID)
    OR
    -- Workspace sessions where user is a member
    workspace_id IN (
        SELECT workspace_id
        FROM workspace_members
        WHERE user_id = CAST(current_setting('app.user_id') AS UUID)
    )
);
```

**User experience**:
- Default: Personal sessions (only creator can access)
- Optional: Create workspace, invite team members
- Workspace sessions: All members can view and contribute
- Audit trail: Who accessed what workspace session when

### 3.5 Query-Time Isolation for RAG

**Critical question**: Can a user's RAG query accidentally retrieve another user's uploaded document chunks?

**Current design**: Every chunk has `user_id` field. Query-time filter: `tenant_id = static OR user_id = 123`

**Risk**: If the filter is omitted from the OpenSearch query, all users' chunks are returned.

**Mitigation**:

```python
# OpenSearch tenant-aware queries
def search_user_documents(user_id: UUID, query: str):
    """
    Enforce tenant isolation at the query builder level.
    Cannot be bypassed by LLM-generated queries.
    """
    # Build filter with mandatory user_id
    filters = {
        "bool": {
            "should": [
                {"term": {"tenant_id": "static"}},  # Public Static KB
                {"term": {"user_id": str(user_id)}}  # User's own uploads
            ],
            "minimum_should_match": 1
        }
    }

    # Combine with user query (LLM cannot override the filter)
    search_body = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"text": query}}  # User's query
                ],
                "filter": filters  # Mandatory isolation
            }
        }
    }

    return opensearch.search(index="unified-legal-index", body=search_body)
```

**Defense in depth**:
1. **Application level**: Query builder enforces filter
2. **OpenSearch level**: Index-level access control (OpenSearch Security plugin)
3. **Network level**: Private VPC, no direct OpenSearch access from internet

### 3.6 End-to-End Encryption Specification

**Based on AI Coach pattern**: Comprehensive encryption strategy covering data in transit, at rest, and application layer.

#### Encryption Layers

| Layer | Mechanism | Specification |
|-------|-----------|---------------|
| **In-transit (all hops)** | TLS 1.3 | TLS 1.3 minimum for all external connections |
| **Internal service-to-service** | mTLS via App Mesh | mTLS between internal services using AWS App Mesh |
| **RDS PostgreSQL at rest** | AES-256 + KMS CMK per account | AWS KMS Customer Managed Key (CMK) per account |
| **S3 documents** | SSE-KMS | Same CMK as RDS; bucket policy denies unencrypted PUTs |
| **Session messages (JSONB)** | Envelope encryption | Per-session DEK (AES-256-GCM) wrapped by KMS CMK |
| **Document chunk content** | Per-project DEK | Per-project DEK wrapped by KMS CMK |
| **Secrets (DB passwords, API keys)** | AWS Secrets Manager + KMS | Injected at ECS task start, never in code |

#### Envelope Encryption Implementation

**Rationale**: Content unreadable without KMS access, providing defense-in-depth even if database is compromised.

```sql
-- Encryption metadata table
CREATE TABLE encryption_keys (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL,
    encrypted_key BYTEA NOT NULL, -- DEK encrypted by KMS CMK
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days')
);

-- Session messages with envelope encryption reference
CREATE TABLE conversation_messages_enveloped (
    message_id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    key_id UUID REFERENCES encryption_keys(key_id),
    encrypted_content BYTEA NOT NULL, -- AES-256-GCM encrypted
    nonce BYTEA NOT NULL,
    auth_tag BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### S3 Bucket Policy (Enforce Encryption)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedObjectUploads",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::case-assistant-documents/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms"
        }
      }
    }
  ]
}
```

---

### 3.6.1 Per-Account Customer Managed Keys (CMK)

**Enhanced Security Model** - Based on AI Coach pattern:

For additional security isolation, use AWS KMS Customer Managed Keys (CMK) per account:

| Layer | Key Type | Scope | Benefit |
|-------|----------|-------|---------|
| **Aurora PostgreSQL** | Per-account CMK | All data in account's tables | Separate key, revocable per account |
| **S3 documents** | Per-account CMK | Document bucket for account | Account-level encryption, separate access policies |
| **Session messages** | Per-session DEK | Wrapped by account CMK | Forward secrecy, compromise limits to one session |

**Benefits**:
- **Granular access control**: Compromised key affects only one account
- **Audit trail**: Each KMS decrypt operation is logged in CloudTrail
- **Compliance**: Customer-managed keys provide encryption sovereignty
- **Revocation**: Keys can be disabled or rotated per account

**Implementation Considerations**:
- Cost: KMS CMK has monthly cost (~$1/month per key)
- Key management: Need to provision key on account creation
- Rotation: Automatic key rotation every 1-3 years
- Performance: KMS decrypt adds ~5-10ms latency per operation

**Recommendation**: Per-account CMK is **optional** for ATO internal use but recommended if:
- System expands to external users
- Compliance requires customer-managed encryption keys
- Legal discovery requires key-level access controls

---

### 3.7 Dead Letter Queue and Alerting Strategy

**Based on AI Coach pattern**: Automated DLQ handling with multi-channel alerting.

#### DLQ Architecture

```mermaid
graph LR
    subgraph "Failure Detection"
        FAIL[Operation Fails<br/>3 retries exhausted]
        SQS[SQS Dead Letter Queue<br/>Failed messages queued]
    end

    subgraph "Monitoring"
        ALARM[CloudWatch Alarm<br/>DLQ depth > 0 for 1min]
    end

    subgraph "Alert Channels"
        PD[PagerDuty<br/>P3 incident business hours<br/>P2 critical incidents]
        DD[Datadog<br/>Metrics + correlations<br/>Unified dashboard]
        SL[Slack<br/>#case-assistant-alerts<br/>Engineering team]
    end

    subgraph "Recovery"
        RETRY1[Chunk Reprocessor<br/>Lambda/K8s Job<br/>Retry from DLQ]
        MANUAL[Manual Review Table<br/>After 3rd failure]
        JIRA[JIRA Auto-ticket<br/>Priority based on severity]
    end

    FAIL --> SQS
    SQS --> ALARM
    ALARM --> PD
    ALARM --> DD
    ALARM --> SL

    SQS --> RETRY1
    RETRY1 -->|Failure 2| RETRY1
    RETRY1 -->|Failure 3| MANUAL
    MANUAL --> JIRA

    style FAIL fill:#FFCDD2
    style SQS fill:#FFF3E0
    style MANUAL fill:#FFE0B2
    style JIRA fill:#E1F5FE
```

#### Alert Thresholds and Escalation

| Metric | Threshold | Alert | Escalation |
|--------|-----------|-------|------------|
| **Chunk DLQ depth** | > 0 for 1 min | PagerDuty P3 + Datadog + Slack | On-call engineer |
| **Embedding API error rate** | > 5% in 5 min | PagerDuty P2 + Datadog + Slack | Senior engineer |
| **LLM call DLQ depth** | > 0 for 1 min | PagerDuty P2 + Datadog + Slack | Senior engineer |
| **Embedding latency p99** | > 5s for 5 min | Datadog + Slack | Performance review |
| **Query trace storage fails** | > 1% in 5 min | PagerDuty P2 + Datadog | Data engineering |
| **RLS policy violation** | Any occurrence | PagerDuty P1 + Slack | Security incident |

#### Manual Review and Recovery

**Manual Review Table**:
```sql
CREATE TABLE manual_review_queue (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    failure_type VARCHAR(100) NOT NULL,
    account_id UUID,
    user_id UUID,
    chunk_id UUID,
    document_id UUID,
    error_message TEXT,
    retry_count INTEGER NOT NULL,
    failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'PENDING',  -- PENDING, IN_REVIEW, RESOLVED, IGNORED
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    resolution TEXT,
    jira_ticket_id VARCHAR(100)
);
```

**Recovery Workflow**:
1. **Failure 1-2**: Automatic retry with exponential backoff
2. **Failure 3**: Move to manual review table, create JIRA ticket
3. **JIRA priority**: Based on failure type and business impact
4. **Resolution options**: Retry manually, mark as ignored, escalate

#### Composite Monitoring (Datadog)

**Correlation Examples** (for faster root-cause analysis):
- Chunk failures + **ECS CPU saturation** = Infrastructure issue
- Chunk failures + **Cohere API error rate** = Third-party API issue
- Chunk failures + **MSK consumer lag** = Streaming pipeline issue
- LLM failures + **Bedrock error rate** = AWS service issue
- Query trace failures + **Aurora latency** = Database issue

**Datadog Composite Monitors**:

**Datadog Dashboard**:
```yaml
dashboard:
  title: Case Assistant Operations
  templates:
    - name: Chunk Failure Rate
      query: rate(sum:case_assistant.chunk.failed{!retry:yes}) by {failure_type}
      thresholds: [avg: 5, max: 10]
    - name: LLM Error Rate
      query: rate(sum:case_assistant.llm.error) by {model, error_type}
      thresholds: [avg: 1, max: 5]
    - name: RLS Violations
      query: sum:case_assistant.rls.violation)
      thresholds: [max: 0]  # Any violation is critical
```

---

### 3.8 Observability with Privacy-Preserving Tracing

**Based on AI Coach LangFuse pattern**: Self-hosted tracing with production redaction.

#### LangFuse Architecture

| Component | Deployment | Data Retention | Privacy |
|-----------|------------|-----------------|---------|
| **LangFuse** | ECS Fargate (self-hosted) | 30 days | Redacted at source |
| **Trace capture** | One trace per user turn | 30 days | Content replaced with [REDACTED] |
| **Metadata retained** | session_id, account_id, latency, model | 30 days | No PII or content |

#### Production Redaction Strategy

```python
def redact_trace_for_langfuse(trace: dict) -> dict:
    """
    Redact sensitive content before sending to LangFuse.
    Only metadata is retained for observability.
    """
    redacted = trace.copy()

    # Redact user messages
    if redacted.get("user_message"):
        redacted["user_message"] = "[REDACTED]"

    # Redact assistant responses
    if redacted.get("assistant_message"):
        redacted["assistant_message"] = "[REDACTED]"

    # Redact retrieved chunks
    if redacted.get("retrieved_chunks"):
        for chunk in redacted["retrieved_chunks"]:
            chunk["content"] = "[REDACTED]"
            chunk["text"] = "[REDACTED]"

    # Retain only metadata for observability
    redacted["metadata_only"] = True

    return redacted
```

#### Trace Schema (Redacted)

```json
{
  "trace_id": "trace-20260407-001",
  "session_id": "sess-abc-123",
  "account_id": "account-xyz",
  "user_id": "user-123",
  "timestamp": "2026-04-07T10:30:00Z",

  "spans": [
    {
      "name": "content_safety_check",
      "status": "success",
      "latency_ms": 45,
      "model": "comprehend",
      "input": "[REDACTED]",
      "output": "[REDACTED]"
    },
    {
      "name": "rag_retrieval",
      "status": "success",
      "latency_ms": 350,
      "chunks_retrieved": 5,
      "retrieved_chunks": [
        {"chunk_id": "chunk-001", "content": "[REDACTED]"},
        {"chunk_id": "chunk-002", "content": "[REDACTED]"}
      ]
    },
    {
      "name": "llm_generation",
      "status": "success",
      "latency_ms": 1500,
      "model": "claude-3-5-sonnet",
      "input_tokens": 450,
      "output_tokens": 847,
      "input": "[REDACTED]",
      "output": "[REDACTED]"
    }
  ],

  "metadata_only": true
}
```

#### Observability Stack

```mermaid
graph TB
    subgraph "Application"
        API[Coaching API]
        RAG[RAG Service]
        LLM[LLM Proxy]
    end

    subgraph "Tracing Layer"
        REDACT[Redaction Middleware<br/>Content → [REDACTED]]
        LANGFUSE[LangFuse Self-Hosted<br/>ECS Fargate]
    end

    subgraph "Metrics Layer"
        CLOUDWATCH[CloudWatch Metrics<br/>Latency, error rates]
        DATADOG[Datadog<br/>Dashboards, alerts]
    end

    API --> REDACT
    RAG --> REDACT
    LLM --> REDACT

    REDACT --> LANGFUSE
    REDACT --> CLOUDWATCH
    REDACT --> DATADOG

    style REDACT fill:#FFEBEE
    style LANGFUSE fill:#E3F2FD
    style CLOUDWATCH fill:#FFF3E0
    style DATADOG fill:#FFF59D
```

#### LangFuse Self-Hosting Benefits

| Benefit | Description |
|---------|-------------|
| **Data sovereignty** | All trace data stays in ATO VPC |
| **Cost control** | No external SaaS subscription |
| **Privacy** | Redaction at source, no third-party access |
| **Integration** | Correlate with CloudWatch and Datadog |
| **Retention control** | Delete data anytime, no vendor lock-in |

#### Alternative: OpenTelemetry + CloudWatch

If LangFuse self-hosting is too complex, use OpenTelemetry with CloudWatch:

```python
from opentelemetry import trace
from opentelemetry.exporter.cloudwatch import CloudWatchSpanExporter

# Configure exporter
exporter = CloudWatchSpanExporter()

# Tracing with automatic redaction
@tracer
async def process_query(query: str):
    trace.get_current_span().set_attribute("user_query", "[REDACTED]")
    trace.get_current_span().set_attribute("account_id", account_id)
    # ... process query
```

---

### 3.9 Vector Database Access Control for RAG

**Critical Challenge**: In RAG applications, the vector database is a potential data leak point. Unlike PostgreSQL where RLS filters rows automatically, vector databases require explicit metadata filtering at query time.

#### Best Practices for RAG Data Isolation

| Practice | Description | Implementation |
|----------|-------------|----------------|
| **Tenant ID in metadata** | Every chunk must include tenant/user_id | Add `user_id` field to all chunk documents |
| **Mandatory query filters** | Filter applied before vector search | Use `filter` clause in OpenSearch/k-NN queries |
| **Never filter after retrieval** | Filter at search time, not after | Prevents data leakage in result set |
| **Separate indices (optional)** | Per-user or per-tenant indices | Useful for highly sensitive data |
| **Index-level access control** | OpenSearch Security plugin | Encrypt data at rest, restrict index access |
| **Audit all queries** | Log who searched for what | Include user_id, timestamp, results count |

#### OpenSearch Implementation

```python
def search_with_isolation(
    query: str,
    user_id: str,
    opensearch_client,
    top_k: int = 10
) -> list[dict]:
    """
    Search with mandatory tenant isolation.
    The filter is applied BEFORE vector search, not after.
    """
    # Generate query embedding
    query_embedding = bedrock.embed_query(query)

    # Build search with MANDATORY filter
    search_body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "knn": {
                            "embedding": {
                                "vector": query_embedding,
                                "k": top_k
                            }
                        }
                    }
                ],
                # MANDATORY: Filter applied before search
                "filter": {
                    "bool": {
                        "should": [
                            {"term": {"tenant_id": "static"}},  # Public Static KB
                            {"term": {"user_id": user_id}}       # User's own uploads
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
        },
        "size": top_k
    }

    results = opensearch_client.search(
        index="unified-legal-index",
        body=search_body
    )

    return results["hits"]["hits"]
```

**Key point**: The filter is inside the `bool.filter` clause, which means OpenSearch applies it **during** the k-NN search, not after. Rows that don't match are never considered.

#### OpenSearch Security Plugin (Defense in Depth)

For additional security, consider the OpenSearch Security plugin:

```yaml
# OpenSearch Security configuration
security_config:
  dynamic:
    filtered_fields_mode: "merge"
    http:
      anonymous_auth_enabled: false
      xff:
        enabled: true
        internalProxies: "10.0.0.0/8"  # VPC CIDR
        remoteProxies: ""

    roles_mapping:
      all_access:
        reserved: true
        backend_roles:
          - admin

      standard_user_role:
        users:
          - "*"
        cluster_permissions:
          - "cluster_composite_ops"
        index_permissions:
          - index_patterns:
              - "unified-legal-index"
            allowed_actions:
              - "read"
              - "search"
          - index_patterns:
              - "user-document-metadata-*"
            fls:
              - "user_id=${user_name}"  # Field-level security
            allowed_actions:
              - "read"
```

**Benefits**:
- Encrypts data at rest with per-user keys
- Index-level access control
- Fine-grained permissions per index
- Audit logging for all searches

#### RAG Security Checklist

| ✅ | Check | Risk if Missing |
|----|-------|-----------------|
| ✅ | Every chunk has `user_id` metadata | Cross-user data retrieval |
| ✅ | Query builder enforces filter filter | LLM-generated queries bypass security |
| ✅ | Filter applied before k-NN search | Data appears in search results |
| ✅ | Unit tests for cross-tenant access | Undetected security bypass |
| ✅ | Integration tests for isolation | Production security gaps |
| ✅ | Penetration testing for data leaks | Public exposure of user data |
| ✅ | Audit logging for all queries | No forensic trail |
| ✅ | Alerting on unusual query patterns | Data exfiltration attacks |

#### Testing RAG Isolation

```python
def test_rag_isolation():
    """
    Verify that User A cannot retrieve User B's documents.
    """
    # Setup: User A and User B upload different documents
    user_a = create_user("user-a")
    user_b = create_user("user-b")

    doc_a = upload_document(user_a, "User A's private document")
    doc_b = upload_document(user_b, "User B's private document")

    # Wait for ingestion
    wait_for_ingestion(doc_a)
    wait_for_ingestion(doc_b)

    # Test: User A searches for content from User B's document
    results_a = search_with_isolation(
        query="content that only exists in User B's document",
        user_id=user_a.id
    )

    # Assert: User A should see NO results from User B's document
    for result in results_a:
        assert result["user_id"] == user_a.id, \
            f"Cross-tenant leak: {result['chunk_id']} belongs to {result['user_id']}"
```

---

### 3.10 Kafka & Outbox Pattern for Async Events

**Based on AI Coach pattern**: Event-driven architecture with outbox pattern for reliable event delivery.

#### Architecture Overview

```mermaid
graph LR
    subgraph "Application Layer"
        API[Case Assistant API]
        DB[(PostgreSQL)]
    end

    subgraph "Outbox Pattern"
        OUTBOX[Outbox Table<br/>Atomic write with turn]
        DEBEZIUM[Debezium CDC<br/>Tails WAL]
    end

    subgraph "Event Streaming"
        KAFKA[Amazon MSK / Kafka<br/>Event streaming]
    end

    subgraph "Consumers"
        ANALYTICS[Analytics Pipeline<br/>Snowflake / S3]
        ALERTING[Alerting & Monitoring<br/>Datadog / Slack]
        ARCHIVAL[Archival<br/>S3 Glacier]
    end

    API --> DB
    API --> OUTBOX
    OUTBOX --> DEBEZIUM
    DEBEZIUM --> KAFKA
    KAFKA --> ANALYTICS
    KAFKA --> ALERTING
    KAFKA --> ARCHIVAL

    style OUTBOX fill:#FFF3E0
    style DEBEZIUM fill:#E8F5E9
    style KAFKA fill:#FFCC80
```

#### Outbox Pattern Implementation

**Problem**: Need reliable event delivery without distributed transactions across PostgreSQL, S3, OpenSearch, and analytics.

**Solution**: Write events atomically to outbox table in same transaction as data changes. CDC (Change Data Capture) tails the WAL and publishes to Kafka.

```sql
-- Outbox table for reliable event delivery
CREATE TABLE outbox_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(100) NOT NULL,  -- 'session', 'query', 'document'
    aggregate_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,  -- 'created', 'updated', 'deleted'
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,

    CONSTRAINT unprocessed_outbox CHECK (processed_at IS NULL)
);

-- Index for CDC to tail
CREATE INDEX idx_outbox_unprocessed ON outbox_events (created_at)
    WHERE processed_at IS NULL;
```

**Transaction Pattern**:
```python
async def create_session_with_event(session_data: dict):
    async with database.transaction():
        # 1. Create session
        session = await database.query(
            "INSERT INTO sessions (...) VALUES (...) RETURNING *",
            session_data
        )

        # 2. Write outbox event (same transaction)
        await database.query(
            """INSERT INTO outbox_events
               (aggregate_type, aggregate_id, event_type, payload)
               VALUES ('session', $1, 'created', $2)""",
            session["session_id"],
            json.dumps({
                "session_id": session["session_id"],
                "user_id": session["user_id"],
                "created_at": session["created_at"]
            })
        )

        # 3. Transaction commits - both persist together
        # 4. Debezium CDC detects new row and publishes to Kafka
```

#### Event Schema and Topics

| Topic | Event Type | Consumer | Purpose |
|-------|-----------|----------|---------|
| **case-assistant.session.completed** | Session created, query completed | Analytics pipeline | Usage metrics, user behavior |
| **case-assistant.query.failed** | Query error, timeout | Alerting | Operational monitoring |
| **case-assistant.chunk.failed** | Embedding failure | Alerting + manual review | DLQ monitoring |
| **case-assistant.user.consent** | Consent granted/revoked | Compliance audit | Legal compliance |

#### Debezium CDC Configuration

```yaml
# Debezium configuration for PostgreSQL CDC
connector:
  name: case-assistant-outbox
  class: io.debezium.connector.postgresql.PostgresConnector

database:
  hostname: aurora-cluster.cluster-xyz.ap-southeast-2.rds.amazonaws.com
  port: 5432
  username: debezium_user
  password: ${DEBEZIUM_PASSWORD}
  database: case_assistant
  plugin.name: pgoutput

properties:
  plugin.name: pgoutput
  publication.name: case_assistant_outbox
  table.include.list: public.outbox_events

  # Snapshot mode (schema_only = no existing data)
  snapshot.mode: schema_only

  # Event processing
  transforms: "outbox_events"
  transforms.unwrap.smt.type: none
  delete.tombstone.handling.mode: emit

  # Kafka settings
  kafka.bootstrap.servers: ${KAFKA_BROKERS}
  kafka.topic.prefix: case-assistant-
  kafka.acks: all
  kafka.retries: 3

  # Error handling
  errors.retry.timeout: -1  # Retry forever
  errors.retry.delay.ms: 1000
```

#### Kafka Topics Configuration

| Topic | Partitions | Retention | Purpose |
|-------|-----------|----------|---------|
| case-assistant.session.completed | 6 | 7 days | Session analytics, user behavior |
| case-assistant.query.failed | 3 | 30 days | Error monitoring, operational metrics |
| case-assistant.chunk.failed | 3 | 30 days | DLQ monitoring, quality tracking |
| case-assistant.user.consent | 3 | 7 years | Compliance audit, legal requirements |

#### Consumer Patterns

**Analytics Pipeline**:
```python
async def process_session_events(events: list[dict]):
    """Process session completion events for analytics."""
    for event in events:
        # Aggregate metrics
        await analytics.upsert({
            "date": event["created_at"].date(),
            "user_id": event["user_id"],
            "session_type": event["session_type"],
            "turns_count": event["turns_count"],
            "duration_seconds": event["duration_seconds"],
            "queries_count": event["queries_count"]
        })

        # Write to analytics warehouse (Snowflake, S3, etc.)
        await warehouse.write(event)
```

#### Benefits of Outbox + Kafka Pattern

| Benefit | Description |
|---------|-------------|
| **Atomic guarantees** | Events and data persist together or not at all |
| **No distributed transactions** | Simple ACID transactions in PostgreSQL only |
| **Decoupling** | Producers don't need to know about consumers |
| **Replay capability** | Kafka events can be replayed for reprocessing |
| **Scalability** | Consumers scale independently of producers |
| **Reliability** | At-least-once delivery guaranteed by Kafka + CDC |
| **Audit trail** | All events retained in Kafka for compliance |

#### When to Use This Pattern

| Use Case | Use Kafka + Outbox | Alternative |
|----------|-----------------|------------|
| **Analytics pipeline** | ✅ Yes | Direct database queries |
| **Real-time monitoring** | ✅ Yes | CloudWatch metrics |
| **Audit trail** | ✅ Yes | Database audit logs |
| **Simple notifications** | ❌ No | SNS direct (simpler) |
| **Low-latency events** | ❌ No | EventBridge (faster) |

---

## 4. Proposed Architecture Changes

### 4.1 Summary of Required Changes

| Change | Current State | Target State | Priority |
|--------|--------------|--------------|----------|
| **Conversation storage** | Redis (ephemeral) | Aurora PostgreSQL (7-year retention) | P0 - Legal requirement |
| **LLM response chain** | Not stored | PostgreSQL query_traces table | P0 - Audit requirement |
| **Deletion mechanism** | Hard-delete | Soft-delete with 7-year retention | P0 - Legal requirement |
| **Session expiry** | Auto-delete after 30 days | Session marked inactive, data retained | P0 - Legal requirement |
| **RBAC** | Authentication only | Full RBAC with RLS | P0 - Security requirement |
| **Team/workspaces** | Not defined | Workspace model for collaboration | P1 - Feature |
| **Archival** | Not defined | Automated archival to Glacier | P2 - Cost optimization |
| **Records authority** | Not engaged | Submit and obtain authority | P0 - Compliance |

### 4.2 Updated Data Flow

```mermaid
sequenceDiagram
    participant User
    participant API as API Gateway
    participant Auth as Cognito + RLS
    participant Redis as ElastiCache Redis
    participant Aurora as Aurora PostgreSQL
    participant OpenSearch as OpenSearch
    participant S3 as S3

    User->>API: Create session
    API->>Auth: Validate JWT, extract user_id/role
    API->>Auth: SET app.user_id, app.user_role
    API->>Aurora: INSERT INTO sessions (user_id, created_at)
    API->>Redis: Cache active session registry
    API-->>User: Session created

    User->>API: Upload document
    API->>S3: Store PDF (encrypted)
    API->>OpenSearch: Index chunks with user_id filter
    API->>Aurora: INSERT INTO uploaded_documents
    API-->>User: Document uploaded

    User->>API: Send query
    API->>Auth: SET app.user_id for RLS
    API->>OpenSearch: Search with user_id filter (RLS enforced)
    API->>Aurora: Store query trace (full chain)
    API->>Bedrock: Generate response
    API->>Aurora: Store LLM response in conversation
    API->>Redis: Cache query (optional)
    API-->>User: Response + citations

    Note over Aurora,Aurora: All conversation and query data<br/>retained for 7 years minimum
    Note over OpenSearch,S3: User data deleted only on<br/>user request or records authority
```

### 4.3 Schema Changes

```sql
-- ============================================
-- SESSIONS
-- ============================================
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id),
    workspace_id UUID REFERENCES workspaces(workspace_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, DELETED

    -- Soft-delete fields
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES users(user_id),
    deletion_reason VARCHAR(255),

    -- Records management
    retention_until TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 years'),
    records_classification VARCHAR(100) DEFAULT 'ADMINISTRATIVE_RECORD',

    -- Session metadata
    business_line VARCHAR(100),
    use_case VARCHAR(100),
    audit_reference VARCHAR(100),

    CONSTRAINT valid_status CHECK (status IN ('ACTIVE', 'INACTIVE', 'DELETED'))
);

CREATE INDEX idx_sessions_user ON sessions(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_sessions_workspace ON sessions(workspace_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_sessions_retention ON sessions(retention_until) WHERE deleted_at IS NOT NULL;

-- ============================================
-- CONVERSATION MESSAGES
-- ============================================
CREATE TABLE conversation_messages (
    message_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(session_id),
    user_id UUID NOT NULL REFERENCES users(user_id),
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    token_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Soft-delete fields
    deleted_at TIMESTAMPTZ,
    retention_until TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 years'),

    CONSTRAINT valid_role CHECK (role IN ('user', 'assistant'))
);

CREATE INDEX idx_messages_session ON conversation_messages(session_id, created_at) WHERE deleted_at IS NULL;

-- ============================================
-- QUERY TRACES (Audit Trail)
-- ============================================
CREATE TABLE query_traces (
    query_trace_id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(session_id),
    user_id UUID NOT NULL REFERENCES users(user_id),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Query
    query_original TEXT NOT NULL,
    query_rewritten TEXT,
    detected_citations JSONB,

    -- Retrieval (optimized - store IDs, not full text)
    citation_lookup JSONB,              -- Matched citation, title, chunk pointers
    vector_search JSONB,                -- Chunk IDs and scores only
    bm25_search JSONB,                  -- Chunk IDs and scores only
    reranking JSONB,                    -- Final ranking of chunk IDs

    -- Context optimization: Store chunk references instead of full text
    context_chunk_ids JSONB,            -- ["chunk-001", "chunk-002", "chunk-003"]
    context_chunk_versions JSONB,       -- {"chunk-001": "v1", "chunk-002": "v1"}
    context_hash BYTEA,                 -- SHA-256 for integrity verification

    -- LLM
    llm_model VARCHAR(100),
    llm_response_full TEXT NOT NULL,    -- Full response IS stored
    llm_parameters JSONB,

    -- Results
    citations JSONB,                    -- Chunk IDs, text snippets, positions
    token_count INTEGER,
    duration_ms INTEGER,

    -- Metadata
    business_line VARCHAR(100),
    use_case VARCHAR(100),

    -- Soft-delete
    deleted_at TIMESTAMPTZ,
    retention_until TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 years')
);

CREATE INDEX idx_traces_user ON query_traces(user_id, timestamp DESC);
CREATE INDEX idx_traces_session ON query_traces(session_id, timestamp);
CREATE INDEX idx_traces_retention ON query_traces(retention_until) WHERE deleted_at IS NOT NULL;

-- ============================================
-- UPLOADED DOCUMENTS
-- ============================================
CREATE TABLE uploaded_documents (
    document_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(session_id),
    user_id UUID NOT NULL REFERENCES users(user_id),
    filename VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_hash VARCHAR(64), -- SHA-256
    content_type VARCHAR(100),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Processing status
    status VARCHAR(50) NOT NULL DEFAULT 'UPLOADING', -- UPLOADING, PROCESSING, READY, FAILED
    page_count INTEGER,
    chunk_count INTEGER,
    processed_at TIMESTAMPTZ,

    -- S3 locations
    s3_bucket VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    s3_version_id VARCHAR(200),

    -- OpenSearch
    opensearch_index VARCHAR(255),

    -- Soft-delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES users(user_id),
    deletion_reason VARCHAR(255),
    retention_until TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 years'),

    CONSTRAINT valid_status CHECK (status IN ('UPLOADING', 'PROCESSING', 'READY', 'FAILED'))
);

CREATE INDEX idx_documents_user ON uploaded_documents(user_id, uploaded_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_documents_session ON uploaded_documents(session_id) WHERE deleted_at IS NULL;

-- ============================================
-- ENABLE ROW LEVEL SECURITY
-- ============================================
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploaded_documents ENABLE ROW LEVEL SECURITY;

-- ... (RLS policies as defined in section 3.3)
```

---

## 5. Implementation Roadmap

### Phase 1: Compliance Foundation (Weeks 1-4) - **BLOCKER**

**Must complete before production deployment**

| Task | Owner | Deliverable |
|------|-------|-------------|
| Engage Records Management Team | Product/Engineering | Data classification matrix |
| Submit Records Authority to NAA | Product | Authority documentation |
| Implement Aurora PostgreSQL | Engineering | Database schema, migrations |
| Implement conversation persistence | Engineering | Full conversation storage |
| Implement query trace storage | Engineering | Complete audit trail |
| Implement soft-delete mechanism | Engineering | Soft-delete for all user data |
| Update session lifecycle logic | Engineering | Remove auto-delete, add soft-delete |
| **Milestone** | | **Compliance sign-off from Records team** |

### Phase 2: Access Control (Weeks 5-8) - **P0**

| Task | Owner | Deliverable |
|------|-------|-------------|
| Define RBAC roles | Product | Role definitions and permissions matrix |
| Implement PostgreSQL RLS | Engineering | All tables have RLS policies |
| Update authentication middleware | Engineering | SET app.user_id from JWT |
| Implement workspace model | Engineering | Team collaboration feature |
| Security review | Security | Penetration testing, access control review |
| **Milestone** | | **Security sign-off for production** |

### Phase 3: Archival (Weeks 9-12) - **P1**

| Task | Owner | Deliverable |
|------|-------|-------------|
| Design archival pipeline | Engineering | Architecture for S3 Glacier archival |
| Implement archival jobs | Engineering | Automated archival after 12 months |
| Implement disposal jobs | Engineering | Automated disposal after 7 years |
| Create disposal reporting | Engineering | Annual disposal certificates |
| **Milestone** | | **Automated archival and disposal operational** |

### Phase 4: Hardening (Weeks 13-16) - **P1**

| Task | Owner | Deliverable |
|------|-------|-------------|
| Implement comprehensive audit logging | Engineering | All access logged |
| Create admin dashboard | Engineering | Audit log viewer, session management |
| Implement alerting | Engineering | Suspicious access detection |
| Run security assessment | Security | Third-party review |
| **Milestone** | | **Production-ready deployment** |

---

## Appendix A: Records Authority Template

**To be submitted to National Archives of Australia**

```
SYSTEM: Case Assistant - ATO Internal Tax Law AI
AGENCY: Australian Taxation Office
FUNCTION: Audit decision support, technical advice, policy research

RECORDS CREATED:
1. Conversation history between ATO officers and AI system
2. Query traces documenting information retrieval and AI responses
3. Uploaded documents (ATO officer research materials)
4. System access and audit logs

RETENTION PERIOD: 7 years
JUSTIFICATION:
- Administrative records supporting ATO business functions
- Evidence of decision-making for audit and technical advice
- Reference to General Disposal Schedule (GDS) for administrative records

DISPOSAL ACTION: Destroy after 7 years
SPECIAL INSTRUCTIONS: Nil

APPROVED: [National Archives signature and date]
AUTHORITY NUMBER: [To be assigned]
```

---

## Appendix B: Open Questions

### Blocking Questions (Must Answer Before Implementation)

1. **Deployment Scenario**: Is this system for public taxpayer-facing use OR ATO internal use?
   - This determines the entire architecture direction
   - Public-facing: Ephemeral sessions acceptable, 90-day retention
   - ATO internal: 7-year retention, Records Authority required

2. **Records Authority Engagement**: Has the ATO Records Management team been engaged? What is the timeline for obtaining NAA authority?

3. **Legal Basis for AI Conversations**: Has legal counsel confirmed that AI conversations are Commonwealth records? What is the specific legal basis?

### Architecture Questions

4. **Cost Approval**: 7-year retention increases costs significantly (~$15K/year vs near-zero for current design). Is this budgeted?

5. **Tiered Retention**: Should different conversation types have different retention periods? (e.g., learning queries: 1 year, audit decisions: 7 years)

6. **Query Trace Storage**: Store full LLM context or just chunk IDs? (Recommendation: Chunk IDs with versioning for 99% cost reduction)

7. **Cross-Region**: If we deploy to multiple AWS regions for resilience, how do we handle records retention across regions?

8. **Export Format**: If we need to export records to National Archives, what format? (PDF conversation logs, JSON data dumps, etc.)

9. **Real-Time Features**: Do we need WebSocket streaming? Can PostgreSQL NOTIFY handle it or do we need Redis?

### Operational Questions

10. **Discovery Protocol**: In legal discovery proceedings, can we be required to produce query traces? What's the protocol?

11. **User Offboarding**: When an ATO officer leaves or is under investigation, how do we handle their data?

12. **SIEM Integration**: Does ATO have a centralized SIEM (Splunk, ELK) that we need to forward logs to?

**For detailed discussion of these questions, see [14a-questions-and-gaps.md](./14a-questions-and-gaps.md).**

---

## Appendix C: References

- [Archives Act 1983](https://www.legislation.gov.au/Details/C2021C00402)
- [Attorney-General's Department - Records Management](https://www.ag.gov.au/business-continuity-and-security/records-management)
- [ATO Records Management Policy](Internal ATO document)
- [AWS SaaS Factory PostgreSQL RLS](https://github.com/aws-samples/aws-saas-factory-postgresql-rls)
- [OWASP ASVS v4.0 - Access Control](https://owasp.org/www-project-application-security-verification-standard/)

---

**Document End**
