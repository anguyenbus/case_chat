# Document Ingestion Pipeline

## 1. Document Ingestion Pipeline Overview

The Case Assistant system processes documents through a unified pipeline that extracts content, generates embeddings, and indexes into OpenSearch. The pipeline handles two distinct knowledge bases:

| Knowledge Base | Trigger | Volume | Processing Time | Chunking Strategy |
|----------------|---------|--------|-----------------|-------------------|
| **Static KB** | Scheduled (monthly) | 1,000-10,000 docs | 1-2 hours | Hybrid (structural + semantic) |
| **User Upload KB** | Event-driven (on upload) | 1 doc per upload | 1-3 minutes | Fixed-size with overlap |

```mermaid
graph TB
    subgraph "Knowledge Base Sources"
        STATIC[Static Knowledge Base<br/>Monthly Sync<br/>Legislation, Rulings, Guidelines]
        USER[User Uploads<br/>On-Demand<br/>Tax Returns, Financial Docs]
    end

    subgraph "Ingestion Control"
        CRON[K8s CronJob<br/>Concurrency: Forbid<br/>Distributed Lock: Redis]
        PRE[Presigned URL Generator<br/>1-Hour Expiry<br/>Duplicate Detection]
    end

    subgraph "Storage Layer"
        RAW_S3[S3 Raw Bucket<br/>Versioning Enabled<br/>90-Day Retention]
        CONFIG_S3[S3 Config Bucket<br/>Source Lists<br/>Validation Staging]
    end

    subgraph "Extraction Layer"
        DETECT[Format Detection<br/>PDF, DOCX, MD, Images]
        TABLE_SCAN{Table Detection<br/>Fast Heuristics}
        TEXTRACT[Text Parser<br/>PyMuPDF / Python-docx]
        VLM[Table Extractor<br/>Textract Confirm → VLM]
    end

    subgraph "Processing Layer"
        CHUNK[Chunking Strategy<br/>800-1200 tokens<br/>12-15% overlap]
        EMBED[Embedding Generation<br/>Bedrock Titan v2<br/>1536 dimensions]
        ENRICH[Metadata Enrichment<br/>Citations, Keywords<br/>Cross-References]
    end

    subgraph "Indexing Layer"
        CITATION[Citation Index<br/>Exact Match Lookup<br/>Versioned Aliases]
        UNIFIED[Unified Legal Index<br/>Vector + BM25<br/>Parent-Child Chunks]
        META[Document Metadata<br/>Per-User Isolation<br/>Status Tracking]
    end

    subgraph "Completion"
        STATUS[Status Update<br/>OpenSearch + S3 Status File]
 NOTIFY[Notification<br/>WebSocket + Polling]
    end

    STATIC --> CRON
    USER --> PRE
    CRON --> RAW_S3
    PRE --> RAW_S3
    CONFIG_S3 -.Validation.-> CRON
    RAW_S3 --> DETECT
    DETECT --> TABLE_SCAN
    TABLE_SCAN -->|Text Page| TEXTRACT
    TABLE_SCAN -->|Table Detected| VLM
    TEXTRACT --> CHUNK
    VLM --> CHUNK
    CHUNK --> EMBED
    EMBED --> ENRICH
    ENRICH --> CITATION
    ENRICH --> UNIFIED
    ENRICH --> META
    CITATION --> STATUS
    UNIFIED --> STATUS
    META --> STATUS
    STATUS --> NOTIFY

    style STATIC fill:#E3F2FD
    style USER fill:#FFF3E0
    style TABLE_SCAN fill:#FF9800
    style VLM fill:#9C27B0
    style CITATION fill:#4CAF50
    style UNIFIED fill:#4CAF50
```

---

## 2. Static KB Ingestion Pipeline

### 2.1 Pipeline Architecture

```mermaid
graph TB
    subgraph "Trigger & Coordination"
        A[K8s CronJob<br/>Schedule: 0 2 1 * *<br/>ConcurrencyPolicy: Forbid]
        B[Redis Distributed Lock<br/>TTL: 7200 seconds<br/>Auto-release on completion]
        C[Source List Validator<br/>S3: case-assistant-config<br/>Stage: Validate → Promote]
    end

    subgraph "Document Fetch"
        D[Fetch from ATO Sources<br/>HTTPS with Fallback URLs<br/>Timeout: 300s per source]
        E{Source Available?}
        F[Use Fallback URL<br/>Retry: 3 attempts<br/>Backoff: Exponential]
        G[Skip Non-Critical<br/>Log Warning<br/>Continue Sync]
        H[Fail Critical<br/>Page On-Call<br/>Abort Sync]
    end

    subgraph "Storage & Validation"
        I[S3 Raw Bucket<br/>Prefix: /static/YYYY-MM-DD/<br/>Calculate SHA-256]
        J{Changed Since Last?}
        K[Skip Processing<br/>Update Metadata<br/>Mark as Unchanged]
    end

    subgraph "Extraction & Processing"
        L[Page Extraction<br/>Format-Specific Parsers<br/>Detect Tables]
        M[Table Detection<br/>Fast: Layout Analysis<br/>Confirm: Textract]
        N[Text Pages → PyMuPDF<br/>Table Pages → VLM Extraction]
    end

    subgraph "Indexing"
        O[Chunking Strategy<br/>Structural Boundaries<br/>Semantic Refinement]
        P[Embedding Generation<br/>Bedrock Titan v2<br/>Batch: 100 chunks]
        Q[Citation Extraction<br/>Normalize → Alias<br/>Cross-Reference]
    end

    subgraph "Completion"
        R[OpenSearch Bulk Index<br/>Citation + Unified Indices<br/>Update Metadata]
        S[SNS Notification<br/>Sync Complete<br/>Error Summary]
    end

    A --> B
    B --> C
    C --> D
    D --> E
    E -->|Yes| I
    E -->|No| F
    F --> E
    E -->|Exhausted Fallbacks| G
    G --> I
    H -.Alert.-> E
    I --> J
    J -->|Unchanged| K
    J -->|Changed| L
    L --> M
    M -->|No Table| N
    M -->|Table Confirmed| N
    N --> O
    O --> P
    P --> Q
    Q --> R
    R --> S
    K --> R

    style A fill:#2196F3
    style B fill:#FF5722
    style E fill:#FF9800
    style M fill:#FF9800
    style N fill:#9C27B0
    style Q fill:#4CAF50
    style R fill:#4CAF50
```

### 2.2 Source List Management

```mermaid
graph LR
    subgraph "S3 Config Bucket Structure"
        CONFIG[case-assistant-config/]
        CURRENT[source-list/current.json<br/>Active Source List]
        VERSIONING[current.json.v1, v2, v3...<br/>S3 Versioning]
        STAGING[staging/<br/>pending-*.json<br/>awaiting-approval.json]
        REJECTED[rejected/<br/>rejected-*.json<br/>with reason]
    end

    subgraph "Update Workflow"
        UPLOAD[1. Professional Uploads<br/>New Source List to staging/]
        VALIDATE[2. Automated Validation<br/>Schema Check<br/>URL Reachability<br/>Duplicate Detection]
        APPROVE[3. Approval Step<br/>Manual Review<br/>Promote to current/]
        DEPLOY[4. Deployment<br/>Atomic S3 Copy<br/>Next Cron Picks Up]
    end

    subgraph "Validation Checks"
        CHECK1[Schema Validation<br/>Required Fields<br/>Data Types]
        CHECK2[URL Reachability<br/>HEAD Request<br/>Timeout Check]
        CHECK3[Duplicate Check<br/>Unique source_id<br/>No Conflicts]
    end

    CONFIG --> CURRENT
    CONFIG --> VERSIONING
    CONFIG --> STAGING
    CONFIG --> REJECTED

    STAGING --> UPLOAD
    UPLOAD --> VALIDATE
    VALIDATE --> CHECK1
    VALIDATE --> CHECK2
    VALIDATE --> CHECK3
    CHECK1 --> APPROVE
    CHECK2 --> APPROVE
    CHECK3 --> APPROVE
    APPROVE --> DEPLOY
    DEPLOY --> CURRENT

    style CURRENT fill:#4CAF50
    style STAGING fill:#FF9800
    style REJECTED fill:#F44336
    style VALIDATE fill:#2196F3
    style APPROVE fill:#9C27B0
```

### 2.3 Source Priority Matrix

| Priority | Availability | Action | Notification |
|----------|--------------|--------|--------------|
| **Critical** | Available | Proceed | None |
| **Critical** | Unavailable | Fail entire sync, retry in 1 hour | Page on-call |
| **Critical** | Fallback Only | Use fallback, alert team | Warning notification |
| **High** | Available | Proceed | None |
| **High** | Unavailable | Skip, log warning, retry in 1 hour | Info log |
| **Normal** | Available | Proceed | None |
| **Normal** | Unavailable | Skip, log warning | None |
| **Low** | Available | Proceed | None |
| **Low** | Unavailable | Skip silently | None |

---

## 3. User Upload Ingestion Pipeline

### 3.1 Presigned URL Upload Flow

```mermaid
sequenceDiagram
    autonumber
    participant U as User Browser
    participant API as API Gateway
    participant K8s as K8s Service
    participant OS as OpenSearch
    participant S3 as S3 Bucket
    participant SQS as SQS Queue
    participant W as S3 Watcher
    participant Job as K8s Ingest Job
    participant WS as WebSocket Service

    U->>API: POST /documents/upload-initiate<br/>{filename, size, content_type, client_hash}
    API->>K8s: Validate JWT, Check quota
    K8s->>OS: Check for existing hash<br/>(optimization, not security)
    OS-->>K8s: Potential duplicates
    K8s->>S3: Generate presigned POST URL<br/>Key: uploads/{user_id}/{doc_id}.pdf<br/>Expires: 1 hour
    S3-->>K8s: Presigned URL + Fields
    K8s->>OS: Create metadata record<br/>status: INITIATED
    K8s-->>API: {document_id, upload_url, expires_at}
    API-->>U: Upload credentials

    Note over U,WS: Client-side upload happens
    U->>S3: POST {upload_url}<br/>Multipart form-data with file
    S3-->>U: 200 OK

    U->>API: POST /documents/{id}/upload-complete
    API->>K8s: Update status to UPLOADED
    K8s->>OS: status: UPLOADED
    K8s-->>U: Acknowledgment

    S3->>SQS: s3:ObjectCreated:* event
    SQS-->>W: Poll for messages
    W->>OS: Check document status<br/>(Idempotency)
    alt Status is UPLOADED or FAILED
        W->>OS: Update status to PROCESSING
        W->>Job: Trigger K8s Job<br/>job: ingest-{doc_id}
        Job->>S3: Download document
        Job->>Job: Extract, Chunk, Embed
        Job->>OS: Bulk index chunks
        Job->>OS: Update status to COMPLETE
        Job->>WS: Broadcast completion
        WS-->>U: WebSocket: status=COMPLETE
    else Status already PROCESSING or COMPLETE
        W->>W: Skip (duplicate event)
    end

    U->>API: GET /documents/{id}/status<br/>(or receive WebSocket push)
    API-->>U: {status: COMPLETE, chunk_count: 45}
```

### 3.2 Document Status State Machine

```mermaid
stateDiagram-v2
    [*] --> INITIATED: Upload initiated<br/>(Presigned URL generated)

    INITIATED --> UPLOADING: Optional: Client<br/>signals upload start
    INITIATED --> UPLOADED: S3 confirms<br/>upload complete
    INITIATED --> ABANDONED: 1 hour expires<br/>without upload

    UPLOADING --> UPLOADED: Upload completes
    UPLOADING --> ABANDONED: Network failure<br/>or timeout

    UPLOADED --> PROCESSING: S3 Watcher<br/>triggers job
    UPLOADED --> ABANDONED: Upload-complete<br/>never called (auto-recover)

    ABANDONED --> UPLOADED: Auto-recovery:<br/>File exists in S3
    ABANDONED --> [*]: File missing<br/>in S3

    PROCESSING --> COMPLETE: All chunks indexed
    PROCESSING --> FAILED: Error during<br/>processing

    FAILED --> PROCESSING: Manual retry<br/>(max 3 attempts)
    FAILED --> [*]: Max retries<br/>exceeded

    COMPLETE --> [*]: Ready for queries

    note right of INITIATED
        TTL: 1 hour
        Cleaned by CronJob
    end note

    note right of PROCESSING
        Progress: 0-100%
        Stage tracking
        WebSocket updates
    end note

    note right of ABANDONED
        Auto-recovery if
        file exists in S3
    end note
```

### 3.3 Idempotency Protection

```mermaid
graph TB
    subgraph "S3 Event Delivery"
        EVENT[S3 ObjectCreated Event]
        SQS[SQS Queue<br/>At-Least-Once Delivery]
        WATCHER[S3 Watcher K8s Service]
    end

    subgraph "Idempotency Check"
        GET[Get Document Metadata<br/>from OpenSearch]
        CHECK{Current Status?}
        CONDITION1[status = INITIATED<br/>+ upload expired]
        CONDITION2[status = UPLOADED<br/>or FAILED]
        CONDITION3[status = PROCESSING<br/>or COMPLETE]
    end

    subgraph "Actions"
        RECOVER[Auto-recovery:<br/>Mark UPLOADED<br/>Trigger job]
        TRIGGER[Trigger K8s Job<br/>Update: PROCESSING]
        SKIP[Skip processing<br/>Log: Duplicate event]
        MARK_ABANDONED[Mark ABANDONED<br/>File never uploaded]
    end

    subgraph "K8s Job Level"
        JOB_CHECK{Job Exists?}
        JOB_RUNNING[Job Active?<br/>Skip trigger]
        JOB_FAILED[Job Failed?<br/>Delete & retry]
        JOB_CREATE[Create new Job<br/>idempotent name]
    end

    EVENT --> SQS
    SQS --> WATCHER
    WATCHER --> GET
    GET --> CHECK
    CHECK -->|INITIATED + Expired| CONDITION1
    CHECK -->|UPLOADED / FAILED| CONDITION2
    CHECK -->|PROCESSING / COMPLETE| CONDITION3
    CHECK -->|Unknown status| SKIP

    CONDITION1 --> RECOVER
    CONDITION2 --> TRIGGER
    CONDITION3 --> SKIP

    TRIGGER --> JOB_CHECK
    JOB_CHECK -->|Exists| JOB_RUNNING
    JOB_CHECK -->|Not exists| JOB_CREATE
    JOB_CHECK -->|Exists + Failed| JOB_FAILED

    style EVENT fill:#FF9800
    style CHECK fill:#FF9800
    style SKIP fill:#9E9E9E
    style TRIGGER fill:#4CAF50
```

---

## 4. Document Format Support

### 4.1 Supported Formats

| Format | Extension | MIME Type | Parser | Table Support |
|--------|-----------|-----------|--------|---------------|
| **PDF** | .pdf | application/pdf | PyMuPDF + Textract | Yes (VLM) |
| **Word** | .docx | application/vnd.openxmlformats-officedocument.wordprocessingml.document | python-docx | Yes |
| **Legacy Word** | .doc | application/msword | antiword | Limited |
| **Markdown** | .md | text/markdown | markdown | N/A |
| **Plain Text** | .txt | text/plain | Native | N/A |
| **Excel** | .xlsx, .xls | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet | openpyxl | Yes |
| **Images** | .png, .jpg, .jpeg, .tiff | image/* | Textract OCR | Limited |

### 4.2 Format Detection & Parser Selection

```mermaid
graph TB
    UPLOAD[File Uploaded<br/>to S3]

    DETECT[Format Detection<br/>By MIME Type + Extension]

    VALIDATE{Format Supported?}

    PDF[PDF Parser<br/>PyMuPDF for text<br/>Textract for tables<br/>VLM for complex tables]
    DOCX[DOCX Parser<br/>python-docx<br/>Preserve structure<br/>Extract tables]
    DOC[Legacy DOC Parser<br/>antiword / LibreOffice<br/>Best effort]
    MD[Markdown Parser<br/>Preserve formatting<br/>Extract headers]
    TXT[Text Parser<br/>Direct ingestion<br/>Chunk by paragraphs]
    XLSX[Excel Parser<br/>openpyxl<br/>Extract sheets as tables]
    IMG[Image Parser<br/>Textract OCR<br/>Confidence scoring]

    REJECT[Reject Upload<br/>Return: Unsupported format]

    PROCESS[Processing Pipeline<br/>Table detection<br/>Chunking<br/>Embedding]

    UPLOAD --> DETECT
    DETECT --> VALIDATE
    VALIDATE -->|application/pdf| PDF
    VALIDATE -->|docx| DOCX
    VALIDATE -->|doc| DOC
    VALIDATE -->|markdown| MD
    VALIDATE -->|text/plain| TXT
    VALIDATE -->|excel| XLSX
    VALIDATE -->|image/*| IMG
    VALIDATE -->|other| REJECT

    PDF --> PROCESS
    DOCX --> PROCESS
    DOC --> PROCESS
    MD --> PROCESS
    TXT --> PROCESS
    XLSX --> PROCESS
    IMG --> PROCESS

    style PDF fill:#E91E63
    style DOCX fill:#2196F3
    style IMG fill:#FF9800
    style REJECT fill:#F44336
```

---

## 5. Table Detection & Extraction

### 5.1 Two-Stage Table Detection Strategy

```mermaid
graph TB
    subgraph "Stage 1: Fast Detection (Local, No API)"
        PAGE[PDF Page]
        HEURISTICS[Fast Heuristics<br/>O(1) checks]

        H1[Count Vector Lines<br/>> 5 lines?]
        H2[Text Density<br/>Regular spacing?]
        H3[Column Detection<br/>>= 3 columns?]

        SCORE[Calculate Score<br/>0-7 points]
        THRESHOLD{Score >= 4?}
    end

    subgraph "Stage 2: Confirmation (Textract API)"
        CONFIRM[Textract Table Detection<br/>FeatureTypes: TABLES<br/>Cost: $0.0015/page]
        CONFIRMED{Table Found?}
    end

    subgraph "Stage 3: Extraction"
        TEXT_PATH[Text Parser<br/>PyMuPDF<br/>Fast, Low Cost]
        TABLE_PATH[VLM Extraction<br/>Bedrock Multimodal<br/>Preserves Structure]
    end

    PAGE --> HEURISTICS
    HEURISTICS --> H1
    HEURISTICS --> H2
    HEURISTICS --> H3
    H1 --> SCORE
    H2 --> SCORE
    H3 --> SCORE
    SCORE --> THRESHOLD

    THRESHOLD -->|No| TEXT_PATH
    THRESHOLD -->|Yes| CONFIRM
    CONFIRM --> CONFIRMED
    CONFIRMED -->|No| TEXT_PATH
    CONFIRMED -->|Yes| TABLE_PATH

    style HEURISTICS fill:#4CAF50
    style CONFIRM fill:#FF9800
    style TABLE_PATH fill:#9C27B0
```

### 5.2 Cost Comparison

| Strategy | 100-page Document | 20 Tables | Cost |
|----------|-------------------|-----------|------|
| **VLM Every Page** | 100 VLM calls @ $0.02 | - | $2.00 |
| **Two-Stage Detection** | 100 free checks | 20 Textract @ $0.0015 + 20 VLM @ $0.02 | $0.43 |
| **Savings** | - | - | **78%** |

### 5.3 Multi-Page Table Handling

```mermaid
graph TB
    subgraph "Detection Phase"
        T1[Table on Page N]
        T2[First Table on Page N+1]

        CHECK{Check Continuation<br/>Indicators}

        IND1[Indicator 1:<br/>Column Count Match?]
        IND2[Indicator 2:<br/>Column Width Similar<br/>> 90%?]
        IND3[Indicator 3:<br/>No Bottom Border<br/>on Page N?]
        IND4[Indicator 4:<br/>No Header on<br/>Page N+1?]
    end

    subgraph "Decision Logic"
        COUNT{Count True<br/>Indicators}
        DECISION{2 or More<br/>Indicators True?}
    end

    subgraph "Decision"
        CONTINUE[Table Continues<br/>Mark for Merge]
        SEPARATE[Separate Tables<br/>Process independently]
    end

    subgraph "Merge Phase"
        GROUP[Group Sequential<br/>Continued Tables]
        MERGE[Merge Into Single<br/>Table Object]
        METADATA[Add Metadata:<br/>page_span: [N, N+1, N+2]<br/>is_multi_page: true]
    end

    T1 --> CHECK
    T2 --> CHECK
    CHECK --> IND1
    CHECK --> IND2
    CHECK --> IND3
    CHECK --> IND4

    IND1 --> COUNT
    IND2 --> COUNT
    IND3 --> COUNT
    IND4 --> COUNT

    COUNT --> DECISION
    DECISION -->|Yes| CONTINUE
    DECISION -->|No| SEPARATE

    CONTINUE --> GROUP
    GROUP --> MERGE
    MERGE --> METADATA

    style CHECK fill:#FF9800
    style DECISION fill:#FF9800
    style CONTINUE fill:#4CAF50
    style SEPARATE fill:#2196F3
```

**Multi-Page Table Metadata:**

```json
{
  "chunk_id": "chunk-table-tax-return-schedule-1",
  "chunk_type": "table",
  "is_multi_page": true,
  "page_span": [5, 6, 7],
  "page_count": 3,
  "row_count": 45,
  "column_count": 6,
  "headers": ["Item", "Description", "Amount", "Deduction", "Taxable", "Labels"]
}
```

---

## 6. Chunking Strategies

### 6.1 Strategy Comparison

| Aspect | Fixed-Size | Semantic | Hybrid (Recommended) |
|--------|-----------|----------|---------------------|
| **Split Method** | Character count | Embedding similarity | Structure first, semantic refinement |
| **API Calls** | 0 (for chunking) | 2x (detect + embed) | 0.2x (20% semantic refinement) |
| **Cost** | $ | $$ | $ |
| **Quality** | Good | Best | Very Good |
| **Use Case** | User uploads | Critical docs | Static KB |

### 6.2 Hybrid Chunking Flow

```mermaid
graph TB
    subgraph "Input"
        DOC[Document Text<br/>Structured Legal Document]
    end

    subgraph "Stage 1: Structural Split"
        STRUCTURE[Extract Structural Boundaries<br/>Sections, Divisions, Provisions]
        SPLIT[Split by Structure<br/>e.g., Division 3, s 288-95]
    end

    subgraph "Stage 2: Size Check"
        SIZE{Section Size}
        FITS[<= 1200 tokens<br/>Use as-is]
        MEDIUM[1200-3600 tokens<br/>Semantic refinement]
        LARGE[> 3600 tokens<br/>Recursive + semantic]
    end

    subgraph "Stage 3: Semantic Refinement"
        SENTENCES[Split into Sentences]
        EMBED[Cheap Sentence Embeddings<br/>Not Titan v2]
        BOUNDARY[Find Semantic Boundaries<br/>Low similarity points]
        SPLIT2[Split at Boundaries]
    end

    subgraph "Output"
        CHUNKS[Chunks 800-1200 tokens<br/>Structural integrity preserved]
        METADATA[Metadata:<br/>source_section, chunk_type]
    end

    DOC --> STRUCTURE
    STRUCTURE --> SPLIT
    SPLIT --> SIZE
    SIZE -->|Fits| FITS
    SIZE -->|Medium| MEDIUM
    SIZE -->|Large| LARGE
    MEDIUM --> SENTENCES
    LARGE --> SENTENCES
    SENTENCES --> EMBED
    EMBED --> BOUNDARY
    BOUNDARY --> SPLIT2
    FITS --> CHUNKS
    SPLIT2 --> CHUNKS
    CHUNKS --> METADATA

    style STRUCTURE fill:#4CAF50
    style EMBED fill:#FF9800
    style BOUNDARY fill:#2196F3
```

### 6.3 Parent-Child Chunking

```mermaid
graph LR
    subgraph "Chunk Creation"
        CHILD[Child Chunks<br/>800-1200 tokens<br/>Precise search]
        PARENT[Parent Chunks<br/>2400-3600 tokens<br/>Full context]
    end

    subgraph "Relationship"
        AGGREGATE[Aggregate 3-6<br/>child chunks]
        LINK[Store parent-child<br/>link in OpenSearch]
    end

    subgraph "Query Flow"
        QUERY[User Query]
        RETRIEVE[Retrieve Child Chunks<br/>Vector similarity]
        EXPAND[Expand to Parent<br/>When needed]
    end

    CHILD --> AGGREGATE
    AGGREGATE --> PARENT
    PARENT --> LINK

    QUERY --> RETRIEVE
    RETRIEVE --> EXPAND
    EXPAND --> PARENT

    style CHILD fill:#2196F3
    style PARENT fill:#9C27B0
    style EXPAND fill:#FF9800
```

### 6.4 Cross-Page Content Handling

```mermaid
graph TB
    subgraph "Detection"
        P1[Page N<br/>Last Paragraph]
        P2[Page N+1<br/>First Paragraph]

        ANALYZE{Analyze Continuation}

        SIG1[Mid-sentence<br/>on Page N]
        SIG2[Semantic Similarity<br/>> 0.8]
        SIG3[No Section Break<br/>detected]
    end

    subgraph "Decision"
        MERGE[Merge into<br/>Single Chunk]
        SEPARATE[Keep Separate<br/>Add Cross-Reference]
    end

    subgraph "Metadata"
        META1[Merged Chunk:<br/>page_numbers: [N, N+1]<br/>cross_page: true]
        META2[Separate Chunks:<br/>continues_to: N+1<br/>continued_from: N]
    end

    P1 --> ANALYZE
    P2 --> ANALYZE
    ANALYZE --> SIG1
    ANALYZE --> SIG2
    ANALYZE --> SIG3

    SIG1 --> MERGE
    SIG2 --> MERGE
    SIG3 --> SEPARATE

    MERGE --> META1
    SEPARATE --> META2

    style ANALYZE fill:#FF9800
    style MERGE fill:#4CAF50
    style SEPARATE fill:#2196F3
```

---

## 7. Index Structure

### 7.1 Two-Index Architecture

```mermaid
graph TB
    subgraph "Input"
        CHUNKS[Processed Chunks<br/>With Embeddings]
        CITATIONS[Extracted Citations<br/>Normalized + Aliases]
        METADATA[Document Metadata<br/>Per-User + Static]
    end

    subgraph "Index 1: Citation Index"
        CITATION_INDEX[citation-index]
        C_EXACT[Exact Match Lookup<br/>Canonical: s-288-95<br/>Aliases: section-288-95]
        C_VERSION[Versioned Citations<br/>is_current: true/false<br/>valid_from, valid_to]
        C_XREF[Cross-References<br/>Related provisions<br/>Definition links]
    end

    subgraph "Index 2: Unified Legal Index"
        UNIFIED_INDEX[unified-legal-index]
        U_VECTOR[Vector Search<br/>Titan v2 embeddings<br/>k-NN: 10 candidates]
        U_BM25[Keyword Search<br/>Full-text BM25<br/>Automatic]
        U_FILTER[Metadata Filters<br/>tenant_id, user_id<br/>document_type]
        U_PARENT[Parent-Child<br/>parent_chunk links<br/>Context expansion]
    end

    subgraph "Metadata Index"
        META_INDEX[user-document-metadata<br/>document-metadata]
        M_STATUS[Status Tracking<br/>INITIATED → COMPLETE<br/>Progress, Stage]
        M_ISO[User Isolation<br/>user_id scoped<br/>tenant_id filtering]
    end

    CITATIONS --> CITATION_INDEX
    CITATION_INDEX --> C_EXACT
    CITATION_INDEX --> C_VERSION
    CITATION_INDEX --> C_XREF

    CHUNKS --> UNIFIED_INDEX
    UNIFIED_INDEX --> U_VECTOR
    UNIFIED_INDEX --> U_BM25
    UNIFIED_INDEX --> U_FILTER
    UNIFIED_INDEX --> U_PARENT

    METADATA --> META_INDEX
    META_INDEX --> M_STATUS
    META_INDEX --> M_ISO

    style CITATION_INDEX fill:#9C27B0
    style UNIFIED_INDEX fill:#4CAF50
    style META_INDEX fill:#2196F3
```

### 7.2 Document Isolation Architecture

```mermaid
graph TB
    subgraph "Document Sources"
        STATIC_DOCS[Static KB Documents<br/>Legislation, Rulings]
        USER_DOCS[User Uploaded Documents<br/>Tax Returns, Financials]
    end

    subgraph "Indexing with Tenant ID"
        STATIC[Index with<br/>tenant_id: static<br/>user_id: null]
        USER_A[Index with<br/>tenant_id: user:123<br/>user_id: 123]
        USER_B[Index with<br/>tenant_id: user:456<br/>user_id: 456]
    end

    subgraph "Query: User 123"
        QUERY[Search Query]
        MANDATORY[Mandatory Filter:<br/>tenant_id = static<br/>OR user_id = 123]
    end

    subgraph "Results"
        R1[Static KB results<br/>Accessible to all]
        R2[User 123 uploads<br/>Accessible only to 123]
        R3[User 456 uploads<br/>BLOCKED - not returned]
    end

    STATIC_DOCS --> STATIC
    USER_DOCS --> USER_A
    USER_DOCS --> USER_B

    QUERY --> MANDATORY
    MANDATORY --> STATIC
    MANDATORY --> USER_A
    MANDATORY -.Blocked.-> USER_B

    STATIC --> R1
    USER_A --> R2
    USER_B -.Security Filter.-> R3

    style STATIC fill:#E3F2FD
    style USER_A fill:#C8E6C9
    style USER_B fill:#FFCDD2
    style MANDATORY fill:#FF5722
    style R3 fill:#F44336
```

---

## 8. Citation Versioning

### 8.1 Citation Lifecycle

```mermaid
stateDiagram-v2
    [*] --> v1: Initial Ingestion<br/>(March 2026)

    v1 --> Active_v1: is_current: true<br/>valid_from: 2026-03-01
    Active_v1 --> Superseded_v1: Legislation Amended<br/>(April 2026)
    Superseded_v1 --> Archive: is_current: false<br/>valid_to: 2026-04-01

    [*] --> v2: New Version Created<br/>(April 2026)
    v2 --> Active_v2: is_current: true<br/>valid_from: 2026-04-01<br/>replaces: v1

    Active_v1 --> [*]: Point-in-time query<br/>(as_of: 2026-03-15)
    Active_v2 --> [*]: Current query<br/>or as_of: 2026-04+

    note right of Active_v1
        Canonical: s-288-95
        Aliases: [section-288-95, s288-95]
        Chunk pointers: [chunk-v1-001, ...]
    end note

    note right of Active_v2
        Canonical: s-288-95
        Aliases: [section-288-95, s288-95, s-288-95-v1→v2]
        Chunk pointers: [chunk-v2-001, ...]
        Change summary: "Penalty 180→210 units"
    end note
```

### 8.2 Citation Resolution Flow

```mermaid
graph TB
    subgraph "Query"
        USER_Q[User Query:<br/>"What is section 288-95?"]
        PARSE[Parse Citation<br/>Normalize: s-288-95]
    end

    subgraph "Resolution"
        POINT_IN_TIME{Is Point-in-Time<br/>Query?}
        CURRENT[Search for<br/>is_current: true]
        HISTORICAL[Search for<br/>valid_from <= as_of<br/>valid_to > as_or OR null]
    end

    subgraph "Result"
        CITATION[Return Citation<br/>With chunk pointers]
        ALIASES[Resolve Aliases<br/>Old → New mappings]
    end

    subgraph "Fallback"
        NOT_FOUND[Citation Not Found]
        SUGGEST[Suggest Similar<br/>Fuzzy match]
    end

    USER_Q --> PARSE
    PARSE --> POINT_IN_TIME
    POINT_IN_TIME -->|No| CURRENT
    POINT_IN_TIME -->|Yes| HISTORICAL
    CURRENT --> CITATION
    HISTORICAL --> CITATION
    CITATION --> ALIASES

    CURRENT -.Not found.-> NOT_FOUND
    HISTORICAL -.Not found.-> NOT_FOUND
    NOT_FOUND --> SUGGEST

    style CURRENT fill:#4CAF50
    style HISTORICAL fill:#FF9800
    style NOT_FOUND fill:#F44336
```

---

## 9. Error Handling & Monitoring

### 9.1 Error Handling Strategy

```mermaid
graph TB
    subgraph "Error Categories"
        SOURCE[Source Fetch Errors]
        EXTRACT[Extraction Errors]
        EMBED[Embedding Errors]
        INDEX[Indexing Errors]
    end

    subgraph "Retry Strategy"
        RETRY[Exponential Backoff<br/>2^n ± 20% jitter<br/>Max: 3 retries]
        DLQ[Dead Letter Queue<br/>s3://failed/]
    end

    subgraph "Recovery Actions"
        FALLBACK[Fallback Parser<br/>Textract → PyMuPDF]
        SKIP[Skip Non-Critical<br/>Log and continue]
        FAIL[Fail Critical<br/>Abort and alert]
    end

    subgraph "Notifications"
        SNS[SNS Alert<br/>On-Call notification]
        DASH[Dashboard Update<br/>Error rate metrics]
    end

    SOURCE --> RETRY
    EXTRACT --> RETRY
    EMBED --> RETRY
    INDEX --> RETRY

    RETRY -->|Exhausted| DLQ
    RETRY -->|Success| COMPLETE
    RETRY -->|Recoverable| FALLBACK

    SOURCE -->|Critical| FAIL
    EXTRACT -->|Textract timeout| FALLBACK
    EMBED -->|Rate limit| SKIP
    INDEX -->|Bulk error| RETRY

    FAIL --> SNS
    DLQ --> DASH

    style RETRY fill:#FF9800
    style DLQ fill:#F44336
    style FAIL fill:#F44336
    style COMPLETE fill:#4CAF50
```

### 9.2 Monitoring Metrics

| Metric | Threshold | Alarm | Action |
|--------|-----------|-------|--------|
| **Ingestion Duration** | Static KB > 2 hours | Warning | Review job logs |
| **Ingestion Duration** | Static KB > 4 hours | Critical | Page on-call |
| **Ingestion Duration** | User upload > 5 min | Warning | Check processing |
| **Textract Error Rate** | > 5% | Warning | Review failed pages |
| **Bedrock Error Rate** | > 1% | Warning | Check quota/throttle |
| **OpenSearch Error Rate** | > 1% | Warning | Review bulk failures |
| **User Upload Failures** | > 5% | Warning | Review validation |
| **Abandoned Uploads** | > 10/hour | Warning | Check S3 events |

---

## 10. Data Deletion Workflow

### 10.1 30-Day Deletion Process

```mermaid
graph TB
    subgraph "Initiation"
        REQUEST[User Deletion Request<br/>or Account Closure]
        VALIDATE[Validate Authority<br/>Admin or verified user]
        CREATE[Create Deletion Record<br/>deletion_id, user_id, timestamp]
    end

    subgraph "Execution (Parallel)"
        STEP1[Step 1: Delete OpenSearch Chunks<br/>Query by user_id<br/>Bulk delete]
        STEP2[Step 2: Delete Metadata<br/>user-document-metadata<br/>document-metadata]
        STEP3[Step 3: Delete S3 Uploads<br/>All versions<br/>Delete markers]
        STEP4[Step 4: Delete Logs<br/>CloudWatch retention<br/>30-day policy]
    end

    subgraph "Verification"
        VERIFY[Verify Deletion<br/>Check each system]
        REPORT[Generate Report<br/>compliance evidence]
    end

    subgraph "Completion"
        COMPLETE[Mark Deletion Complete<br/>status: COMPLETE<br/>completed_at]
        NOTIFY[Notify Requester<br/>Confirmation + Report]
    end

    REQUEST --> VALIDATE
    VALIDATE --> CREATE
    CREATE --> STEP1
    CREATE --> STEP2
    CREATE --> STEP3
    CREATE --> STEP4

    STEP1 --> VERIFY
    STEP2 --> VERIFY
    STEP3 --> VERIFY
    STEP4 --> VERIFY

    VERIFY --> REPORT
    REPORT --> COMPLETE
    COMPLETE --> NOTIFY

    style CREATE fill:#2196F3
    style STEP1 fill:#FF9800
    style STEP2 fill:#FF9800
    style STEP3 fill:#FF9800
    style STEP4 fill:#FF9800
    style VERIFY fill:#9C27B0
    style COMPLETE fill:#4CAF50
```

### 10.2 Deletion Verification

| System | Check Method | Success Criteria |
|--------|--------------|------------------|
| **OpenSearch Chunks** | Count query by user_id | 0 chunks |
| **OpenSearch Metadata** | Count query by user_id | 0 documents |
| **S3 Uploads** | List objects with prefix | 0 objects |
| **S3 Versions** | List object versions | 0 versions |
| **CloudWatch Logs** | Query logs | Past retention only |

---

## 11. OCR Quality Validation

### 11.1 Quality Check Flow

```mermaid
graph TB
    subgraph "OCR Output"
        TEXTRACT_RESP[Textract Response<br/>+ Confidence Scores]
    end

    subgraph "Validation Checks"
        V1[Average Confidence<br/>>= 70%?]
        V2[Low Confidence Blocks<br/>< 20% of total?]
        V3[Text Present<br/>> 0 blocks?]
        V4[Suspicious Patterns<br/>O vs 0, l vs 1?]
    end

    subgraph "Decisions"
        PASS[All Checks Pass<br/>Proceed to indexing]
        WARN[Warnings Raised<br/>Index with flag<br/>Monitor quality]
        FAIL[Critical Failure<br/>Flag for review<br/>Retry with alt OCR]
    end

    subgraph "Actions"
        INDEX[Index to OpenSearch<br/>ocr_quality: high/medium/low]
        REVIEW[Add to Manual Queue<br/>priority: high/medium]
        RETRY[Retry with Alternative<br/>Different OCR settings]
    end

    TEXTRACT_RESP --> V1
    TEXTRACT_RESP --> V2
    TEXTRACT_RESP --> V3
    TEXTRACT_RESP --> V4

    V1 -->|All pass| PASS
    V2 -->|< 20%| PASS
    V2 -->|>= 20%| WARN
    V3 -->|0 blocks| FAIL
    V4 -->|Patterns found| WARN

    PASS --> INDEX
    WARN --> INDEX
    WARN --> REVIEW
    FAIL --> RETRY
    RETRY -->|Success| INDEX
    RETRY -->|Failed| REVIEW

    style PASS fill:#4CAF50
    style WARN fill:#FF9800
    style FAIL fill:#F44336
```

---

## 12. Full Refresh vs Incremental

### 12.1 Current Approach: Full Refresh

```mermaid
graph LR
    subgraph "Trigger"
        EVENT[Document Re-ingested]
    end

    subgraph "Decision"
        HASH{File Hash<br/>Changed?}
    end

    subgraph "Full Refresh"
        DELETE1[Delete all existing<br/>chunks from OpenSearch]
        DELETE2[Delete existing<br/>citations]
        REPROCESS[Re-process all pages<br/>from scratch]
        REINDEX[Re-chunk, Re-embed,<br/>Re-index all content]
    end

    subgraph "Completion"
        UPDATE[Update metadata<br/>increment version]
        VERSION[S3 versioning<br/>preserves history]
    end

    EVENT --> HASH
    HASH -->|Unchanged| SKIP[Skip processing<br/>Mark unchanged]
    HASH -->|Changed| DELETE1
    DELETE1 --> DELETE2
    DELETE2 --> REPROCESS
    REPROCESS --> REINDEX
    REINDEX --> UPDATE
    UPDATE --> VERSION

    style HASH fill:#FF9800
    style REPROCESS fill:#9C27B0
    style SKIP fill:#4CAF50
```

### 12.2 Incremental Strategy (Future - Phase 2)

**Trigger Criteria:**
- Monthly ingestion cost exceeds $500
- Static KB sync exceeds 4 hours consistently
- Users complain about re-upload processing time
- Static KB grows beyond 50,000 documents

**Proposed Approaches:**

| Level | Strategy | Complexity | Savings |
|-------|----------|------------|---------|
| **Document-Level** | Re-process only changed documents | Low (2-3 days) | 20-30% |
| **Page-Level** | Re-process only changed pages | Medium (1-2 weeks) | 40-50% |
| **Chunk-Level** | Re-embed only changed chunks | High (3-4 weeks) | 50-60% |

**Recommendation:** Start with document-level incremental if needed.

---

## Related Documents

- **[07-ingestion-strategies-comparison.md](./07-ingestion-strategies-comparison.md)** - Ingestion strategies and AWS service integration
- **[13-chunking-strategies.md](./13-chunking-strategies.md)** - Detailed chunking strategies for legal documents
- **[12-high-level-design.md](./12-high-level-design.md)** - Overall system architecture
- **[05-evaluation-strategy.md](./05-evaluation-strategy.md)** - Evaluation metrics and testing approaches
