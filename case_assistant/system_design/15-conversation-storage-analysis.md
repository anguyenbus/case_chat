# Conversation History Storage Analysis

**Document Version**: 5.0.0
**Date**: 2026-04-22
**Author**: Principal AI Engineer
**Status**: Research & Analysis
**Related Documents**: [04-session-lifecycle.md](./04-session-lifecycle.md), [01-chat-architecture.md](./01-chat-architecture.md), [14-data-retention-and-governance.md](./14-data-retention-and-governance.md)

---

## Executive Summary

Choosing between OpenSearch and Aurora PostgreSQL for conversation history storage depends on **access patterns**, **consistency requirements**, and **feature needs**. This document analyzes both options across multiple use cases.

**Quick Recommendation**:
- **Aurora PostgreSQL + pgvector**: Primary store, ACID, cost-effective, simpler operations, compliance-grade retention
- **OpenSearch**: Secondary index for analytics, semantic search, and high-scale filtering. Also provides built-in conversational memory for agents running within its ml-commons framework
- **Hybrid pattern**: Best for production systems with varied access patterns

---

## Table of Contents

1. [Technology Comparison](#technology-comparison)
2. [Use Case Analysis](#use-case-analysis)
3. [Scenario-Based Recommendations](#scenario-based-recommendations)
4. [What Is the OpenSearch ML-Commons Framework](#what-is-the-opensearch-ml-commons-framework)
5. [OpenSearch Built-in Conversational Memory](#opensearch-built-in-conversational-memory)
6. [When OpenSearch IS the Right Choice for Conversation History](#when-opensearch-is-the-right-choice-for-conversation-history)
7. [Architecture Patterns](#architecture-patterns)
8. [Implementation Guidance](#implementation-guidance)

---

## Technology Comparison

### Aurora PostgreSQL with pgvector

**Source**: [pgvector/pgvector GitHub](https://github.com/pgvector/pgvector)

| Capability | Specification |
|------------|----------------|
| **Vector Support** | Up to 16,000 dimensions, supports float32/half/binary/sparse |
| **Index Types** | HNSW (fast query, high recall), IVFFlat (faster build, lower memory) |
| **Distance Functions** | L2, inner product, cosine, L1, Hamming, Jaccard |
| **ACID Compliance** | Full - WAL replication, point-in-time recovery |
| **Hybrid Search** | Vector + GIN full-text indexes, efficient pre-filtering |
| **Scalability** | Vertical scaling, read replicas, Citus for sharding |
| **Storage Cost** | ~50-70% cheaper than OpenSearch for equivalent data |
| **Query Latency** | Sub-100ms for typical ANN queries with proper indexes |

**Strengths**:
- ✅ Strong consistency guarantees
- ✅ Mature tooling and operational expertise
- ✅ Complex relational queries (JOINs, foreign keys)
- ✅ Point-in-time recovery for compliance
- ✅ Lower total cost of ownership

**Limitations**:
- ⚠️ Vector search throughput lower than dedicated vector DBs at extreme scale
- ⚠️ Analytics queries require materialized views or additional tooling
- ⚠️ Full-text search less powerful than OpenSearch's capabilities

---

### OpenSearch with k-NN

**Source**: [OpenSearch Vector Search Documentation](https://opensearch.org/docs/latest/search-plugins/vector-search/)

| Capability | Specification |
|------------|----------------|
| **Vector Support** | Up to 16,000 dimensions, byte and binary vectors |
| **Index Types** | HNSW (Lucene, Faiss, NMSLIB), IVF (Faiss) |
| **Distance Functions** | L2, inner product, cosineine, L1 |
| **Engines** | Lucene (smart filtering), Faiss (large-scale) |
| **Approximate Search** | HNSW (fast, high quality), IVF (fastest build, lower quality) |
| **Native Features** | Aggregations, full-text search, geo queries, complex filters |
| **Scalability** | Horizontal scaling, tens of billions of vectors |
| **Storage Cost** | Higher due to index overhead and replication |

**Engine Recommendations**:

| Engine | Best For | Max Vectors | Filter Support | Quality |
|--------|----------|-------------|----------------|---------|
| Lucene/HNSW | Small deployments, smart filtering | <10M | Pre/post-filter auto-selected | High |
| Faiss/HNSW | Large-scale production | Tens of billions | Post-filter | High |
| Faiss/IVF | Highest indexing throughput | Tens of billions | Post-filter | Lower |

**Strengths**:
- ✅ Excellent semantic search at scale
- ✅ Native aggregations and analytics
- ✅ Powerful full-text search with analyzers
- ✅ Complex multi-field filtering
- ✅ Horizontal scaling capabilities

**Limitations**:
- ⚠️ Eventual consistency (near real-time, ~1 sec refresh)
- ⚠️ Higher operational complexity
- ⚠️ Higher storage costs
- ⚠️ No ACID guarantees or foreign key relationships

---

## Use Case Analysis

### Use Case 1: Simple Chat Bot - Conversation Retrieval

**Pattern**: Retrieve all messages in a session, ordered by timestamp

```
User: "Show me my conversation from yesterday"
System: SELECT * FROM messages WHERE session_id = ? ORDER BY created_at
```

| Database | Performance | Cost | Complexity |
|----------|-------------|------|------------|
| **Aurora** | ⚡ Excellent (B-tree index) | 💰 Low | 🟢 Simple |
| **OpenSearch** | ⚡ Good | �💰 Medium | 🟡 Moderate |

**Verdict**: **Aurora PostgreSQL**

Native B-tree indexes on `(session_id, created_at)` provide optimal sequential retrieval. OpenSearch is overkill for this pattern.

---

### Use Case 2: Semantic Search - "Find Similar Conversations"

**Pattern**: Find past conversations similar to current query

```
User: "What did I ask about capital gains last month?"
System: Vector similarity search across all conversations
```

| Database | Performance | Cost | Complexity |
|----------|-------------|------|------------|
| **Aurora + pgvector** | ⚡ Good (HNSW) | 💰 Low | 🟢 Simple |
| **OpenSearch** | ⚡ Excellent (Faiss) | �💰 Medium | 🟡 Moderate |

**Verdict**: **Depends on scale**

- **<10M messages**: Aurora + pgvector sufficient
- **>10M messages**: OpenSearch provides better throughput

---

### Use Case 3: Tag-Based Organization

**Pattern**: Conversations tagged by topic, project, or custom labels

```
User: "Show me all conversations tagged #tax-advice"
User: "Find conversations about #gst from last quarter"
```

| Database | Performance | Cost | Features |
|----------|-------------|------|----------|
| **Aurora** | ⚡ Excellent (many-to-many + B-tree) | 💰 Low | Full relational capabilities |
| **OpenSearch** | ⚡ Excellent (keyword field + aggregations) | 💰💰 Medium | Built-in tag clouds, facets |

**Schema Comparison**:

**Aurora** - Relational approach:
```sql
CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE conversation_tags (
    conversation_id UUID REFERENCES conversations(id),
    tag_id INT REFERENCES tags(id),
    PRIMARY KEY (conversation_id, tag_id)
);

-- Efficient tag filtering
CREATE INDEX ON conversation_tags(tag_id);
-- Tag aggregation with counts
SELECT t.name, COUNT(*) FROM conversation_tags ct
JOIN tags t ON ct.tag_id = t.tag_id
GROUP BY t.name;
```

**OpenSearch** - Denormalized approach:
```json
{
  "mappings": {
    "properties": {
      "tags": {"type": "keyword"},
      "tag_count": {"type": "integer"}
    }
  }
}

// Tag filtering
POST /conversations/_search
{
  "query": {"term": {"tags": "#tax-advice"}},
  "aggs": {
    "tag_cloud": {"terms": {"field": "tags"}}
  }
}
```

**Verdict**: **Aurora for complex tag relationships, OpenSearch for simple tag clouds**

- **Complex tag hierarchies**: Aurora (foreign keys, constraints)
- **Simple tag filtering + analytics**: OpenSearch (aggregations)

---

### Use Case 4: Analytics & Reporting

**Pattern**: Generate insights from conversation data

```
Analytics: "Average messages per session this week"
Analytics: "Most discussed topics by tag"
Analytics: "User engagement metrics"
```

| Database | Performance | Features |
|----------|-------------|----------|
| **Aurora** | ⚡ Moderate (requires materialized views) | Standard SQL, window functions |
| **OpenSearch** | ⚡ Excellent (native aggregations) | Date histograms, percentiles, cardinality |

**Verdict**: **OpenSearch for heavy analytics workloads**

Native aggregations pipeline provides superior performance for:
- Date range analytics
- Funnel analysis
- Real-time dashboards
- Anomaly detection

---

## Scenario-Based Recommendations

### Scenario 1: Simple RAG Chatbot

**Characteristics**:
- Sequential conversation retrieval
- Document-based Q&A
- Moderate scale (<10K users)
- Cost-sensitive

**Recommended Architecture**:

```
┌─────────────────────────────────────────────────────┐
│                  Aurora PostgreSQL                  │
│  ┌─────────────────────────────────────────────┐   │
│  │ • Sessions                                   │   │
│  │ • Messages (with content_embedding via pgvector) │   │
│  │ • Document references                        │   │
│  │ • Tags (many-to-many)                        │   │
│  └─────────────────────────────────────────────┘   │
│                     Single Database                │
└─────────────────────────────────────────────────────┘
```

**Justification**:
- Aurora handles all access patterns efficiently
- pgvector enables semantic search when needed
- Simplified operations (one database)
- Lower TCO

---

### Scenario 2: Tag-Heavy Knowledge Base

**Characteristics**:
- Complex tag hierarchies
- User-defined categories
- Tag-based navigation
- Faceted search requirements

**Recommended Architecture**:

```
┌─────────────────────────────────────────────────────────┐
│                     Aurora PostgreSQL                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • Sessions, Messages (source of truth)          │   │
│  │ • Tags (hierarchical, with relationships)       │   │
│  │ • Tag definitions, constraints                  │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                     OpenSearch                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • Message index (for search)                    │   │
│  │ • Denormalized tags (for facets)                │   │
│  │ • Search UI support                             │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Justification**:
- Aurora manages complex tag relationships with referential integrity
- OpenSearch provides fast faceted search and tag clouds
- Hybrid approach gives best of both worlds

---

### Scenario 3: Agentic AI System

**Characteristics**:
- Multiple agents collaborate
- Shared conversation memory
- Tool use tracking
- Agent handoff contexts
- Reflection and planning logs

**Data Model Requirements**:

```sql
-- Agent coordination
CREATE TABLE agent_turns (
    turn_id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    agent_name TEXT NOT NULL,
    agent_role TEXT NOT NULL,  -- orchestrator, researcher, validator
    parent_turn_id UUID REFERENCES agent_turns(turn_id),  -- For handoffs
    input JSONB,  -- Structured input to agent
    output JSONB,  -- Agent output
    tool_calls JSONB,  -- Tools used
    reasoning TEXT,  -- Chain of thought
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversation summary (for context compression)
CREATE TABLE conversation_summaries (
    summary_id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    turn_range INT4RANGE NOT NULL,  -- Which turns this covers
    summary TEXT NOT NULL,
    summary_embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Recommended Architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                 Aurora PostgreSQL (Primary)                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • Sessions, Messages                                  │ │
│  │ • Agent turns (hierarchical relationships)            │ │
│  │ • Tool execution logs                                 │ │
│  │ • Conversation summaries (with embeddings)            │ │
│  │ • User feedback and ratings                           │ │
│  └───────────────────────────────────────────────────────┘ │
│                    Source of Truth                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   OpenSearch (Analytics)                    │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • Agent performance analytics                         │ │
│  │ • Tool usage patterns                                 │ │
│  │ • Success/failure rates by agent                      │ │
│  │ • Latency tracking                                    │ │
│  └───────────────────────────────────────────────────────┘ │
│                   Observability Only                       │
└─────────────────────────────────────────────────────────────┘
```

**Justification**:
- **ACID critical**: Agent handoffs require consistent state
- **Complex relationships**: Parent-child turn chains need foreign keys
- **Structured queries**: "Show all failed tool calls for agent X"
- **Analytics separate**: OpenSearch for observability, not primary storage

---

### Scenario 4: High-Scale Multi-Tenant System

**Characteristics**:
- >100K concurrent users
- Multi-tenant isolation
- Real-time analytics dashboard
- Semantic search across all conversations

**Recommended Architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│              Aurora PostgreSQL (Per-Tenant)                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • Tenant isolation via row-level security             │ │
│  │ • User sessions, messages                             │ │
│  │ • Primary data store                                  │ │
│  │ • Read replicas for scaling                           │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ (CDC Stream)
┌─────────────────────────────────────────────────────────────┐
│                   OpenSearch Cluster                        │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ • Global semantic search index                        │ │
│  │ • Cross-tenant analytics (aggregated)                 │ │
│  │ • Real-time dashboard data                            │ │
│  │ • Tenant routing for isolation                        │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Justification**:
- Aurora handles tenant isolation with RLS
- OpenSearch enables cross-tenant search (with proper auth)
- Scaling: Aurora vertical + replicas, OpenSearch horizontal

---

## What Is the OpenSearch ML-Commons Framework

**Research Date**: April 2026
**Source**: [OpenSearch ml-commons Plugin Documentation](https://docs.opensearch.org/latest/ml-commons-plugin/)

### One-Sentence Summary

**ml-commons** is OpenSearch's built-in plugin that turns your OpenSearch cluster into an AI/ML execution platform — allowing you to run machine learning models, build AI agents, and manage conversational memory entirely *inside* OpenSearch without an external application orchestrating the AI pipeline.

### Why This Matters

Understanding ml-commons is **prerequisite** to understanding where OpenSearch's conversational memory fits. The memory feature is not a standalone database API — it is a capability *of* the ml-commons agent framework. Using it means buying into the framework.

---

### The Six Capabilities of ml-commons

```
┌─────────────────────────────────────────────────────────────────┐
│                 OpenSearch Cluster                               │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Search &  │  │ Indexing │  │ Security │  │ ml-commons   │   │
│  │ Analytics │  │ & Ingest │  │ Plugin   │  │ Plugin       │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
│                                                │                │
│                  ┌─────────────────────────────┘                │
│                  ▼                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  ml-commons capabilities                  │   │
│  │                                                          │   │
│  │  1. Model Management                                     │   │
│  │     • Pretrained models (built-in)                       │   │
│  │     • Custom models (upload your own)                    │   │
│  │     • Remote connectors (Bedrock, OpenAI, SageMaker)     │   │
│  │                                                          │   │
│  │  2. Inference APIs                                       │   │
│  │     • Text embedding (at ingest or query time)           │   │
│  │     • ML inference (classify, summarize, etc.)           │   │
│  │     • Batch + async ingestion                            │   │
│  │                                                          │   │
│  │  3. Agent Framework                                      │   │
│  │     • Flow agents (sequential tool pipelines)            │   │
│  │     • Conversational flow agents (RAG chatbots)          │   │
│  │     • Conversational agents (autonomous tool selection)  │   │
│  │     • Plan-execute-reflect agents (multi-step reasoning) │   │
│  │     • AG-UI agents (interactive UI protocol)             │   │
│  │                                                          │   │
│  │  4. Tools                                                │   │
│  │     • VectorDBTool, MLModelTool, IndexMappingTool        │   │
│  │     • DataDistributionTool, CatIndexTool, etc.           │   │
│  │     • Agent Tool (nest agents inside agents)             │   │
│  │                                                          │   │
│  │  5. Conversational Memory                                │   │
│  │     • Legacy: Memory → Messages (conversation_index)     │   │
│  │     • Agentic: Container → Session → Memory entries      │   │
│  │     • Context management (sliding window, summarization) │   │
│  │                                                          │   │
│  │  6. Guardrails                                           │   │
│  │     • Input/output filtering                             │   │
│  │     • Bedrock guardrails integration                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

### Two Modes of Operation

#### Mode 1: Model Hosting (you call OpenSearch for ML tasks)

Your application sends a request to OpenSearch, and ml-commons runs the model:

```
Application → POST /_plugins/_ml/_predict/text_embedding
                { "text": "What are penalty units?" }

OpenSearch (ml-commons) → Returns: [0.012, -0.034, 0.056, ...]
```

This is how vector embeddings get generated — ml-commons runs the embedding model inside OpenSearch so you don't need a separate ML inference service. **You can use this mode independently of the agent framework.**

#### Mode 2: Agent Framework (OpenSearch runs the entire AI pipeline)

You register an **agent** in OpenSearch that orchestrates the full RAG/agentic loop:

```
User Question
     │
     ▼
POST /_plugins/_ml/agents/{agent_id}/_execute
     { "parameters": { "question": "What are penalty units for this offence?" } }
     │
     ▼
┌─────────────────────────────────────────────────┐
│  Agent Framework (runs INSIDE OpenSearch)        │
│                                                  │
│  1. Retrieve conversation history from Memory    │
│  2. Run VectorDBTool → k-NN search on your index│
│  3. Run MLModelTool → call LLM (Bedrock, etc.)  │
│  4. Save interaction to Memory (auto)            │
│  5. Return response                              │
└─────────────────────────────────────────────────┘
     │
     ▼
Response to your application
```

**This is the key insight**: When people say "OpenSearch stores message history and is good for agentic work," they mean this Mode 2 — where OpenSearch's agent framework handles the **entire** RAG pipeline internally, including conversation memory.

---

### Available Agent Types

| Agent Type | Memory | Tool Execution | Description |
|------------|--------|----------------|-------------|
| `flow` | No | Sequential pipeline | Non-conversational tasks |
| `conversational_flow` | Yes (`conversation_index`) | Sequential, predefined order | RAG chatbots with conversation history |
| `conversational` | Yes (`conversation_index`) | Dynamic LLM-chosen order | Agent autonomously picks which tools to run |
| `plan_execute_reflect` | Via agentic memory | Plan-execute-reflect loop | Complex multi-step reasoning |
| `ag_ui` | Via agentic memory | AG-UI protocol | Interactive UI agents |

---

### Available Tools (Built-in)

Agents can use these tools to interact with OpenSearch and external services:

| Tool | Purpose |
|------|---------|
| `VectorDBTool` | k-NN vector similarity search on an OpenSearch index |
| `MLModelTool` | Call an ML model (local or remote via connector) |
| `IndexMappingTool` | Retrieve index mappings and schema information |
| `DataDistributionTool` | Analyse data distribution in an index |
| `CatIndexTool` | List and inspect index metadata |
| `SearchIndexTool` | Perform full-text or structured searches |
| `AgentTool` | Nest one agent inside another (agent composition) |
| `ConnectorTool` | Invoke a remote connector (e.g., Bedrock, OpenAI) |

---

### Architecture Decision: External Orchestration vs OpenSearch-Native Agents

This is the critical decision point for this project:

```
OPTION A: External Orchestration (current design)
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│ Frontend │────>│ EKS Chat     │────>│ Aurora PG    │
│          │     │ Engine       │────>│ OpenSearch   │
│          │     │ (orchestrates│────>│ Bedrock LLM  │
│          │     │  everything) │     │              │
└──────────┘     └──────────────┘     └──────────────┘
                  ^ Conversation history in Aurora
                  ^ OpenSearch = search + vectors only
                  ^ ml-commons = embedding inference only (Mode 1)

OPTION B: OpenSearch-Native Agents
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│ Frontend │────>│ API Gateway  │────>│ OpenSearch   │
│          │     │ (thin proxy) │     │ (ml-commons  │
│          │     │              │     │  agent runs   │
│          │     │              │     │  everything)  │
└──────────┘     └──────────────┘     └──────────────┘
                  ^ Agent framework handles RAG + memory + tools
                  ^ Still need Aurora for compliance/audit
                  ^ ml-commons = full agent framework (Mode 2)
```

| Dimension | Option A (External) | Option B (OpenSearch-Native) |
|-----------|--------------------|------------------------------|
| **Control** | Full — custom business logic, custom tool calls | Constrained by agent framework capabilities |
| **Compliance** | Straightforward — single source of truth in Aurora | Complex — must replicate from OpenSearch memory to Aurora |
| **Custom logic** | Unlimited — any Python/Node.js logic | Limited to agent framework's tool system |
| **Operational complexity** | Higher — manage Chat Engine + Aurora + OpenSearch | Lower — OpenSearch handles most of the pipeline |
| **Lock-in** | Lower — swap components independently | Higher — tied to ml-commons agent framework |
| **Debugging** | Standard application observability | Must understand ml-commons internals |
| **Conversation memory** | Build it yourself in Aurora (well-understood) | Built-in (automatic, but opaque) |

### Recommendation for This Project

For a government compliance system with 7-year retention requirements:

- **Use ml-commons in Mode 1** (model hosting / embedding inference only)
- **Do NOT use ml-commons in Mode 2** (agent framework) as the primary orchestration
- **Reason**: The compliance, audit, and retention requirements make Option A the safer choice. The agent framework's internal memory indices are not designed for compliance-grade data management.

---

## OpenSearch Built-in Conversational Memory

**Research Date**: April 2026
**Sources**: OpenSearch official documentation, OpenSearch blog (April 13, 2026), ml-commons plugin API reference

### Key Finding

OpenSearch **does** provide native conversation memory storage through the **ml-commons plugin**. This is a real, production-grade feature designed specifically for agentic AI workflows. However, it serves a **different purpose** than a general-purpose conversation history database.

---

### Two Generations of Memory

#### Generation 1: Legacy Memory System (`conversation_index`)

**Source**: [OpenSearch Conversational Memory Docs](https://opensearch.org/docs/latest/ml-commons-plugin/conversational-memory/)

Used by `conversational_flow` and `conversational` agent types. Two-level data model:

| Concept | Description | Identifier |
|---------|-------------|------------|
| **Memory** | A conversation container — groups all messages in a single conversation | `memory_id` |
| **Message** | A single Q&A exchange between human and LLM, including tool traces | `parent_message_id` |

**API Endpoints**:

| Operation | Endpoint |
|-----------|----------|
| Create memory | `POST /_plugins/_ml/memory/` |
| Get memory | `GET /_plugins/_ml/memory/{memory_id}` |
| Search memories | `GET /_plugins/_ml/memory/_search` |
| Delete memory | `DELETE /_plugins/_ml/memory/{memory_id}` |
| Get messages | `GET /_plugins/_ml/memory/{memory_id}/messages` |
| Get message | `GET /_plugins/_ml/memory/message/{message_id}` |
| Get traces | `GET /_plugins/_ml/memory/message/{message_id}/traces` |

**Agent Configuration**:

```json
POST /_plugins/_ml/agents/_register
{
    "name": "case-assistant-agent",
    "type": "conversational_flow",
    "memory": {
        "type": "conversation_index"
    },
    "tools": ["VectorDBTool", "MLModelTool"]
}
```

**Continuing a Conversation**:

```json
POST /_plugins/_ml/agents/{agent_id}/_execute
{
  "parameters": {
    "question": "What are the penalty units for this offence?",
    "memory_id": "gQ75lI0BHcHmo_cz2acL",
    "message_history_limit": 5
  }
}
```

The `memory_id` from a prior response links to the existing conversation. `message_history_limit` controls how many prior messages are injected into the LLM prompt via the `${parameters.chat_history:-}` template variable.

---

#### Generation 2: Agentic Memory System (OpenSearch 3.5+)

**Source**: [OpenSearch Agentic Memory Docs](https://opensearch.org/docs/latest/ml-commons-plugin/agentic-memory/)

A more sophisticated three-level model for advanced agent workflows:

| Concept | Description | API Prefix |
|---------|-------------|------------|
| **Container** | Top-level organizer for related sessions | `/_plugins/_ml/agentic-memory/container/` |
| **Session** | A conversation session within a container | `/_plugins/_ml/agentic-memory/session/` |
| **Memory** | Individual memory entries within a session | `/_plugins/_ml/agentic-memory/` |

Full CRUD + search APIs at each level.

---

#### Context Management (OpenSearch 3.5, April 2026)

**Source**: [OpenSearch Blog - "Solving context overflow" (April 13, 2026)](https://opensearch.org/blog/solving-context-overflow-how-opensearch-agents-stay-smart-in-long-conversations/)

OpenSearch 3.5 introduced a hook-based **context management** system that prevents context window overflow in long agent conversations. Three built-in context managers:

| Manager | Purpose | Example Config |
|---------|---------|----------------|
| **SlidingWindowManager** | Keeps only the N most recent messages, removing older ones when limits are reached | `max_messages: 6`, activates when `message_count_exceed: 20` |
| **SummarizationManager** | LLM-summarizes older interactions, preserving essential information while reducing token count | `summary_ratio: 0.3`, `preserve_recent_messages: 10`, activates when `tokens_exceed: 200000` |
| **ToolsOutputTruncateManager** | Truncates tool outputs that exceed specified limits | `max_output_length: 100000` |

**Configuration Example**:

```json
POST /_plugins/_ml/context_management/research-assistant-optimizer
{
  "description": "Context management for agents with extensive tool interactions",
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

**Usage in Agent**:

```json
POST /_plugins/_ml/agents/_register
{
  "name": "my-smart-agent",
  "type": "conversational",
  "llm": { "model_id": "your-llm-model-id" },
  "context_management_name": "research-assistant-optimizer"
}
```

---

### Agent Types and Memory Support

| Agent Type | Memory | Tool Execution | Use Case |
|------------|--------|----------------|----------|
| `flow` | No | Sequential pipeline | Non-conversational tasks |
| `conversational_flow` | Yes (`conversation_index`) | Sequential, predefined order | RAG chatbots with history |
| `conversational` | Yes (`conversation_index`) | Dynamic LLM-chosen order | Autonomous tool selection |
| `plan_execute_reflect` | Via agentic memory | Plan-execute-reflect loop | Complex multi-step reasoning |
| `ag_ui` | Via agentic memory | AG-UI protocol | Interactive UI agents |

**Requirement**: Agent framework must be enabled: `plugins.ml_commons.agent_framework_enabled: true`

---

### How Data Is Stored Internally

All conversation data is stored in **system-level OpenSearch indices** managed by the ml-commons plugin (not user-visible indices). The plugin handles indexing, retrieval, and cleanup automatically. The `memory_id` and `message_id` values are OpenSearch document IDs within these internal indices.

**Architecture**:

```
Agent Execution Request
    │
    ▼
Agent Framework (ml-commons plugin)
    │
    ├──► Creates/Retrieves Memory (conversation)
    │         stored as internal OpenSearch index
    │
    ├──► Runs Tools (VectorDBTool, MLModelTool, etc.)
    │         tool outputs stored as message traces
    │
    ├──► Applies Context Management (pre_llm / post_tool hooks)
    │         sliding window, summarization, truncation
    │
    ├──► Saves Message (question + answer + traces)
    │         linked to memory_id
    │
    └──► Returns: memory_id + parent_message_id + LLM response
```

---

### Critical Nuance: What This IS vs What It ISN'T

#### What it IS:

| Capability | Detail |
|-----------|--------|
| Runtime memory for OpenSearch agents | Designed for agents executing *within* the ml-commons plugin |
| Multi-turn conversation management | Auto-injects chat history into LLM prompts |
| Context window management | Native sliding window, summarization, truncation |
| Tool trace storage | Every tool invocation linked to message for debugging |
| Searchable | `GET /_plugins/_ml/memory/_search` for full-text search over history |
| Perfect for RAG | Co-located with vector search — same cluster, same query |

#### What it ISN'T:

| Limitation | Impact |
|-----------|--------|
| **Not a general-purpose conversation DB** | Tightly coupled to ml-commons agent framework |
| **Not designed for compliance retention** | No Row-Level Security, no soft-delete, no audit joins |
| **Not user-facing schema** | System-level indices managed by plugin, not extensible |
| **No ACID guarantees** | Eventually consistent, potential data loss on cluster event |
| **No relational features** | No foreign keys, no JOINs across sessions/users/metadata |
| **Not designed for 7-year retention** | No built-in archival or partitioning strategies |

---

### When OpenSearch Memory Is the Right Choice

| Scenario | Verdict |
|----------|---------|
| Building RAG chatbot entirely within OpenSearch ml-commons | Use it |
| Agent orchestrates tool calls via OpenSearch agent framework | Use it |
| Need runtime context management for long conversations | Use it |
| Already running OpenSearch for vector search and want to add chat history | Use it (for runtime context) |

### When Aurora Is Still Needed

| Scenario | Verdict |
|----------|---------|
| Government compliance requiring 7-year retention | Aurora required |
| Need Row-Level Security for multi-tenant isolation | Aurora required |
| Audit trails with relational queries across sessions, users, traces | Aurora required |
| Custom orchestration running on EKS (not OpenSearch agents) | Aurora required |
| Soft-delete, point-in-time recovery, ACID transactions | Aurora required |

---

### Recommendation Matrix for This Project

Given this project's architecture (EKS-based Chat Engine, government compliance, potential 7-year retention):

```
┌─────────────────────────────────────────────────────────────┐
│                     THIS PROJECT                             │
│                                                              │
│  ┌─────────────────────┐    ┌──────────────────────────┐   │
│  │ OpenSearch           │    │ Aurora PostgreSQL         │   │
│  │                      │    │                           │   │
│  │ • Vector embeddings  │    │ • Sessions (compliance)   │   │
│  │ • RAG chunks         │    │ • Conversation messages   │   │
│  │ • BM25 keyword index │    │ • Query traces (audit)    │   │
│  │ • Agent memory       │    │ • Soft-delete, RLS        │   │
│  │   (runtime context)  │    │ • 7-year retention        │   │
│  └─────────────────────┘    └──────────────────────────┘   │
│                                                              │
│  OpenSearch memory = runtime context for agents               │
│  Aurora = source-of-truth for compliance & audit              │
└─────────────────────────────────────────────────────────────┘
```

| Architecture Choice | Primary Conversation Store | OpenSearch Memory Role |
|---------------------|---------------------------|----------------------|
| **OpenSearch-native agents** (agent runs in ml-commons) | OpenSearch memory for runtime + Aurora for compliance persistence | Runtime memory, auto-managed |
| **Custom orchestration** (EKS Chat Engine) | Aurora PostgreSQL only | Not used — adds complexity with no benefit |
| **Hybrid** (some OpenSearch agents, some custom) | Aurora for all persistent storage | Runtime agent context only, not persisted |

**Bottom Line**: OpenSearch's conversational memory is a genuine, well-designed feature for agentic AI. It's not a replacement for Aurora when you need compliance-grade retention, relational queries, and audit trails. They serve **different purposes** and can coexist in a hybrid architecture.

### Pattern 1: Aurora-First (Simple)

```
┌───────────────────────────────────────────────────────────┐
│                     Application                           │
└───────────────────────────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────┐
│              Aurora PostgreSQL + pgvector                 │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ • Sessions                                          │  │
│  │ • Messages (with content_embedding)                 │  │
│  │ • Vector similarity search                          │  │
│  │ • All queries served here                           │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

**When to use**:
- <50K messages total
- Simple access patterns
- Cost-sensitive
- Small team

---

### Pattern 2: Hybrid with CDC Sync

```
┌───────────────────────────────────────────────────────────┐
│                     Application                           │
└───────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│   Aurora PostgreSQL     │    │      OpenSearch         │
│   (Primary Store)       │◀───│    (Search Index)       │
│                         │    │                         │
│  • Sessions             │    │  • Message index        │
│  • Messages             │    │  • Semantic search      │
│  • ACID writes          │    │  • Analytics            │
│  • Sequential reads     │    │  • Faceted search       │
└─────────────────────────┘    └─────────────────────────┘
            ▲                               │
            └───────────────┬───────────────┘
                            │
                    ┌───────┴────────┐
                    │  CDC / Lambda  │
                    │  Change Stream │
                    └────────────────┘
```

**When to use**:
- >50K messages
- Need both ACID and analytics
- Complex access patterns
- Can manage two systems

**CDC Options**:
- AWS DMS (managed)
- Logical replication + custom handler
- PGAdapter + Lambda

---

### Pattern 3: Write-Through Cache

```
┌───────────────────────────────────────────────────────────┐
│                     Application                           │
└───────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
    ┌───────────────────┐    ┌───────────────────┐
    │   Aurora (Write)  │    │ OpenSearch (Write) │
    │                   │    │                   │
    │  • INSERT/UPDATE  │    │  • Index document  │
    │  • Return success │    │  • Async optional  │
    └───────────────────┘    └───────────────────┘
                │                       │
                ▼                       ▼
    ┌───────────────────┐    ┌───────────────────┐
    │   Aurora (Read)   │    │ OpenSearch (Read)  │
    │                   │    │                   │
    │  • By session_id  │    │  • Semantic search │
    │  • By timestamp   │    │  • Analytics       │
    └───────────────────┘    └───────────────────┘
```

**When to use**:
- Need real-time search availability
- Can tolerate occasional sync divergence
- Search is critical path

**Trade-off**:
- ✅ Search always available
- ❌ Dual write complexity
- ❌ Eventual consistency between stores

---

---

## When OpenSearch IS the Right Choice for Conversation History

**Research Date**: April 2026
**Sources**: OpenSearch official documentation, OpenSearch blog posts, AWS blogs, pgvector GitHub, OpenSearch ml-commons plugin API reference

### Purpose of This Section

Previous sections recommend Aurora PostgreSQL for this project. This section provides the **counter-research** — specific, concrete scenarios where OpenSearch IS the right primary store for conversation history. This ensures the team makes an informed decision with full awareness of when the alternative would be superior.

---

### Scenario 1: OpenSearch-Native Agentic RAG Platform

**When you want OpenSearch to be the entire AI platform, not just a search index.**

If the team decides to use OpenSearch's ml-commons agent framework as the primary orchestration layer (Mode 2), then storing conversation history in OpenSearch's built-in memory is the natural and correct choice.

```
User Question
     │
     ▼
POST /_plugins/_ml/agents/{agent_id}/_execute
     │
     ▼
┌──────────────────────────────────────────────────┐
│  OpenSearch (runs the ENTIRE AI pipeline)         │
│                                                   │
│  • Retrieves conversation history (built-in)      │
│  • Runs VectorDBTool (k-NN on same cluster)       │
│  • Runs MLModelTool (calls Bedrock/OpenAI)         │
│  • Applies context management (auto)               │
│  • Saves interaction to memory (auto)              │
│  • Returns response                                │
│                                                   │
│  Everything in one system. No external orchestration│
└──────────────────────────────────────────────────┘
```

**Why OpenSearch wins here**:
- Zero integration code — memory, retrieval, and LLM calls are all managed by the agent framework
- Built-in context management (SlidingWindowManager, SummarizationManager) — you don't build this yourself
- Conversation history co-located with vector index — no network hop between retrieval and memory
- Tool traces automatically stored alongside messages for debugging

**Who should choose this**: Teams that want to minimise custom code and are comfortable committing to the OpenSearch agent framework as their AI platform.

**Trade-off**: You must still replicate to Aurora/DynamoDB for any compliance or long-term retention needs.

---

### Scenario 2: Full-Text Search Over Conversation History Is a Core Feature

**When users need to search across all past conversations by keywords, phrases, or topics.**

OpenSearch's text analysis pipeline (analysers, tokenisers, stemmers, n-grams, synonym graphs) is far more powerful than PostgreSQL's full-text search (`tsvector`/`tsquery`). If searching conversation history is a first-class feature, not an afterthought:

```json
POST /conversations/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "content": "penalty units for tax evasion" } },
        { "term": { "workspace_id": "ws-123" } }
      ]
    }
  },
  "highlight": {
    "fields": { "content": {} }
  },
  "aggs": {
    "by_topic": { "terms": { "field": "tags.keyword" } },
    "over_time": { "date_histogram": { "field": "created_at", "interval": "day" } }
  }
}
```

**Why OpenSearch wins here**:
- **Analysers**: Language-specific tokenisation, stemming, stop-word removal — PostgreSQL's `tsvector` is basic by comparison
- **Highlighting**: Built-in hit highlighting shows exactly where the search term appears in the conversation
- **Aggregations**: Date histograms, term facets, significant terms — all computed server-side in a single query
- **Fuzzy matching**: `fuzziness: "AUTO"` handles typos in user searches
- **BM25 scoring**: Relevance ranking out of the box

**PostgreSQL alternative**: `plainto_tsquery()` + GIN index works but requires manual implementation of faceting, highlighting, and fuzzy matching.

---

### Scenario 3: Massive Scale Horizontal Scaling (>100M messages)

**When conversation volume exceeds what a single PostgreSQL instance can handle.**

| Scale | Aurora PostgreSQL | OpenSearch |
|-------|------------------|------------|
| <1M messages | Excellent (single instance) | Overkill |
| 1M-10M messages | Good (read replicas, partitioning) | Good |
| 10M-100M messages | Requires sharding (Citus) or partitioning | Native horizontal scaling |
| >100M messages | Complex sharding required | Scales horizontally by adding nodes |

OpenSearch scales horizontally by design — add data nodes to increase both storage and query capacity. PostgreSQL scales vertically (bigger instance) and requires external sharding (Citus, pg_partman) for horizontal scale.

**Why OpenSearch wins here**:
- Add nodes to scale — no application-level sharding logic
- Data streams + ISM policies handle time-based rollover automatically
- Index-level partitioning is native (shards per index)
- Cross-cluster replication for geo-distributed reads

**PostgreSQL alternative**: Citus (distributed PostgreSQL) or pg_partman for time-based partitioning. Both add operational complexity.

---

### Scenario 4: Real-Time Conversation Analytics Dashboard

**When product teams need live dashboards on conversation patterns, topics, sentiment, and usage metrics.**

```
┌─────────────────────────────────────────────────────┐
│  Product Analytics Dashboard (OpenSearch Dashboards) │
│                                                      │
│  • Conversations per day (date histogram)             │
│  • Top discussed topics (term aggregation)            │
│  • Average conversation length (stats aggregation)    │
│  • Sentiment distribution (range aggregation)         │
│  • Active users per workspace (cardinality)           │
│  • Trending queries (significant terms)               │
│                                                      │
│  All from a single OpenSearch aggregation query       │
└─────────────────────────────────────────────────────┘
```

**Why OpenSearch wins here**:
- **Native aggregations**: Date histograms, terms, cardinality, percentiles, significant terms — all computed at query time without pre-computation
- **OpenSearch Dashboards**: Built-in visualisation layer connected directly to the data
- **Real-time**: Index refresh interval (~1 second) means dashboards are near-real-time
- **No ETL**: Same index serves both conversation retrieval AND analytics

**PostgreSQL alternative**: Requires materialised views (refresh periodically), or a separate analytics pipeline (ETL to a data warehouse), or tools like Metabase/Grafana with SQL queries. All add latency and complexity.

---

### Scenario 5: Multi-Tenant SaaS with Document-Level Security

**When each tenant must only see their own conversations, enforced at the database level.**

OpenSearch's Security plugin provides **document-level security (DLS)** — you can define roles that automatically filter queries to only return documents matching a tenant ID:

```yaml
# Role definition for tenant "acme-corp"
index_permissions:
  - index_patterns: ["conversations"]
    dls: '{"term": {"tenant_id": "acme-corp"}}'
    allowed_actions: ["read"]
```

Every query from a user with this role is automatically filtered — no application-level filtering needed.

**Why OpenSearch wins here**:
- DLS is enforced at the query execution level — impossible to bypass from the application
- Field-level security (FLS) can hide sensitive fields per role
- Field masking can redact PII in real-time
- Works with SAML/OIDC for SSO integration

**PostgreSQL alternative**: Row-Level Security (RLS) provides equivalent functionality and is actually more mature. **This is one scenario where PostgreSQL may be equally good or better.**

---

### Scenario 6: Append-Only Conversation Logs with ISM Lifecycle

**When conversations are write-once, never updated, and need automated lifecycle management.**

OpenSearch's **Index State Management (ISM)** policies automate the entire lifecycle:

```json
{
  "policy": {
    "description": "Conversation lifecycle",
    "default_state": "hot",
    "states": [
      { "name": "hot", "actions": [ { "rollover": { "min_size": "50gb" } } ] },
      { "name": "warm", "actions": [ { "replica_count": 1 } ] },
      { "name": "cold", "actions": [ { "searchable_snapshot": {} } ] },
      { "name": "delete", "actions": [ { "delete": {} } ] }
    ]
  }
}
```

Combined with **data streams** (designed for append-only time-series data), this gives you:
- Automatic rollover when indices get large
- Automatic migration from hot → warm → cold → delete storage tiers
- Searchable snapshots for cold data (query without restoring)
- Zero application code for lifecycle management

**Why OpenSearch wins here**:
- ISM is fully automated — no cron jobs, no Lambda functions, no manual intervention
- Data streams handle append-only writes natively
- Searchable snapshots let you query cold data without rehydrating

**PostgreSQL alternative**: `pg_partman` for partition management + S3 archival. Requires custom scripting for tier management.

---

### Scenario 7: Conversational Search (RAG with Memory)

**When the primary use case is conversational search over documents — the chatbot IS a search interface.**

OpenSearch's **conversational search** feature (via search pipelines) stores conversation memory natively and uses it to improve subsequent search results:

```json
POST /legal-docs/_search
{
  "query": { "match": { "content": "tax penalty provisions" } },
  "ext": {
    "generative_qa_parameters": {
      "llm_model": "bedrock-claude",
      "llm_question": "What are the penalty provisions?",
      "memory_id": "previous-conversation-id",
      "context_size": 5
    }
  }
}
```

This automatically:
1. Retrieves the last 5 messages from memory
2. Performs vector + BM25 search on the document index
3. Passes context + history to the LLM
4. Stores the new interaction in memory
5. Returns the generated answer

**Why OpenSearch wins here**:
- Single API call handles retrieval + LLM + memory — no orchestration code
- Memory is co-located with the document index — zero network latency between retrieval and memory
- Context management (sliding window, summarisation) is built-in

---

### Scenario 8: Observability-First Chat (Logging + Search + Analytics)

**When conversation logs are treated as observability data — ingested via Data Prepper, queried alongside application logs.**

```
Application Logs → Data Prepper → OpenSearch
Chat Messages  → Data Prepper → OpenSearch
Agent Traces   → Data Prepper → OpenSearch
                                     │
                                     ▼
                          Single query across all three
```

**Why OpenSearch wins here**:
- Trace Analytics plugin correlates agent traces with conversation messages
- Data Prepper provides ingestion pipelines (enrichment, transformation, deduplication)
- Unified observability: see conversation messages alongside application logs and traces
- Piped aggregations for complex analytics across data types

---

### Decision Matrix: When to Choose OpenSearch for Conversation History

| # | Scenario | OpenSearch Advantage | Applicability to THIS Project |
|---|----------|---------------------|-------------------------------|
| 1 | OpenSearch-native agentic RAG | Zero integration code, built-in memory + context management | **Low** — project uses EKS Chat Engine, not ml-commons agents |
| 2 | Full-text search over conversations | Powerful analysers, highlighting, fuzzy matching, aggregations | **Medium** — could be useful if "search my history" becomes a feature |
| 3 | Massive scale (>100M messages) | Native horizontal scaling | **Low** — projected volume is well under 1M messages |
| 4 | Real-time analytics dashboard | Native aggregations + Dashboards | **Medium** — could add later if analytics requirements grow |
| 5 | Multi-tenant with DLS | Document-level security | **Low** — Aurora RLS is equally good and simpler for this case |
| 6 | Append-only with ISM lifecycle | Automated tier management | **Low** — Aurora partitioning + S3 archival already designed |
| 7 | Conversational search (RAG) | Single API for retrieval + LLM + memory | **Low** — project uses EKS orchestration, not search pipelines |
| 8 | Observability-first | Correlate chats with logs/traces | **Low** — separate observability stack already planned |

### Conclusion for This Project

For this project's specific requirements (EKS Chat Engine, ATO compliance, ACID, PITR, 7-year retention, RLS, ~$250/month budget), **none of the 8 scenarios above are strong enough to override the Aurora recommendation**. However, if any of these conditions change — particularly if the team decides to adopt the OpenSearch agent framework (Scenario 1) or needs powerful full-text search over history (Scenario 2) — this table provides the decision framework.

---

## Implementation Guidance

### Aurora Schema Example

```sql
-- Core schema
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    content_embedding vector(1536),  -- Adjust dimension for your model
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Optimize for sequential retrieval
CREATE INDEX messages_session_created_idx ON messages(session_id, created_at DESC);

-- Enable vector search (if needed)
CREATE INDEX messages_embedding_idx ON messages
    USING hnsw (content_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Tag support (many-to-many)
CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    color TEXT DEFAULT '#1976D2'
);

CREATE TABLE message_tags (
    message_id UUID REFERENCES messages(message_id) ON DELETE CASCADE,
    tag_id INT REFERENCES tags(tag_id),
    PRIMARY KEY (message_id, tag_id)
);
```

### Query Pattern Examples

```python
# Sequential conversation retrieval (primary pattern)
async def get_conversation(session_id: str) -> list[Message]:
    async with db.transaction():
        messages = await db.query("""
            SELECT message_id, role, content, created_at
            FROM messages
            WHERE session_id = $1
            ORDER BY created_at ASC
        """, session_id)
    return messages

# Semantic search (if needed)
async def search_similar(query_embedding: list[float], limit: int = 10):
    async with db.transaction():
        results = await db.query("""
            SELECT m.session_id, m.content, m.created_at,
                   m.content_embedding <=> $1 as distance
            FROM messages m
            ORDER BY m.content_embedding <=> $1
            LIMIT $2
        """, query_embedding, limit)
    return results

# Keyword search via tsvector
async def search_messages(query: str, limit: int = 10):
    async with db.transaction():
        results = await db.query("""
            SELECT m.session_id, m.content, m.created_at
            FROM messages m
            WHERE m.content_tsvector @@ plainto_tsquery($1)
            ORDER BY m.created_at DESC
            LIMIT $2
        """, query, limit)
    return results
```

**Only consider if**:
- Message volume >10M
- Real-time analytics becomes core requirement
- Full-text search over conversations is primary feature

```python
# Hybrid read routing (IF you add OpenSearch)
class MessageRepository:
    async def get_conversation(self, session_id: str) -> list[Message]:
        # Sequential reads from Aurora
        return await self._db.get_conversation(session_id)

    async def semantic_search(self, query: str, embedding: list[float]) -> list[Message]:
        # Semantic search from OpenSearch (IF added)
        return await self._opensearch.semantic_search(query, embedding)

    async def aggregate_by_date(self, days: int) -> dict:
        # Analytics from OpenSearch (IF added)
        return await self._opensearch.date_histogram(days)
```

**Phase 1: Add OpenSearch alongside Aurora**

```python
# Dual write
async def save_message(message: Message):
    # 1. Write to Aurora (primary)
    await db.execute("""
        INSERT INTO messages (message_id, session_id, role, content, content_embedding)
        VALUES ($1, $2, $3, $4, $5)
    """, message.id, message.session_id, message.role, message.content, message.embedding)

    # 2. Index in OpenSearch (fire and forget)
    await opensearch.index(
        index="messages",
        id=message.id,
        body={
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "content_embedding": message.embedding,
            "created_at": message.created_at
        }
    )
```

**Phase 2: Route reads based on query type**

```python
class MessageRepository:
    async def get_conversation(self, session_id: str) -> list[Message]:
        # Sequential reads from Aurora
        return await self._db.get_conversation(session_id)

    async def semantic_search(self, query: str, embedding: list[float]) -> list[Message]:
        # Semantic search from OpenSearch
        return await self._opensearch.semantic_search(query, embedding)

    async def aggregate_by_date(self, days: int) -> dict:
        # Analytics from OpenSearch
        return await self._opensearch.date_histogram(days)
```

**Phase 3: Add CDC for sync (optional)**

- Ensures OpenSearch catches up if writes fail
- Enables adding OpenSearch later without dual-write
- Use AWS DMS or custom Lambda handler

---

## Decision Checklist

Use this checklist to decide your architecture:

### Choose Aurora-Only if:
- [x] Primary access is sequential (by session, by time)
- [x] Conversations are derivations, not primary knowledge
- [x] Strong consistency required (ACID, compliance)
- [x] Cost-sensitive project
- [x] Prefer single-system operations

### Choose OpenSearch-Only if:
- [ ] Building agent entirely within OpenSearch ml-commons
- [ ] Conversations ARE the primary knowledge artifact
- [ ] No compliance requirements (no 7-year retention)
- [ ] Real-time aggregations are critical path
- [ ] Horizontal scaling requirement (>100M messages)

### Choose Hybrid if:
- [ ] System fundamentally requires BOTH ACID AND large-scale analytics
- [ ] Message volume >10M AND analytics is core requirement
- [ ] Can accept two-system operational complexity

**For Case Chat**: Aurora-only satisfies all requirements.

---

## Cost Comparison (Monthly Estimates)

### Scenario: 1M messages, 10K active sessions

| Component | Aurora | OpenSearch | Hybrid |
|-----------|--------|------------|--------|
| **Storage (1TB)** | $80 | $150 | $80 + $150 |
| **Compute (r6g.large)** | $100 | $120 | $100 + $120 |
| **I/O** | Included | Included | Included |
| **Data Transfer** | Included | Included | Included |
| **Total** | **~$180** | **~$270** | **~$450** |

**Note**: Hybrid costs more but provides both ACID and search capabilities. OpenSearch-only may require additional database for user/auth data.

---

## Appendix: Query Pattern Mapping

| Query Pattern | Aurora | OpenSearch |
|---------------|--------|------------|
| `Get session messages` | ✅ B-tree index | ⚠️ Filter by session_id |
| `Search by keyword` | ⚠️ GIN/TSVECTOR | ✅ Native text search |
| `Semantic similarity` | ✅ pgvector HNSW | ✅ k-NN |
| `Date histogram` | ⚠️ date_trunc + GROUP BY | ✅ Native aggregation |
| `Tag filtering` | ✅ JOIN or array ops | ✅ Terms query |
| `Faceted search` | ⚠️ Complex subqueries | ✅ Aggregations |
| `Relationship queries` | ✅ Native JOINs | ❌ Denormalize or app-side |
| `Point-in-time recovery` | ✅ Native | ⚠️ Snapshot/restore |
| `ACID transactions** | ✅ Full | ❌ None |

---

## Related Documents

- [04-session-lifecycle.md](./04-session-lifecycle.md) - Session lifecycle and TTL
- [01-chat-architecture.md](./01-chat-architecture.md) - Overall chat architecture
- [03-message-routing.md](./03-message-routing.md) - Message routing and orchestrator
- [12-high-level-design.md](./12-high-level-design.md) - AWS services catalog

---

## Change History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-22 | Initial research document with Aurora vs OpenSearch comparison, use case analysis, scenario-based recommendations, and implementation guidance |
| 2.0.0 | 2026-04-22 | Added comprehensive OpenSearch Conversational Memory research (ml-commons plugin, legacy memory system, agentic memory system, context management), recommendation matrix for hybrid architecture, sources from OpenSearch official docs and blog posts |
| 3.0.0 | 2026-04-22 | Added "What Is the OpenSearch ML-Commons Framework" section — explains the six pillars of ml-commons, two modes of operation (model hosting vs agent framework), available agent types and tools, and the critical architecture decision between external orchestration and OpenSearch-native agents |
| 4.0.0 | 2026-04-22 | Added "When OpenSearch IS the Right Choice for Conversation History" — comprehensive research of 8 specific scenarios where OpenSearch beats Aurora for conversation storage (native agentic RAG, full-text search, massive scale, real-time analytics, multi-tenant DLS, ISM lifecycle, conversational search, observability-first), with applicability assessment for this project |
| 5.0.0 | 2026-04-22 | Removed phased approach language — updated implementation guidance to focus on Aurora-first, clarified hybrid pattern as "only if requirements fundamentally change," updated decision checklist to emphasize that Aurora-only satisfies all Case Chat requirements |
