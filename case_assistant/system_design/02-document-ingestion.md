# Document Ingestion Pipeline

## 1. Document Ingestion Pipeline Overview

The Case Assistant system processes documents through a unified pipeline that extracts content, generates embeddings, and indexes into OpenSearch. The pipeline handles two distinct knowledge bases:

| Knowledge Base | Trigger | Volume | Processing Time |
|----------------|---------|--------|-----------------|
| **Static KB** | Scheduled (monthly) | 1,000-10,000 docs | 1-2 hours |
| **User Upload KB** | Event-driven (on upload) | 1 doc per upload | 1-3 minutes |

```mermaid
graph TB
    subgraph "Document Ingestion Pipeline"
        subgraph "Stage 1: Input"
            STATIC[Scheduled Trigger<br/>EventBridge Monthly]
            USER[User Upload<br/>API Gateway]
        end

        subgraph "Stage 2: Storage"
            RAW_S3[S3 Raw Bucket<br/>Document storage]
        end

        subgraph "Stage 3: Extraction"
            TEXTRACT[Document Extraction<br/>Lambda + Textract]
            TABLE_DETECT{Table Detected?<br/>Page-level check}
            TEXT_PARSE[Text Pages<br/>Standard parser]
            TABLE_PARSE[Table Pages<br/>VLM + GPU]
        end

        subgraph "Stage 4: Processing"
            CHUNK[Chunking Strategy<br/>Semantic: 800-1200 tokens]
            EMBED[Embeddings<br/>Bedrock Titan v2]
            META[Metadata Extraction<br/>Citations, keywords]
        end

        subgraph "Stage 5: Indexing"
            INDEX[OpenSearch<br/>citation + unified indices]
            META_DOC[Document Metadata<br/>OpenSearch indices]
            VERSION[S3 Versioning<br/>History tracking]
        end

        subgraph "Stage 6: Completion"
            STATUS[Status Update<br/>S3 status file]
            NOTIFY[Notification<br/>SNS / User callback]
        end

        STATIC --> RAW_S3
        USER --> RAW_S3
        RAW_S3 --> TEXTRACT
        TEXTRACT --> TABLE_DETECT
        TABLE_DETECT -->|Text| TEXT_PARSE
        TABLE_DETECT -->|Table| TABLE_PARSE
        TEXT_PARSE --> CHUNK
        TABLE_PARSE --> CHUNK
        CHUNK --> EMBED
        EMBED --> META
        META --> INDEX
        META --> META_DOC
        META --> VERSION
        INDEX --> STATUS
        STATUS --> NOTIFY
    end
```

---

## 2. Page-Level Splitting for Table Detection

The primary reason for splitting documents into pages is to **detect and handle tables separately** to preserve their structural integrity.

### The Table Chunking Problem

| Issue | Description | Example |
|-------|-------------|---------|
| **Broken Columns** | Text chunking splits mid-column | "Column A: Value A123..." → broken |
| **Lost Rows** | Row relationships destroyed | Header row separated from data rows |
| **Merged Cells** | Complex tables lose structure | Spans not recognized after split |
| **Nested Tables** | Tables within tables broken | Inner table isolated from context |

### VLM + GPU Solution for Tables

```
Table Page
    ↓
[VLM Model with GPU]
    ├─ Textract Tables (for simple tables)
    ├─ Bedrock Multimodal (for complex tables)
    └─ Processes page as IMAGE
    ↓
Structured Table Output
    ├─ Column headers preserved
    ├─ Row mappings intact
    ├─ Merged cells detected
    └─ Nested tables handled
```

### Page-Level Decision Flow

```mermaid
graph TB
    PAGE[Extracted Page]
    TABLE_DETECT{Table Detected?<br/>Vision-based check}

    TEXT_PATH[Text-Only Page]
    TABLE_PATH[Table Page]

    TEXT_CHUNK[Standard Text Chunking<br/>Semantic: 800-1200 tokens]
    VLM_CHUNK[VLM Extraction<br/>Table as JSON + text]

    TEXT_OUT[Text Chunks<br/>Fast, low cost]
    TABLE_OUT[Structured Table<br/>Preserved integrity]

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

### Table Detection Criteria

| Feature | Detection Method | Action |
|---------|-----------------|--------|
| **Grid lines** | Visual detection | Flag for VLM |
| **Tabular patterns** | Layout analysis | Flag for VLM |
| **Multiple columns** | Structure analysis | Flag for VLM |
| **Merged cells** | Visual complexity | Flag for VLM |
| **Headers + data rows** | Pattern matching | Flag for VLM |

### Cost Optimization

| Page Type | Parser Used | GPU? | Cost |
|-----------|-------------|------|------|
| **Text-only pages** | PyMuPDF/Textract | No | Low |
| **Simple tables** | Textract Tables | No | Medium |
| **Complex tables** | Bedrock Multimodal | Yes | High |

**Benefit**: Only table pages use expensive GPU resources → 60-70% cost savings.

---

## 3. Chunking Strategy

### Semantic Chunking (Primary Method)

**Chunk Size**: 800-1200 tokens (optimized for Titan v2's 1536 dimensions)

**Overlap**: 100-150 tokens (12-19%, reduced from 40-67%)

```mermaid
graph LR
    DOC[Document Text]
    SEMANTIC[Semantic Boundary Detection<br/>Embedding similarity]
    CHUNKS[Chunks 800-1200 tokens<br/>With 100-150 token overlap]

    DOC --> SEMANTIC
    SEMANTIC --> CHUNKS

    style SEMANTIC fill:#2196F3
    style CHUNKS fill:#4CAF50
```

**Why Semantic Over Fixed-Size**:
- Preserves legal provision boundaries
- Maintains logical argument flow
- Reduces mid-sentence splits
- 15-20% better retrieval precision for legal documents

### Parent-Child Chunking

| Chunk Type | Size | Purpose | Index |
|------------|------|---------|-------|
| **Child chunks** | 800-1200 tokens | Precise semantic search | unified-legal-index |
| **Parent chunks** | 2400-3600 tokens | Complete legal context | unified-legal-index (linked) |

**Process**:
1. Create child chunks using semantic boundaries
2. Aggregate 3-6 child chunks into 1 parent chunk
3. Store both in OpenSearch with parent-child relationship
4. Query returns child chunks, expand to parent context as needed

### Cross-Page Content Handling

```mermaid
graph LR
    P1[Page 5<br/>Last paragraph]
    P2[Page 6<br/>First paragraph]

    DETECT{Text<br/>Continues?}

    MERGE[Merge into<br/>single chunk]
    SPLIT[Keep separate<br/>add metadata]

    C1[Chunk with<br/>pages 5-6]
    C2[Chunk 5<br/>with metadata]
    C3[Chunk 6<br/>with metadata]

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

**Metadata for Cross-Page Chunks**:
```json
{
  "chunk_id": "chunk-doc-001-pages-5-6",
  "text": "...continued from page 5...",
  "metadata": {
    "page_numbers": [5, 6],
    "cross_page": true,
    "continued_from": 5,
    "continues_to": 6
  }
}
```

---

## 4. Index Population

The ingestion pipeline populates **2 indices** (simplified from original 6-index design):

### Index 1: Citation Index

**Purpose**: Fast exact-match lookup for legal citations

**Extraction Process**:
```text
For each chunk:
  1. Detect citation patterns:
     - Section citations: "Section 288-95", "s 288-95"
     - Ruling citations: "TR 2022/1", "TD 2023/5"
     - Case citations: "FCT v. Myer (1937)"

  2. Normalize to canonical form
  3. Generate aliases for matching variations
  4. Extract hierarchy (parent/child sections)

  5. Build citation document:
     - canonical: "s-288-95"
     - aliases: ["section-288-95", "s288-95", "sec-288-95"]
     - chunk_pointers: [chunk IDs containing this citation]
     - cross_references: [related citations]
```

**OpenSearch Document**:
```json
{
  "citation_id": "cit-itaa-1997-s-288-95",
  "citation_canonical": "s-288-95",
  "citation_aliases": ["section-288-95", "s288-95", "sec-288-95"],
  "act": "ITAA 1997",
  "title": "Failure to lodge return on time",
  "chunk_pointers": ["chunk-itaa-1997-s-288-95-001", "chunk-itaa-1997-s-288-95-002"],
  "cross_references": [
    {"citation": "s-995-1", "type": "definition", "relationship": "defines_term"},
    {"citation": "s-288-90", "type": "related_provision", "relationship": "related_to"}
  ],
  "metadata": {
    "document_type": "tax_legislation",
    "jurisdiction": "federal",
    "kb_type": "static"
  }
}
```

### Index 2: Unified Legal Index

**Purpose**: Hybrid vector + BM25 search with metadata filtering and parent-child context

**Document Structure**:
```json
{
  "chunk_id": "chunk-itaa-1997-s-288-95-001",
  "chunk_type": "child",
  "text": "A penalty of 210 penalty units applies...",
  "embedding": [0.123, 0.456, ...],  // Titan v2, 1536 dimensions
  "parent_chunk": {
    "parent_id": "parent-itaa-1997-s-288-95",
    "parent_text": "(1) An entity that fails to lodge..."
  },
  "metadata": {
    "document_type": "tax_legislation",
    "jurisdiction": "federal",
    "act": "ITAA 1997",
    "section": "288-95",
    "year": 1997,
    "status": "active",
    "kb_type": "static"
  },
  "citations": ["s-288-95", "s-995-1"],
  "keywords": ["penalty-units", "activity-statement"]
}
```

**What's Included** (combines 6 indices into 2):

| Original Index | Now Stored In |
|----------------|---------------|
| **Citation Index** | Separate citation-index (unchanged) |
| **Semantic Index** | unified-legal-index (embedding field) |
| **Keyword Index** | unified-legal-index (BM25 automatic) |
| **Context Index** | unified-legal-index (parent_chunk field) |
| **Metadata Index** | unified-legal-index (metadata field) |
| **Cross-Reference Index** | citation-index (cross_references array) |

---

## 5. Metadata and Version Tracking

### OpenSearch for Metadata

**Index: document-metadata**
```json
{
  "document_id": "itaa-1997",
  "current_version": 5,
  "document_type": "tax_legislation",
  "title": "Income Tax Assessment Act 1997",
  "source_url": "https://legislation.gov.au/...",
  "file_hash": "a1b2c3d4...",
  "chunk_count": 4500,
  "citation_count": 890,
  "last_ingested_at": "2026-03-30T02:15:00Z",
  "ingestion_status": "COMPLETE",
  "kb_type": "static",
  "s3_version_id": "5z9LW7xTi..."
}
```

**Index: user-document-metadata**
```json
{
  "user_id": "user-123",
  "document_id": "doc-user-123-001",
  "filename": "my_tax_return_2024.pdf",
  "file_size_bytes": 1048576,
  "status": "COMPLETE",
  "chunk_count": 45,
  "uploaded_at": "2026-03-30T10:00:00Z",
  "processed_at": "2026-03-30T10:02:30Z",
  "kb_type": "user_upload"
}
```

### S3 Versioning for History

**Automatic version tracking**:
```
case-assistant-raw/static/itaa-1997.pdf
  Version 1: 2026-01-01 (initial)
  Version 2: 2026-02-01 (amendment)
  Version 3: 2026-03-01 (amendment)
  Version 4: 2026-03-15 (amendment)
  Version 5: 2026-03-30 (current)
```

**Benefits**:
- Automatic with S3 versioning enabled
- All historical versions preserved
- OpenSearch stores version metadata
- Lifecycle policy manages old versions

---

## 6. AWS Services Step-by-Step

### Static KB Ingestion Flow

```
Step 1: EventBridge triggers Lambda (monthly cron)
Step 2: Lambda fetches from ATO sources
Step 3: Store raw PDFs in S3: /raw/static/YYYY-MM-DD/
Step 4: Lambda extracts pages, detects tables
Step 5: Text pages → PyMuPDF, Table pages → Textract/VLM
Step 6: Semantic chunking (800-1200 tokens)
Step 7: Bedrock Titan v2 generates embeddings
Step 8: OpenSearch bulk indexing
Step 9: Update metadata in OpenSearch
Step 10: SNS notification
```

### User Upload Ingestion Flow

```
Step 1: User calls API Gateway: POST /documents/upload-initiate
Step 2: Cognito validates JWT
Step 3: Lambda returns presigned S3 URL
Step 4: User uploads directly to S3
Step 5: S3 event triggers processing Lambda
Step 6: Lambda extracts pages, detects tables
Step 7: Text pages → PyMuPDF, Table pages → Textract/VLM
Step 8: Semantic chunking (800-1200 tokens)
Step 9: Bedrock Titan v2 generates embeddings
Step 10: OpenSearch bulk indexing with user_id scope
Step 11: Update user-document-metadata in OpenSearch
Step 12: Create status file in S3
Step 13: User polls or receives notification
```

---

## 7. Full Refresh Ingestion (Current Approach)

> **NOTE**: Incremental ingestion with delta detection was evaluated but **deferred for simplicity**. The current implementation uses full refresh for both knowledge bases.

### Full Refresh Process

```
When document is re-ingested:
  1. Compare file-level hash (SHA-256)
  2. If unchanged: Skip processing
  3. If changed:
     a. Delete all existing vectors for document_id
     b. Re-process all pages from scratch
     c. Re-chunk, re-embed, re-index all content
     d. Update metadata with new version
     e. S3 versioning keeps history
```

**Benefits**:
- Simpler implementation (2-3 days vs 2-3 weeks)
- Guaranteed consistency (no partial states)
- Easier debugging and maintenance
- Sufficient for initial launch

**When to Add Incremental (Phase 2)**:
- Cost/benefit analysis shows >70% savings
- Re-upload frequency >5x per document
- User experience demands faster updates

---

## 8. Error Handling

### Retry Strategy

```
Retry Configuration:
  - Max retries: 3
  - Backoff: Exponential (2^n seconds)
  - Jitter: ±20% random
  - Dead letter queue: Failed documents to S3 failed/
```

### Error Categories

| Error Type | Detection | Recovery |
|------------|-----------|----------|
| **Source Fetch Failed** | HTTP errors | Retry with backoff |
| **Textract Failed** | API timeout | Retry, fallback to PDF parser |
| **Embedding Failed** | Bedrock API error | Retry, continue on rate limit |
| **OpenSearch Failed** | Bulk API error | Retry failed chunks |
| **User Upload Failed** | Validation error | Return error to user |

---

## 9. Monitoring

### CloudWatch Metrics

| Metric | Namespace | Alarm Threshold |
|--------|-----------|-----------------|
| **Ingestion Duration** | CaseAssistant/Ingestion | > 2 hours (static), > 5 min (user) |
| **Textract API Errors** | CaseAssistant/Textract | > 5% |
| **Bedrock API Errors** | CaseAssistant/Bedrock | > 1% |
| **OpenSearch Index Errors** | CaseAssistant/OpenSearch | > 1% |
| **User Upload Failures** | CaseAssistant/UserUpload | > 5% |

### CloudWatch Dashboards

**Static KB Dashboard**:
- Last sync time and duration
- Documents processed per sync
- Error rates by service
- Storage usage trends

**User Upload Dashboard**:
- Uploads per hour/day
- Processing latency (p50, p95, p99)
- Error rates by error type
- Active users count

---

## Related Documents

- **[07-ingestion-strategies-comparison.md](./07-ingestion-strategies-comparison.md)** - Ingestion strategies and AWS service integration
- **[13-chunking-strategies.md](./13-chunking-strategies.md)** - Detailed chunking strategies for legal documents
- **[12-high-level-design.md](./12-high-level-design.md)** - Overall system architecture
