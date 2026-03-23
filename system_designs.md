# Case Assistant: System Design (Conceptual Architecture)

**Domain**: Tax Law (100% Focus)
**Document Version**: 2.0.0
**Date**: 2026-03-23
**Author**: Principal AI Engineer
**Status**: Production Architecture Specification
**Audience**: Engineering, Product, Architecture Teams

> **NOTE**: This document describes the conceptual architecture without AWS-specific implementation details. For AWS deployment specifics, see [system_designs_aws.md](./system_designs_aws.md).

> **DOMAIN SCOPE**: This system is designed **exclusively for tax law** - federal and state tax codes, IRS regulations, tax court cases, and tax-related legal documents.

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
   - 1.1 Chat Application Architecture (Conceptual)
   - 1.2 Chat Conversation Flow
   - 1.3 Document Ingestion Pipeline (Conceptual)
   - 1.4 Message Types and Routing
   - 1.5 Session Lifecycle (Conceptual)
   - 1.6 Evaluation Strategy (Conceptual)
   - 1.7 Core Component Descriptions
   - 1.8 Data Flow Overview
   - 1.9 Technology Mapping Overview
2. [Document Ingestion Flow](#2-document-ingestion-flow)
3. [Chat Service Flow](#3-chat-service-flow)
4. [Evaluation and Observability Flow](#4-evaluation-and-observability-flow)
5. [Session and Data Lifecycle](#5-session-and-data-lifecycle)
6. [Security and Compliance](#6-security-and-compliance)
7. [Technology Mapping](#7-technology-mapping)

---

**Related Documents**:
- [system_designs_aws.md](./system_designs_aws.md) - AWS-specific implementation details
- [evaluation_strategy.md](./evaluation_strategy.md) - Evaluation framework and gold dataset

---

## 1. High-Level Architecture

### 1.1 Chat Application Architecture (Conceptual)

```mermaid
graph TB
    subgraph "Chat Application - Logical Architecture"
        subgraph "Client Layer"
            WEB[Web Application<br>React SPA]
            MOBILE[Mobile Apps<br>iOS / Android]
        end

        subgraph "Connection Layer"
            API[REST API<br>HTTP/HTTPS]
            WS[WebSocket API<br>Real-time bidirectional]
            AUTH[Authentication Service<br>JWT Tokens]
        end

        subgraph "Application Layer"
            CONN_MGR[Connection Manager<br>WebSocket connections<br>Session management]
            CHAT_ENGINE[Chat Engine<br>Message processing<br>Conversation logic]
            SESSION_MGR[Session Manager<br>Temporary session lifecycle<br>Auto-cleanup]
            DOC_MGR[Document Manager<br>Upload / Processing / Retrieval]
        end

        subgraph "Intelligence Layer"
            RETRIEVER[Retriever<br>Hybrid search<br>Vector + Keyword]
            SYNTHESIZER[Synthesizer<br>LLM integration<br>Response generation]
            EXTRACTOR[Fact Extractor<br>Structured data extraction<br>JSON/CSV output]
            VALIDATOR[Citation Validator<br>Source verification<br>Accuracy checking]
        end

        subgraph "Storage Layer"
            VECTOR_STORE[(Vector Database<br>Embeddings + Metadata<br>Per-session indices)]
            DOC_STORE[(Document Storage<br>Original files<br>Processed chunks)]
            SESSION_STORE[(Session Store<br>Conversation history<br>User messages + AI responses)]
            METADATA_STORE[(Metadata Store<br>Session info<br>Document tracking<br>Status)]
        end

        subgraph "Background Processing"
            INGESTION[Document Ingestion Pipeline<br>Extract → Chunk → Embed<br>Async processing]
            CLEANUP[Cleanup Service<br>Session expiration<br>Auto-deletion]
        end
    end

    WEB --> API
    WEB --> WS
    MOBILE --> API
    MOBILE --> WS

    API --> AUTH
    WS --> AUTH

    AUTH --> CONN_MGR
    CONN_MGR --> CHAT_ENGINE
    CHAT_ENGINE --> SESSION_MGR

    CHAT_ENGINE --> DOC_MGR
    DOC_MGR --> INGESTION

    CHAT_ENGINE --> RETRIEVER
    RETRIEVER --> SYNTHESIZER
    SYNTHESIZER --> VALIDATOR

    RETRIEVER --> VECTOR_STORE
    RETRIEVER --> DOC_STORE
    SYNTHESIZER --> SESSION_STORE

    CHAT_ENGINE --> METADATA_STORE
    DOC_MGR --> METADATA_STORE
    SESSION_MGR --> METADATA_STORE

    INGESTION --> VECTOR_STORE
    INGESTION --> DOC_STORE
    CLEANUP --> VECTOR_STORE
    CLEANUP --> DOC_STORE
    CLEANUP --> SESSION_STORE
    CLEANUP --> METADATA_STORE

    style CHAT_ENGINE fill:#4CAF50
    style RETRIEVER fill:#2196F3
    style SYNTHESIZER fill:#9C27B0
    style VECTOR_STORE fill:#FF9800
    style SESSION_STORE fill:#FFEB3B
```

### 1.2 Chat Conversation Flow

```mermaid
sequenceDiagram
    participant User
    participant ChatApp as Chat Application
    participant Session as Session Manager
    participant Retriever as Document Retriever
    participant LLM as LLM Service
    participant Validator as Citation Validator
    participant Storage as Storage

    Note over User,Storage: Session Initialization
    User->>ChatApp: Connect to chat
    ChatApp->>Session: Create session
    Session->>Storage: Initialize session storage
    Session-->>ChatApp: Session ready

    Note over User,Storage: Conversation Start
    User->>ChatApp: Upload legal document
    ChatApp->>Storage: Store document
    ChatApp->>Session: Trigger ingestion

    Note over User,Storage: Message 1 - Initial Query
    User->>ChatApp: "What are the key dates in this contract?"
    ChatApp->>Session: Store user message
    ChatApp->>Retriever: Search for relevant content
    Retriever->>Storage: Query vector store
    Storage-->>Retriever: Return relevant chunks
    Retriever-->>ChatApp: Retrieved context

    ChatApp->>LLM: Generate response with context
    LLM-->>ChatApp: Stream response tokens
    ChatApp->>Validator: Validate citations (async)
    Validator->>Storage: Fetch source documents
    Storage-->>Validator: Return source text
    Validator-->>ChatApp: Citations validated

    ChatApp->>Session: Store assistant message + citations
    ChatApp-->>User: Stream complete response

    Note over User,Storage: Message 2 - Follow-up
    User->>ChatApp: "What about payment terms?"
    ChatApp->>Session: Store user message
    ChatApp->>Retriever: Search with conversation context
    Retriever->>Storage: Query with refinement
    Storage-->>Retriever: Payment-related chunks
    Retriever-->>ChatApp: Retrieved context

    ChatApp->>LLM: Generate contextual response
    LLM-->>ChatApp: Stream response
    ChatApp->>Session: Store conversation turn
    ChatApp-->>User: Stream response

    Note over User,Storage: Session End
    User->>ChatApp: Disconnect / Close
    ChatApp->>Session: Mark session inactive
    Session->>Storage: Persist conversation history
    Storage-->>Session: Session saved (user can return)
```

### 1.3 Document Ingestion Pipeline (Conceptual)

```mermaid
graph TB
    subgraph "Document Ingestion - Logical Flow"
        subgraph "Upload Stage"
            USER[User uploads document]
            VALIDATE[Validate file<br>Type, size, format<br>SHA-256 hash check]
            DEDUP{Duplicate?<br>Check hash}
            STORE[Store raw document<br>S3 with metadata]
        end

        subgraph "Extraction Stage - Adaptive Parser Selection"
            ANALYZE[Analyze Page Structure<br>Detect tables<br>Check complexity]
            TABLE_CHECK{Table Detected?<br>Page-by-page analysis}
            SIMPLE[Text-Only Pages<br>Standard parser<br>Textract/PyMuPDF]
            COMPLEX[Table Pages<br>VLM-based parser<br>LlamaParse/Bedrock + GPU]
            MERGE[Merge Results<br>Combine text+table pages<br>Unified output]
        end

        subgraph "Delta Detection (Reupload)"
            DELTA_CHECK{Reupload?<br>Same file hash}
            PAGE_HASH[Compare Page Hashes<br>Identify changed pages]
            DELETE_OLD[Delete Old Vectors<br>Only changed pages]
            KEEP_SAME[Keep Existing Vectors<br>Unchanged pages]
        end

        subgraph "Chunking Stage"
            PAGE_SPLIT[Split into Pages<br>Extract individual pages<br>Page-level granularity]
            CROSS_PAGE[Detect Cross-Page Text<br>Track text spanning pages<br>Continuity markers]
            STRATEGY[Apply Chunking Strategy<br>Header-based or Parent-Child<br>Page-by-page processing]
            META[Add Metadata<br>Document ID, page numbers<br>Chunk type, position<br>Cross-page links]
        end

        subgraph "Embedding Stage"
            EMBED[Generate Embeddings<br>Bedrock Titan<br>Batch processing]
            BATCH[Batch Processing<br>Process chunks in batches<br>Optimize throughput]
        end

        subgraph "Indexing Stage"
            INDEX[Index in Vector Store<br>Per-session index<br>Hybrid: vector + keyword]
            VERIFY[Verify Indexing<br>Validate all chunks indexed<br>Quality check]
        end

        subgraph "Completion Stage"
            STATUS[Update Status<br>Mark document: READY<br>Notify user]
            TTL[Set TTL<br>7-day inactivity timer<br>Auto-extend on access]
        end
    end

    USER --> VALIDATE
    VALIDATE --> DEDUP
    DEDUP -->|Existing| RETURN[Return existing chunks<br>Skip reprocessing]
    DEDUP -->|New| STORE
    STORE --> ANALYZE

    ANALYZE --> TABLE_CHECK
    TABLE_CHECK -->|No table| SIMPLE
    TABLE_CHECK -->|Table detected| COMPLEX
    SIMPLE --> MERGE
    COMPLEX --> MERGE

    MERGE --> DELTA_CHECK
    DELTA_CHECK -->|Reupload| PAGE_HASH
    PAGE_HASH --> DELETE_OLD
    PAGE_HASH --> KEEP_SAME
    DELETE_OLD --> PAGE_SPLIT
    KEEP_SAME --> INDEX
    DELTA_CHECK -->|New upload| PAGE_SPLIT

    PAGE_SPLIT --> CROSS_PAGE
    CROSS_PAGE --> STRATEGY
    STRATEGY --> META
    META --> EMBED
    EMBED --> BATCH
    BATCH --> INDEX
    VERIFY --> STATUS
    STATUS --> TTL

    style DEDUP fill:#FFEB3B
    style ANALYZE fill:#2196F3
    style COMPLEX fill:#9C27B0
    style DELTA_CHECK fill:#FF9800
    style PAGE_HASH fill:#FF5722
```

**Why Page-Level Splitting? Table Detection Problem**:

The primary reason for splitting documents into pages is to **detect and handle tables separately** to preserve their structural integrity.

**The Table Chunking Problem**:

| Issue | Description | Example |
|-------|-------------|---------|
| **Broken Columns** | Text chunking splits mid-column | "Column A: Value A123..." → broken |
| **Lost Rows** | Row relationships destroyed | Header row separated from data rows |
| **Merged Cells** | Complex tables lose structure | Spans not recognized after split |
| **Nested Tables** | Tables within tables broken | Inner table isolated from context |

**Example of Broken Table Chunking**:

❌ **WRONG - Text-based splitting**:
```
Chunk 1: "| Name | Age |"
Chunk 2: "| John | 25 |"
Chunk 3: "| Jane | 30 |"
```
→ **Problem**: No column context, headers separated from data

✅ **CORRECT - VLM with GPU**:
```
Table Page → VLM processes as image → Extracts complete table with structure
```
→ **Solution**: Preserves column/row relationships, merged cells, formatting

**VLM + GPU Solution for Tables**:

```
Table Page
    ↓
[VLM Model with GPU]
    ├─ LlamaParse (Vision Model)
    ├─ Bedrock Multimodal (Claude)
    └─ Processes page as IMAGE
    ↓
Structured Table Output
    ├─ Column headers preserved
    ├─ Row mappings intact
    ├─ Merged cells detected
    └─ Nested tables handled
```

**Why GPU is Required**:
- **Image Processing**: Tables rendered as images need GPU inference
- **Complex Layout**: Merged cells, multi-level headers need compute
- **Accuracy**: GPU ensures precise cell boundary detection
- **Speed**: Batch processing of table pages faster with GPU

**Page-Level Decision Flow**:

```mermaid
graph TB
    PAGE[Extracted Page]

    TABLE_DETECT{Table Detected?<br>Vision-based check}

    TEXT_PATH[Text-Only Page]
    TABLE_PATH[Table Page]

    TEXT_CHUNK[Standard Text Chunking<br>Character/Word based]
    VLM_CHUNK[VLM + GPU Chunking<br>Image-based extraction]

    TEXT_OUT[Text Chunks<br>Fast, low cost]
    TABLE_OUT[Structured Table<br>Preserved integrity]

    PAGE --> TABLE_DETECT

    TABLE_DETECT -->|No table| TEXT_PATH
    TABLE_DETECT -->|Table found| TABLE_PATH

    TEXT_PATH --> TEXT_CHUNK
    TABLE_PATH --> VLM_CHUNK

    TEXT_CHUNK --> TEXT_OUT
    VLM_CHUNK --> TABLE_OUT

    style TABLE_DETECT fill:#FF9800
    style VLM_CHUNK fill:#9C27B0
    style TABLE_OUT fill:#4CAF50
```

**Table Detection Criteria**:

| Feature | Detection Method | Action |
|---------|-----------------|--------|
| **Grid lines** | Visual detection | Flag for VLM |
| **Tabular patterns** | Layout analysis | Flag for VLM |
| **Multiple columns** | Structure analysis | Flag for VLM |
| **Merged cells** | Visual complexity | Flag for VLM |
| **Headers + data rows** | Pattern matching | Flag for VLM |

**Benefits of Page-Level Table Detection**:

1. **Preserve Table Integrity** - No broken columns/rows
2. **GPU Efficiency** - Only table pages use expensive GPU resources
3. **Cost Optimization** - Text pages use cheaper text extraction
4. **Accuracy** - Tables extracted with proper structure
5. **Scalability** - Targeted GPU usage, not whole document

**Page-Level Chunking Process**:

```mermaid
graph TB
    subgraph "Page-Level Chunking Flow"
        DOC[PDF/DOC Document]
        PAGES[Extract Pages<br>Page 1, Page 2, ... Page N]

        subgraph "Page Processing Loop"
            PAGE[Single Page]

            subgraph "Table Detection - Primary Goal"
                TABLE_CHECK{Table<br>Detected?}
                TEXT_PROC[Text-Only Processing<br>Standard chunking]
                TABLE_PROC[VLM + GPU Processing<br>Table extraction]
            end

            CROSS[Cross-Page Detection<br>Check text continuity<br>Mark boundaries]
            CHUNK[Apply Chunking Strategy<br>Header-based or Parent-Child]
            META_TAG[Add Metadata<br>Page number, table flag<br>Cross-page links]
        end

        CHUNKS[Chunked Output<br>Text chunks + Table chunks<br>Cross-page linked]
    end

    DOC --> PAGES
    PAGES --> PAGE

    PAGE --> TABLE_CHECK
    TABLE_CHECK -->|No table| TEXT_PROC
    TABLE_CHECK -->|Table found| TABLE_PROC

    TEXT_PROC --> CROSS
    TABLE_PROC --> CROSS

    CROSS --> CHUNK
    CHUNK --> META_TAG
    META_TAG --> CHUNKS

    style TABLE_CHECK fill:#FF9800
    style TABLE_PROC fill:#9C27B0
    style TEXT_PROC fill:#4CAF50
```

**Cross-Page Text Handling**:

```mermaid
graph LR
    P1[Page 5<br>Last paragraph]
    P2[Page 6<br>First paragraph]

    DETECT{Text<br>Continues?}

    MERGE[Merge into<br>single chunk]
    SPLIT[Keep separate<br>add metadata]

    C1[Chunk with<br>pages 5-6]
    C2[Chunk 5<br>with metadata]
    C3[Chunk 6<br>with metadata]

    P1 --> DETECT
    P2 --> DETECT
    DETECT -->|Yes & small| MERGE
    DETECT -->|Yes & large| SPLIT
    DETECT -->|No| SPLIT

    MERGE --> C1
    SPLIT --> C2
    SPLIT --> C3

    style DETECT fill:#FF9800
    style MERGE fill:#4CAF50
    style SPLIT fill:#2196F3
```

**VLM + GPU Usage - Table Pages Only**:

The system uses **Vision Language Models (VLM) with GPU** for pages containing tables to preserve structural integrity:

| Page Type | Parser Used | GPU? | Cost | Examples |
|-----------|-------------|------|------|----------|
| **Text-only pages** | Textract/PyMuPDF | No | Low | Plain text contracts, letters, agreements |
| **Simple tables** | Textract Tables | No | Medium | Basic 2-column tables, simple lists |
| **Complex tables** | VLM (LlamaParse/Bedrock) | Yes | High | Merged cells, nested headers, multi-level tables |
| **Scanned docs** | Textract OCR | No | Medium | Image-based PDFs (no tables) |

**Table Detection Triggers VLM + GPU**:
- ✅ **Tables with merged cells** - Visual boundaries needed
- ✅ **Nested headers** - Multi-level column structure
- ✅ **Complex grid layouts** - Irregular cell sizes
- ✅ **Tables spanning pages** - Cross-page continuity
- ✅ **Financial tables** - Numbers, calculations, currencies
- ✅ **Legal tables** - Schedules, appendices, references

**Why GPU for Tables?**:

| Requirement | Why GPU is Needed |
|-------------|-------------------|
| **Image Processing** | Table pages processed as images |
| **Cell Boundary Detection** | Precise visual boundary detection |
| **Merged Cell Recognition** | Complex spatial relationships |
| **Multi-Level Headers** | Nested structure understanding |
| **Cross-Page Tables** | Continuity across page breaks |
| **Batch Processing** | Faster inference with GPU acceleration |

**Cost Optimization**:
- Page-level detection before VLM processing
- Only table pages use expensive GPU resources
- Text pages use cheaper text extraction
- ~60-70% cost savings vs. processing all pages with VLM

**Delta Update on Reupload**:

When same file is reuploaded:
1. Compare SHA-256 page hashes
2. Identify changed pages
3. Delete vectors ONLY from changed pages
4. Re-index only changed pages
5. Keep existing vectors from unchanged pages

**Benefit**: Faster reuploads, reduced embedding costs

**Page-Level Chunking with Cross-Page Tracking**:

The chunking process operates at **page-level granularity** for two critical reasons:

1. **PRIMARY: Table Detection** - Identify and route table pages to VLM+GPU
2. **SECONDARY: Delta Updates** - Enable efficient re-processing of changed pages

```
Document → Pages → Table Detection → Chunking → Vectors
                    ↓ (if table)
                  VLM + GPU
```

**Why Page-Level?**:
- **Table Integrity**: Detect tables before chunking to preserve structure
- **Targeted GPU Usage**: Only table pages use expensive VLM resources
- **Efficient Updates**: Re-process only changed pages on re-upload
- **Cross-Page Tracking**: Handle content spanning page boundaries

**Process Flow**:

1. **Page Extraction**
   - Split document into individual pages
   - Each page gets a unique page_id
   - Store page boundaries for reference

2. **Table Detection (PRIMARY GOAL)**
   - Analyze page structure for tables
   - Detect grid lines, tabular patterns
   - Check for merged cells, complex layouts
   - **If table found**: Route to VLM + GPU
   - **If no table**: Use standard text extraction

3. **Cross-Page Content Detection**
   - Detect when text/tables span across pages
   - Mark continuation relationships (e.g., "page 5 continued from page 4")
   - Track logical sentence boundaries across page breaks
   - Add metadata: `cross_page: true`, `continued_from: page_N`, `continues_to: page_N+1`

4. **Page-by-Page Chunking**
   - **Text pages**: Apply header-based or parent-child chunking
   - **Table pages**: VLM extracts structured table with preserved integrity
   - For cross-page content:
     - Option A: Merge split content into single chunk (if < max size)
     - Option B: Keep separate but add continuity metadata
   - Tag each chunk with source page number

5. **Metadata Enrichment**
   - Document ID, Session ID
   - Page number(s) (single or range for cross-page)
   - Content type: `text`, `table`, `cross_page_text`, `cross_page_table`
   - Chunk position in page
   - Cross-page flags and links
   - Table structure (for table chunks): columns, rows, merged cells

**Example**:

| Chunk | Content | Page | Type | Processing |
|-------|---------|------|------|------------|
| Chunk 1 | "The party of the first part..." | 5 | Text | Standard chunking |
| Chunk 2 | "Financial Schedule (table)" | 6 | Table | **VLM + GPU** |
| Chunk 3 | "| Year | Revenue |" | 6 | Table cell | **VLM extracted** |
| Chunk 4 | "| 2024 | $1.2M |" | 6 | Table cell | **VLM extracted** |
| Chunk 5 | "...hereby agrees to the terms..." | 6-7 | Cross-page text | Merged chunk |
| Chunk 6 | "...continued from previous page" | 7 | Cross-page text | `continued_from: 6` |

**Benefits**:
- **Table Integrity** (PRIMARY): No broken columns/rows, VLM preserves structure
- **Targeted GPU Usage**: Only table pages use expensive VLM resources
- **Targeted Updates**: Re-process only changed pages
- **Context Preservation**: Track content across page boundaries
- **Efficient Retrieval**: Search includes cross-page context
- **Cost Savings**: Skip re-embedding unchanged pages

### 1.4 Message Types and Routing

```mermaid
graph TB
    subgraph "Message Orchestrator - Chat Application"
        subgraph "Incoming Messages"
            MSG_CHAT[Chat Message<br>User question/comment<br>Needs intent classification]
            MSG_CMD[Command Message<br>/summarize, /extract<br>Special handling]
            MSG_DOC[Document Action<br>Upload/delete/download<br>File operations]
            MSG_SYS[System Message<br>Connection events<br>Session lifecycle]
        end

        subgraph "Orchestrator - Decision Before DB"
            ORCHESTRATOR[LLM Orchestrator<br>Intent Classification<br>Single LLM call determines:]
            INTENT[Query Intent:<br>abusive, greeting, vague, rag_query]
            SCOPE[Search Scope:<br>system_only, user_only, hybrid]
            DECISION[Routing Decision<br> BEFORE any DB access]
        end

        subgraph "Cost-Optimized Paths"
            PATH_GREET[Greeting Path<br>NO vector DB hit<br>NO LLM generation<br>Instant response]
            PATH_CLARIFY[Clarification Path<br>Ask user question<br>Max 2 rounds<br>THEN retrieval]
            PATH_REJECT[Reject Path<br>Abusive content<br>NO processing<br>Protect budget]
            PATH_RAG[Full RAG Path<br>Vector DB + LLM<br>Standard retrieval]
        end

        subgraph "Post-Orchestration Processing"
            PATH_CHAT[Chat Processing<br>Retrieval → LLM → Stream<br>Only after routing]
            PATH_CMD[Command Processing<br>Specialized handlers<br>Structured output]
            PATH_DOC[Document Processing<br>Async pipeline<br>Status updates]
            PATH_SYS[System Processing<br>Session management<br>Notifications]
        end

        subgraph "Response Types"
            RESP_STREAM[Streaming Response<br>Token-by-token<br>Real-time delivery]
            RESP_STRUCTURED[Structured Data<br>JSON/CSV<br>Fact extraction]
            RESP_STATUS[Status Update<br>Progress indicator<br>Document ready]
            RESP_ERROR[Error Response<br>User-friendly<br>Recovery options]
        end
    end

    MSG_CHAT --> ORCHESTRATOR
    MSG_CMD --> ORCHESTRATOR
    MSG_DOC --> ORCHESTRATOR
    MSG_SYS --> ORCHESTRATOR

    ORCHESTRATOR --> INTENT
    INTENT --> SCOPE
    SCOPE --> DECISION

    DECISION -->|greeting| PATH_GREET
    DECISION -->|vague| PATH_CLARIFY
    DECISION -->|abusive| PATH_REJECT
    DECISION -->|rag_query| PATH_RAG

    PATH_GREET --> RESP_STREAM
    PATH_CLARIFY -->|clarified| PATH_RAG
    PATH_REJECT --> RESP_ERROR
    PATH_RAG --> PATH_CHAT

    MSG_CMD --> PATH_CMD
    MSG_DOC --> PATH_DOC
    MSG_SYS --> PATH_SYS

    PATH_CHAT --> RESP_STREAM
    PATH_CMD --> RESP_STRUCTURED
    PATH_DOC --> RESP_STATUS
    PATH_SYS --> RESP_STATUS
    PATH_CMD --> RESP_ERROR
    PATH_CHAT --> RESP_ERROR

    style ORCHESTRATOR fill:#9C27B0
    style INTENT fill:#FF9800
    style SCOPE fill:#FF9800
    style DECISION fill:#FF9800
    style PATH_GREET fill:#4CAF50
    style PATH_CLARIFY fill:#2196F3
    style PATH_REJECT fill:#F44336
    style PATH_RAG fill:#9C27B0
```

**What is an Orchestrator?**

An **Orchestrator** is a message routing component that uses LLM-based intent classification to determine the appropriate processing path **before** any expensive operations (vector DB queries, LLM generation) are executed.

**Key Characteristics**:

| Aspect | Description |
|--------|-------------|
| **Decision Point** | First component that processes every incoming message |
| **Single LLM Call** | Determines intent + scope + routing in one efficient call |
| **Cost Optimization** | Routes ~30% of messages to low-cost paths (greetings, clarifications) |
| **Pre-DB Classification** | Makes routing decisions BEFORE hitting vector database |
| **Not an Agent** | It's a router/classifier, not an autonomous decision-maker |

**Orchestrator vs Agent**:

| Orchestrator | Agent |
|--------------|-------|
| Routes messages based on intent | Makes autonomous decisions |
| Single decision point per message | Multi-step reasoning chains |
| Pre-determined paths | Dynamic behavior |
| Fast, predictable | Slower, exploratory |
| Best for: Chat applications | Best for: Complex workflows |

**Example Flow**:

```
User message: "hi"
  ↓
Orchestrator (LLM call): Intent=greeting, Scope=none
  ↓
Routing Decision: Greeting path
  ↓
Response: "Hello! How can I help?" (NO vector DB hit, NO LLM generation)
  ↓
Cost: $0 (saved vector DB + LLM call)
```
```mermaid
graph TB
    ROUTER[Message Router]
    PRIORITY[Priority Classification]
    PATH_CHAT[Chat Processing]
    PATH_CMD[Command Processing]
    PATH_DOC[Document Processing]
    PATH_SYS[System Processing]
    RESP_STREAM[Stream Response]
    RESP_STRUCTURED[Structured Response]
    RESP_STATUS[Status Update]
    RESP_ERROR[Error Response]

    ROUTER --> PRIORITY

    PRIORITY --> PATH_CHAT
    PRIORITY --> PATH_CMD
    PRIORITY --> PATH_DOC
    PRIORITY --> PATH_SYS

    PATH_CHAT --> RESP_STREAM
    PATH_CMD --> RESP_STRUCTURED
    PATH_DOC --> RESP_STATUS
    PATH_SYS --> RESP_STATUS
    PATH_CMD --> RESP_ERROR
    PATH_CHAT --> RESP_ERROR

    style ROUTER fill:#9C27B0
    style PRIORITY fill:#FF9800
    style PATH_CHAT fill:#4CAF50
    style PATH_CMD fill:#2196F3
    style PATH_DOC fill:#FFEB3B
```

### 1.5 Session Lifecycle (Conceptual)

```mermaid
stateDiagram-v2
    [*] --> Initializing: User creates session
    Initializing --> Active: Session ready

    state Active {
        [*] --> Uploading: User uploads doc
        [*] --> Chatting: User sends message
        [*] --> Idle: No activity
        [*] --> Paused: User leaves session

        Uploading --> Chatting: Upload complete
        Chatting --> Chatting: Continue conversation
        Chatting --> Idle: User stops typing
        Idle --> Chatting: User resumes
        Idle --> Paused: User navigates away
        Paused --> Chatting: User returns to session
    }

    Active --> Inactive: 7 days no activity
    Inactive --> Cleanup: 30 day grace period

    Cleanup --> Deleting: Delete resources
    Deleting --> [*]: Data removed

    Active --> Deleting: User deletes session
    Chatting --> Deleting: User manual delete
    Paused --> Deleting: User deletes session

    note right of Active
        SESSION LIFECYCLE:
        - Session persists indefinitely
        - User can return anytime
        - No auto-deletion while active
        - Documents tracked per session
    end note

    note right of Inactive
        DOCUMENT TTL:
        - Documents: 7 days inactive
        - Auto-extend on activity
        - Vectors deleted with docs
        - Conversation history persists
    end note

    note right of Cleanup
        DATA DELETION POLICY:
        Documents deleted after:
        - 7 days inactivity
        - OR user manual delete

        Conversation persists:
        - Chat history retained
        - Session metadata kept
        - User can view past conversations
        - Only documents are purged
    end note
```

### 1.6 Evaluation Strategy (Conceptual)

Evaluation ensures the **tax law AI system** produces accurate, trustworthy, and compliant outputs. Tax law AI requires a **defensive, attribution-first** approach where errors can result in incorrect tax advice, penalties, or legal liability.

**Evaluation Philosophy**:

| Aspect | General Chatbot | Tax Law AI |
|--------|----------------|-------------|
| **Error Impact** | User inconvenience | Incorrect tax advice, IRS penalties, legal liability |
| **Attribution** | Optional | Mandatory (IRC sections, tax court citations required) |
| **Accuracy** | ~80-90% acceptable | ≥95% required (tax codes are precise) |
| **Hallucinations** | Minor annoyance | Zero tolerance (cannot invent tax laws) |
| **Testing** | Basic QA tests | Multi-layered validation against tax code |

#### Three-Tier Evaluation Model

```mermaid
graph TB
    subgraph "Evaluation Layers - Defense in Depth"
        T1[Tier 1: Automated Continuous<br>Every commit<br>Smoke tests, RAG quality<br>CI/CD System]
        T2[Tier 2: Scheduled Batch<br>Daily/Weekly<br>Gold dataset, regression<br>Evaluation Service]
        T3[Tier 3: Manual Expert<br>Monthly/Quarterly<br>Legal accuracy, adversarial<br>Legal Professionals]
    end

    T1 --> T2
    T2 --> T3

    style T1 fill:#4CAF50
    style T2 fill:#FF9800
    style T3 fill:#F44336
```

**Tier Comparison**:

| Tier | Frequency | Scope | Owner | Pass Criteria |
|------|-----------|-------|-------|--------------|
| **Tier 1: Automated Continuous** | Every commit | Smoke tests, basic RAG quality | CI/CD System | 100% tests pass, precision ≥90% |
| **Tier 2: Scheduled Batch** | Daily/Weekly | Gold dataset, regression testing | Evaluation Service | Precision ≥95%, recall ≥90% |
| **Tier 3: Manual Expert** | Monthly/Quarterly | Legal accuracy, edge cases | Legal Professionals | Qualitative approval |

#### Gold Dataset Approach

The **Gold Dataset** provides ground truth for systematic evaluation:

```mermaid
graph TB
    subgraph "Gold Dataset Composition"
        DOCS[500 Legal Documents<br>Diverse domains<br>Varying complexity]

        subgraph "Document Types"
            CONT[IRC Sections<br>Tax Code<br>Revenue Procedures]
            EVID[IRS Regulations<br>Revenue Rulings<br>Private Letter Rulings]
            LEGAL[Tax Court Cases<br>Tax Court Memoranda<br>IRS Publications]
        end

        ANNOT[Human Annotated<br>Ground truth facts<br>Test cases<br>Expected outputs]

        TEST[Test Cases<br>1,500 queries<br>Multiple query types]
    end

    DOCS --> ANNOT
    ANNOT --> TEST

    style DOCS fill:#2196F3
    style ANNOT fill:#FF9800
    style TEST fill:#4CAF50
```

**Gold Dataset Characteristics**:

| Characteristic | Value |
|----------------|-------|
| **Total Documents** | 500 tax law documents |
| **Test Cases** | ~1,500 (3 per document) |
| **Tax Law Domains** | Federal tax code, IRS regulations, Tax court cases, State tax codes |
| **Document Types** | IRC sections, Revenue Rulings, Tax Court opinions, IRS forms, Private letter rulings |
| **Complexity Levels** | Simple (40%), Medium (40%), Complex (20%) |
| **Annotation** | 100% human-verified by tax professionals |
| **Ground Truth Facts** | ~10,000 facts (tax sections, regulations, case citations, tax amounts, deadlines) |

#### LLM-as-Judge Framework

**Concept**: Use a high-quality LLM to evaluate system outputs against ground truth with **strict content confinement**.

```mermaid
graph TB
    subgraph "LLM-as-Judge Evaluation Flow"
        INPUT[System Output<br>+ Ground Truth<br>+ Retrieved Context]

        JUDGE[LLM Judge<br>High-quality model<br>Structured evaluation]

        EVAL[Four Evaluation Categories<br>Safety, Quality<br>Truthfulness, Retrieval]

        SCORE[Quality Scores<br>Binary Yes/No per criterion<br>Aggregate metrics]

        PASS{Meets Threshold?<br>Precision ≥95%<br>Hallucination ≤2%}

        REPORT[Evaluation Report<br>Per-test results<br>Category breakdown<br>Regression alerts]
    end

    INPUT --> JUDGE
    JUDGE --> EVAL
    EVAL --> SCORE
    SCORE --> PASS
    PASS -->|Yes| REPORT
    PASS -->|No| REPORT

    style JUDGE fill:#9C27B0
    style EVAL fill:#FF9800
    style PASS fill:#F44336
```

**Four Evaluation Categories** (expanded from basic approach):

```mermaid
graph TB
    subgraph "Comprehensive Evaluation Categories"
        BASE[LLM-as-Judge Evaluation]

        SAFETY[Safety Evaluation<br>Scope adherence<br>Bias detection<br>Harm prevention]

        QUALITY[Quality Evaluation<br>Relevance<br>Tone/Persona<br>Accuracy]

        TRUTH[Truthfulness Evaluation<br>Hallucination detection<br>Faithfulness<br>Attribution]

        RETR[Retrieval/RAG Evaluation<br>Context precision<br>Noise detection<br>PII leakage]
    end

    BASE --> SAFETY
    BASE --> QUALITY
    BASE --> TRUTH
    BASE --> RETR

    style SAFETY fill:#F44336
    style QUALITY fill:#4CAF50
    style TRUTH fill:#FF9800
    style RETR fill:#2196F3
```

**LLM Judge Responsibilities** (enhanced):

1. **Safety Evaluation**
   - **Scope Adherence**: Does response stay within tax law domain (IRC, regulations, tax court)?
   - **Bias & Harm**: Detect harmful bias in tax advice
   - **Tax Advice Boundaries**: Ensure appropriate disclaimers (not professional tax advice)
   - **Sensitive Topics**: Handle audits, penalties, tax debt appropriately

2. **Quality Evaluation**
   - **Relevance**: Directly relevant to user's tax question
   - **Tone/Persona**: Professional, empathetic, tax-appropriate
   - **Accuracy**: Tax-law sound advice (IRC citations, regulations)
   - **Clarity**: Understandable to non-tax professionals
   - **Completeness**: Addresses user's tax question fully

3. **Truthfulness Evaluation**
   - **Hallucination Detection** (3 types):
     - New facts not in source documents
     - Contradictions to source material
     - Fabricated legal citations
   - **Faithfulness**: Response entirely based on retrieved facts
   - **Attribution**: All claims properly sourced

4. **Retrieval/RAG Evaluation**
   - **Context Precision**: Enough relevant information retrieved
   - **Context Irrelevance**: No significant irrelevant chunks
   - **Context Sufficiency**: Information sufficient for complete answer
   - **Noisy Ratio**: Noise doesn't interfere with understanding
   - **Distractor Presence**: No semantically similar but incorrect chunks
   - **Context Utilization**: Active use of provided context
   - **PII Leakage**: Retrieved context doesn't expose PII
   - **Prompt Leakage**: Response doesn't repeat system instructions

**Judge Question Schema** (structured approach):

```json
{
  "type": "question",
  "question": "STRICTLY CONFINE YOUR EVALUATION to the content of the system_response. Does the response introduce any facts not present in the retrieved_context?",
  "category": "Truthfulness",
  "expected_answer": "No",
  "required_content": ["system_response", "retrieved_context"],
  "rationale": "Tax law AI must not hallucinate tax codes, regulations, or case law"
}
```

**Binary Yes/No Scale**:
- Every judge question has binary Yes/No answer
- Declared `expected_answer` for automated scoring
- Strict content confinement prevents external knowledge leakage

#### Key Evaluation Metrics

**Comprehensive Metric Hierarchy**:

```mermaid
graph TB
    subgraph "Evaluation Metrics Hierarchy"
        ALL[Overall Quality Score]

        subgraph "Category Scores"
            SAFE[Safety Score<br>Scope + Bias + Harm]
            QUAL[Quality Score<br>Relevance + Tone + Accuracy]
            TRUTH[Truthfulness Score<br>Hallucination + Faithfulness]
            RAG[Retrieval Score<br>Context + Utilization]
        end

        subgraph "Individual Metrics (20+)"
            S1[Scope Adherence]
            S2[Bias Detection]
            S3[Harm Prevention]

            Q1[Relevance]
            Q2[Tone Match]
            Q3[Legal Accuracy]
            Q4[Clarity]
            Q5[Completeness]

            T1[Hallucination Rate]
            T2[Faithfulness]
            T3[Attribution]

            R1[Context Precision]
            R2[Context Irrelevance]
            R3[Context Sufficiency]
            R4[Noisy Ratio]
            R5[Distractor Presence]
            R6[Context Utilization]
            R7[PII Leakage]
            R8[Prompt Leakage]
        end
    end

    ALL --> SAFE
    ALL --> QUAL
    ALL --> TRUTH
    ALL --> RAG

    SAFE --> S1
    SAFE --> S2
    SAFE --> S3

    QUAL --> Q1
    QUAL --> Q2
    QUAL --> Q3
    QUAL --> Q4
    QUAL --> Q5

    TRUTH --> T1
    TRUTH --> T2
    TRUTH --> T3

    RAG --> R1
    RAG --> R2
    RAG --> R3
    RAG --> R4
    RAG --> R5
    RAG --> R6
    RAG --> R7
    RAG --> R8

    style ALL fill:#9C27B0
    style SAFE fill:#F44336
    style QUAL fill:#4CAF50
    style TRUTH fill:#FF9800
    style RAG fill:#2196F3
```

**Legal Quality Metrics** (expanded):

**Operational Metrics**:

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Session Creation Success** | ≥99.9% | Core functionality must work |
| **Query Response Time (p95)** | <3 seconds | User experience |
| **Document Ingestion Success** | ≥99% | Users must be able to upload documents |

**Compliance Metrics**:

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Data Deletion Compliance** | 100% | Legal requirement |
| **Session Isolation** | 100% | Security requirement |
| **PII Leakage** | 0 incidents | Privacy requirement |

#### Observability and Trace Collection

**Concept**: Capture detailed traces of every query to understand what the system retrieved, how it processed information, and where it may have failed.

```mermaid
graph TB
    subgraph "Observability Pipeline"
        QUERY[User Query]

        subgraph "System Processing"
            RETRIEVE[Document Retrieval<br>Vector search + Keyword]
            RANK[Re-ranking<br>Fusion of results]
            LLMM[LLM Generation<br>RAG + Citations]
            RESPONSE[System Response]
        end

        TRACE[Observability Platform<br>Trace collection<br>Metadata extraction]

        subgraph "Trace Metadata"
            META_RETRIEVE[Retrieved documents<br>Page numbers<br>Relevance scores]
            META_TOOLS[Tool calls<br>Search queries<br>Filter criteria]
            META_CONTEXT[Context window<br>Token usage<br>Citations]
        end

        EVAL[Evaluation Data<br>Fetch traces<br>Build conversation history<br>Run LLM-as-Judge]
    end

    QUERY --> RETRIEVE
    RETRIEVE --> RANK
    RANK --> LLMM
    LLMM --> RESPONSE

    RETRIEVE --> TRACE
    RANK --> TRACE
    LLMM --> TRACE

    TRACE --> META_RETRIEVE
    TRACE --> META_TOOLS
    TRACE --> META_CONTEXT

    TRACE --> EVAL

    style TRACE fill:#2196F3
    style EVAL fill:#9C27B0
```

**Trace Metadata Collected**:

| Metadata Type | What It Captures | Evaluation Value |
|---------------|------------------|------------------|
| **Retrieved Documents** | Document IDs, page numbers, relevance scores | Evaluate retrieval quality |
| **Tool Calls** | Search queries, filters, database operations | Understand what system searched for |
| **Context Window** | Token usage, context size, truncation | Detect context overflow |
| **Citations** | Source locations, page references | Validate citation accuracy |
| **Timing** | Latency per component, total response time | Performance optimization |
| **Errors** | Failures, retries, fallbacks | Identify reliability issues |

**Data Cleaning Pipeline**:

```mermaid
graph LR
    subgraph "Trace Processing"
        RAW[Raw Traces<br>Multiple traces per turn]

        CLEAN[Data Cleaning Pipeline]

        EXTRACT[Extract Tool Calls<br>Search queries, retrievals<br>Filter operations]

        COLLAPSE[Collapse Traces<br>Aggregate multi-trace turns<br>First-non-empty for scalars<br>Combine-unique for arrays]

        HISTORY[Build Conversation History<br>Prior turns<br>Accumulated context]

        OUTPUT[Cleaned Dataset<br>Ready for evaluation<br>Structured CSV/JSON]
    end

    RAW --> CLEAN
    CLEAN --> EXTRACT
    EXTRACT --> COLLAPSE
    COLLAPSE --> HISTORY
    HISTORY --> OUTPUT

    style CLEAN fill:#FF9800
    style OUTPUT fill:#4CAF50
```

**Cleaned Dataset Schema**:

| Column | Description | Evaluation Use |
|--------|-------------|----------------|
| `session_id` | Unique conversation session | Track multi-turn conversations |
| `trace_id` | Observability trace IDs | Link to full traces |
| `user_query` | User's question | Input for evaluation |
| `system_response` | System's answer | Output for evaluation |
| `retrieved_documents` | Document IDs, pages | Evaluate retrieval quality |
| `retrieval_scores` | Relevance scores | Context precision analysis |
| `tool_calls` | Search/filter operations | Understand system behavior |
| `citations` | Source references | Citation accuracy check |
| `conversation_history` | Prior turns | Context handling evaluation |
| `latency_ms` | Response time | Performance metrics |
| `token_count` | Tokens used | Cost analysis |

#### Continuous Evaluation Pipeline

#### Test Case Categories

**Query Types**:

| Query Type | Description | Example | Evaluation Focus |
|------------|-------------|---------|------------------|
| **Fact Extraction** | Extract specific tax facts | "What are the key tax dates?" | Precision, Recall |
| **Summary** | Document summary | "Summarize this Tax Court opinion" | Completeness, Accuracy |
| **Cross-Document** | Multi-document queries | "Compare Section 199A and Section 162" | Synthesis, Citations |
| **Tax Law Reasoning** | Tax analysis | "What are the requirements for this deduction?" | Tax accuracy |
| **Adversarial** | Edge cases, attacks | "What if I don't report this income?" | Robustness, Hallucinations |

#### Persona-Driven Stress Testing

**Concept**: Simulate different user communication styles to test system robustness and adaptability.

```mermaid
graph TB
    subgraph "Persona-Driven Testing"
        PERSONA[Select User Persona]

        subgraph "Tax Law User Personas"
            STRESS[Stressed Taxpayer<br>Emotional, urgent<br>Auditor notice received]
            CPA[CPA/Tax Professional<br>Precise, technical<br>Complex tax questions]
            INDIV[Individual Taxpayer<br>Non-tax background<br>Confused by tax jargon]
            ATTORNEY[Tax Attorney<br>Formal, specific<br>Tax court procedures]
            IRS_AGENT[IRS Agent/Auditor<br>Procedural focus<br>Compliance checking]
        end

        SCENARIO[Apply to Test Scenarios<br>Fact extraction<br>Document analysis<br>Legal reasoning]

        EVAL[Persona-Specific Evaluation<br>Tone appropriateness<br>Clarity for persona<br>Handling style]
    end

    PERSONA --> STRESS
    PERSONA --> LAWER
    PERSONA --> PRO_SE
    PERSONA --> JUDGE

    STRESS --> SCENARIO
    LAWER --> SCENARIO
    PRO_SE --> SCENARIO
    JUDGE --> SCENARIO

    SCENARIO --> EVAL

    style PERSONA fill:#9C27B0
    style EVAL fill:#FF9800
```

**Persona Definitions for Tax Law AI**:

| Persona | Communication Style | Tests |
|---------|---------------------|-------|
| **Stressed Taxpayer** | Emotional, rushed, typos, incomplete | Can system extract facts from audit notice? |
| **CPA/Tax Professional** | Precise, tax terminology, complex | Can system handle technical tax questions? |
| **Individual Taxpayer** | Non-tax background, confused by jargon | Can system explain tax concepts simply? |
| **Tax Attorney** | Formal, specific, tax court procedures | Does system provide proper procedural guidance? |
| **IRS Agent/Auditor** | Procedural focus, compliance checking | Does system handle audit-related queries accurately? |
| **Efficient User** | Brief, direct, minimal context | Can system work with minimal information? |
| **Verbose User** | Long-winded, story-telling | Can system extract key tax facts from narrative? |
| **Skeptical User** | Challenging, adversarial | Does system maintain composure and accuracy? |
| **Multi-Document User** | References many tax forms/cases | Can system synthesize across documents? |
| **Follow-up User** | Asks series of related tax questions | Does system maintain context? |

**Persona-Based Evaluation Criteria**:

```mermaid
graph LR
    subgraph "Persona-Specific Metrics"
        TONE[Tone Appropriateness<br>Match user's emotional state<br>Professional but empathetic]

        CLARITY[Clarity for Persona<br>Simple language for non-lawyers<br>Technical for attorneys]

        ROBUSTNESS[Robustness<br>Handle incomplete input<br>Correct misunderstandings]

        ACCURACY[Accuracy<br>Maintain factual correctness<br>Regardless of user style]
    end

    style TONE fill:#4CAF50
    style CLARITY fill:#2196F3
    style ROBUSTNESS fill:#FF9800
    style ACCURACY fill:#F44336
```

**Example Persona Test**:

| Persona | User Query | System Should |
|---------|-----------|--------------|
| **Stressed Taxpayer** | "I got an IRS audit notice wat do I do HELP" | Calm response, extract notice details, explain audit process |
| **CPA** | "What are the Section 199A deduction limitations for specified service trades?" | Technical tax analysis, precise IRC citations |
| **Individual Taxpayer** | "I don't understand 'adjusted gross income' - what is it?" | Simple explanation, examples, plain language |
| **Tax Attorney** | "Cite controlling precedent for the economic substance doctrine in tax court" | Formal response, precise tax court citations |
| **IRS Agent** | "What documentation supports this Schedule C deduction?" | Procedural response, documentation requirements, compliance standards |

#### Compliance Evaluation

Tax law AI systems must validate compliance requirements:

```mermaid
graph TB
    subgraph "Compliance Evaluation"
        COMP[Compliance Tests]

        subgraph "Data Deletion"
            DEL[Delete Session Test<br>Verify vectors removed<br>Verify documents deleted<br>Verify metadata purged]
        end

        subgraph "Session Isolation"
            ISO[Cross-Session Test<br>Query from Session A<br>Cannot access Session B data<br>100% isolation required]
        end

        subgraph "PII Protection"
            PII[PII Scan Test<br>Scan responses for PII<br>Zero leaks allowed<br>Redaction validation]
        end

        REPORT[Compliance Report<br>Pass/Fail each test<br>100% required for compliance]
    end

    COMP --> DEL
    COMP --> ISO
    COMP --> PII

    DEL --> REPORT
    ISO --> REPORT
    PII --> REPORT

    style DEL fill:#4CAF50
    style ISO fill:#FF9800
    style PII fill:#F44336
```

**Compliance Requirements**:

| Requirement | Test Method | Pass Criteria |
|-------------|-------------|---------------|
| **Data Deletion** | Delete session, verify cleanup | 0 vectors, 0 documents, 0 metadata remain |
| **Session Isolation** | Cross-session queries | 0% data leakage between sessions |
| **PII Protection** | PII scan on responses | 0 PII leaks |
| **Retention Policy** | Verify 7-day document TTL | Documents auto-deleted after inactivity |

#### Evaluation-Driven Development

**Development Workflow**:

1. **Write Test Case First**
   - Define query and expected output
   - Add to gold dataset
   - Establish baseline metrics

2. **Implement Feature**
   - Build functionality
   - Run automated evaluation (Tier 1)

3. **Validate Against Gold Dataset**
   - Run LLM-as-Judge evaluation
   - Verify metrics meet thresholds
   - Fix regressions

4. **Manual Review (Critical Features)**
   - Legal professional review
   - Adversarial testing
   - Edge case validation

**Regression Prevention**:

- Every commit runs Tier 1 tests
- Daily runs full gold dataset (Tier 2)
- Any degradation blocks deployment
- Trends tracked over time
- Manual review for significant changes

### 1.7 Core Component Descriptions

#### Connection Manager
- **Purpose**: Manages WebSocket connections and real-time communication
- **Responsibilities**:
  - Accept and authenticate WebSocket connections
  - Maintain connection registry (active sessions)
  - Route messages to appropriate handlers
  - Handle connection lifecycle (connect, disconnect, heartbeat)
  - Manage message queues per connection
  - Broadcast real-time updates (status changes, errors)

#### Chat Engine
- **Purpose**: Core orchestration for chat conversations
- **Responsibilities**:
  - Process incoming messages
  - Coordinate conversation flow
  - Manage conversation state and history
  - Route to retriever for document queries
  - Invoke LLM for response generation
  - Stream responses back to client
  - Handle multi-turn context management

#### Session Manager
- **Purpose**: Manage temporary session lifecycle
- **Responsibilities**:
  - Create ephemeral sessions (4-16 hour lifetime)
  - Track session expiration and extensions
  - Schedule automatic cleanup
  - Isolate data between sessions
  - Provide session-scoped resources (vector index, storage prefix)
  - Enforce zero data retention policy

#### Document Manager
- **Purpose**: Handle document upload, processing, and retrieval
- **Responsibilities**:
  - Accept file uploads via presigned URLs
  - Trigger ingestion pipeline
  - Track document processing status
  - Provide document metadata
  - Enable document deletion
  - Manage per-document access control

#### Retriever
- **Purpose**: Find relevant content from uploaded documents
- **Responsibilities**:
  - Hybrid search (vector + keyword)
  - Reciprocal Rank Fusion (RRF)
  - Context-aware retrieval (conversation history)
  - Query rewriting for follow-up questions
  - Reranking and result filtering
  - Citation extraction

#### Synthesizer
- **Purpose**: Generate AI responses using LLM
- **Responsibilities**:
  - Build conversation context
  - Assemble retrieved documents
  - Invoke LLM with appropriate prompts
  - Stream responses in real-time
  - Handle different query types (summary, extraction, chat)
  - Manage conversation tone and style

#### Fact Extractor
- **Purpose**: Extract structured data from documents
- **Responsibilities**:
  - Identify fact types (dates, parties, amounts, deadlines)
  - Generate structured output (JSON/CSV)
  - Provide confidence scores
  - Handle cross-document synthesis
  - Export results in multiple formats

#### Citation Validator
- **Purpose**: Ensure response accuracy and attribution
- **Responsibilities**:
  - Verify citation accuracy
  - Check document existence
  - Validate page numbers
  - Confirm text snippets match sources
  - Assess relevance of citations
  - Filter invalid citations

### 1.8 Data Flow Overview

```mermaid
graph LR
    subgraph "Request Flow"
        USER[User Message] --> ROUTER[Message Router]
        ROUTER --> |Chat| RETRIEVE[Retrieve Documents]
        ROUTER --> |Command| EXTRACT[Extract Facts]
        ROUTER --> |Document| UPLOAD[Handle Upload]
    end

    subgraph "Processing Flow"
        RETRIEVE --> SEARCH[Vector + Keyword Search]
        SEARCH --> RRF[Reciprocal Rank Fusion]
        RRF --> ASSEMBLE[Assemble Context]
        ASSEMBLE --> LLM[Generate Response]
        LLM --> VALIDATE[Validate Citations]
        VALIDATE --> STREAM[Stream Response]
    end

    subgraph "Response Flow"
        STREAM --> USER[User]
        EXTRACT --> USER
        UPLOAD --> STATUS[Status Update]
        STATUS --> USER
    end

    style ROUTER fill:#9C27B0
    style LLM fill:#4CAF50
    style VALIDATE fill:#F44336
    style STREAM fill:#2196F3
```

### 1.9 Technology Mapping Overview

| Component Category | Conceptual | AWS Implementation |
|-------------------|------------|-------------------|
| **API Layer** | REST API + WebSocket | API Gateway |
| **Authentication** | JWT Tokens | Amazon Cognito |
| **Application** | Chat Engine, Session Manager | EKS with Kubernetes |
| **Background Jobs** | Ingestion, Cleanup | Lambda + SQS |
| **Vector Database** | Vector Store | Amazon OpenSearch |
| **Document Storage** | Document Store | Amazon S3 |
| **Session Storage** | Session Store, Conversation History | DynamoDB + Redis |
| **Metadata Storage** | Metadata Store | DynamoDB + RDS PostgreSQL |
| **LLM** | LLM Service | Amazon Bedrock |
| **Observability** | Observability Platform | Self-hosted on EKS |

---
