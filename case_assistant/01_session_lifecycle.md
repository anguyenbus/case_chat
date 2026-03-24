# Case Assistant - Session Lifecycle Diagrams

## Document Metadata

| Field | Value |
|-------|-------|
| **Document Version** | 1.0.0 |
| **Last Updated** | 2026-03-17 |
| **Author** | Principal AI Engineer |
| **Related** | [Technical Design](./case_assistant_technical_design.md) |

---

## Table of Contents

1. [Session State Machine](#1-session-state-machine)
2. [Session Creation Flow](#2-session-creation-flow)
3. [Document Upload and Ingestion Flow](#3-document-upload-and-ingestion-flow)
4. [Query Execution Flow](#4-query-execution-flow)
5. [Session Extension Flow](#5-session-extension-flow)
6. [Session Deletion Flow](#6-session-deletion-flow)
7. [Automatic Cleanup Flow](#7-automatic-cleanup-flow)

---

## 1. Session State Machine

```mermaid
stateDiagram-v2
    [*] --> Creating: User initiates session
    Creating --> Active: Resources allocated
    Active --> Uploading: User uploads documents
    Uploading --> Processing: Upload complete
    Processing --> Ready: Ingestion complete
    Processing --> Error: Ingestion failed
    Ready --> Querying: User submits query
    Querying --> Ready: Query complete
    Ready --> Expiring: TTL timeout
    Active --> Expiring: TTL timeout
    Error --> Expiring: TTL timeout
    Expiring --> Deleting: Cleanup triggered
    Deleting --> Deleted: All resources removed
    Deleting --> [*]
    Active --> Deleting: Manual delete
    Ready --> Deleting: Manual delete

    note right of Creating
        Duration: ~500ms
        Creates:
        - OpenSearch index
        - S3 prefix
        - DynamoDB metadata
    end note

    note right of Ready
        User can now:
        - Query documents
        - Summarize
        - Extract facts
    end note

    note right of Expiring
        TTL reached
        Cleanup scheduled
        within 5 minutes
    end note

    note right of Deleting
        Irreversible
        All data deleted:
        - OpenSearch index
        - S3 documents
        - DynamoDB metadata
    end note
```

---

## 2. Session Creation Flow

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant WebApp as Web Application
    participant APIGW as API Gateway
    participant Cognito as Amazon Cognito
    participant SessionSvc as Session Service
    participant DynamoDB as DynamoDB
    participant OpenSearch as OpenSearch
    participant S3 as S3
    participant SQS as SQS
    participant CloudWatch as CloudWatch Logs

    User->>WebApp: Click "Create New Session"
    WebApp->>APIGW: POST /api/v1/sessions
    APIGW->>Cognito: Validate JWT token
    Cognito-->>APIGW: Token valid (user_id, permissions)

    APIGW->>SessionSvc: CreateSession(ttl_hours=4)
    SessionSvc->>SessionSvc: Generate session_id (UUID)
    SessionSvc->>DynamoDB: Create session metadata
    Note over DynamoDB: Table: case_assistant_sessions<br/>PK: session_id<br/>TTL: expires_at

    DynamoDB-->>SessionSvc: Session created

    SessionSvc->>OpenSearch: PUT /vector_store_session_{id}
    Note over OpenSearch: Create temporary index<br/>No replicas (cost optimization)<br/>k-NN enabled

    OpenSearch-->>SessionSvc: 200 OK (index created)

    SessionSvc->>S3: Create prefix /sessions/{id}/
    Note over S3: Session-scoped storage<br/>Lifecycle policy: 1 day retention

    S3-->>SessionSvc: Prefix created

    SessionSvc->>SQS: Schedule cleanup job
    Note over SQS: Delayed message<br/>Delay: ttl_hours * 3600 seconds

    SQS-->>SessionSvc: Cleanup scheduled

    SessionSvc->>CloudWatch: Log session_created event
    SessionSvc-->>APIGW: SessionResponse(session_id, expires_at)
    APIGW-->>WebApp: 201 Created
    WebApp-->>User: Show session details

    Note over User,CloudWatch: Total time: ~500ms<br/>Session now ACTIVE and ready for uploads
```

---

## 3. Document Upload and Ingestion Flow

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant WebApp as Web Application
    participant APIGW as API Gateway
    participant S3 as Amazon S3
    participant SQS as SQS Ingestion Queue
    participant Lambda as Ingestion Lambda
    participant PyPDF as PyPDF Parser
    participant Chunking as Chunking Service
    participant Bedrock as Bedrock Embeddings
    participant OpenSearch as OpenSearch
    participant DynamoDB as DynamoDB
    participant SNS as SNS Notifications
    participant WebSocket as WebSocket Service

    User->>WebApp: Select documents to upload
    WebApp->>APIGW: POST /sessions/{id}/documents
    APIGW-->>WebApp: Presigned S3 URL

    User->>S3: Upload file via presigned URL
    S3-->>WebApp: Upload complete

    S3->>SQS: s3:ObjectCreated:* event
    SQS->>Lambda: Trigger ingestion

    Lambda->>PyPDF: Parse document
    Note over PyPDF: Extract text from PDF<br/>Calculate page numbers<br/>Extract metadata

    PyPDF-->>Lambda: Parsed text + metadata

    Lambda->>DynamoDB: UPDATE document status: PROCESSING
    Lambda->>Chunking: Chunk document (2000/1500/1000 tokens)
    Note over Chunking: Three chunk types:<br/>- Summary (2000t)<br/>- Detail (1500t)<br/>- Fact (1000t)

    Chunking-->>Lambda: Array of chunks

    loop For each chunk
        Lambda->>Bedrock: Generate embedding (Amazon Titan)
        Bedrock-->>Lambda: 1536-dimensional vector
        Lambda->>OpenSearch: Index chunk with vector
        Note over OpenSearch: Index: vector_store_session_{id}<br/>k-NN vector search enabled
    end

    Lambda->>DynamoDB: UPDATE document status: READY
    Lambda->>SNS: Publish document_ready event

    SNS->>WebSocket: Broadcast status update
    WebSocket-->>WebApp: WebSocket message: document.status_update
    WebApp-->>User: Show "Document ready for querying"

    Note over User,WebSocket: Total time: 5-30 seconds<br/>Depends on document size
```

---

## 4. Query Execution Flow

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant WebApp as Web Application
    participant APIGW as API Gateway
    participant QuerySvc as Query Service
    participant Cache as ElastiCache
    participant OpenSearch as OpenSearch
    participant Bedrock as Bedrock LLM
    participant DynamoDB as DynamoDB

    User->>WebApp: Enter query: "Summarize allegations"
    WebApp->>APIGW: POST /sessions/{id}/query
    APIGW->>QuerySvc: ExecuteQuery(query)

    QuerySvc->>Cache: Check cache (query_hash)
    alt Cache hit
        Cache-->>QuerySvc: Cached result
        QuerySvc-->>APIGW: Return cached answer
        APIGW-->>WebApp: 200 OK with cached answer
    else Cache miss
        Note over QuerySvc: Generate query embedding

        QuerySvc->>OpenSearch: Parallel: Vector + BM25
        par Vector Search
            OpenSearch->>OpenSearch: k-NN search (k=20)
        and Keyword Search
            OpenSearch->>OpenSearch: BM25 search (k=20)
        end

        OpenSearch-->>QuerySvc: 40 results (20 vector + 20 keyword)

        Note over QuerySvc: Reciprocal Rank Fusion (RRF)<br/>Combine and re-rank results

        QuerySvc->>OpenSearch: Cross-encoder rerank (20→10)
        OpenSearch-->>QuerySvc: Top 10 chunks

        QuerySvc->>Bedrock: Synthesize answer with context
        Note over Bedrock: Claude 4 Sonnet<br/>Context: Top 10 chunks<br/>Query: "Summarize allegations"

        Bedrock-->>QuerySvc: Generated answer with citations

        QuerySvc->>Cache: Store result (TTL: 1 hour)
        QuerySvc->>DynamoDB: Log query for audit

        QuerySvc-->>APIGW: QueryResponse(answer, citations)
        APIGW-->>WebApp: 200 OK
    end

    WebApp-->>User: Display answer with source citations

    Note over User,DynamoDB: Total time: 2-5 seconds<br/>p95 target: <3 seconds
```

---

## 5. Session Extension Flow

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant WebApp as Web Application
    participant APIGW as API Gateway
    participant SessionSvc as Session Service
    participant DynamoDB as DynamoDB
    participant SQS as SQS
    participant WebSocket as WebSocket Service

    User->>WebApp: Click "Extend Session (+4 hours)"
    WebApp->>APIGW: PUT /sessions/{id}/extend

    APIGW->>SessionSvc: ExtendSessionRequest
    SessionSvc->>DynamoDB: Get session metadata

    DynamoDB-->>SessionSvc: SessionMetadata

    alt Session can be extended
        Note over SessionSvc: Validate:<br/>- State is ACTIVE or READY<br/>- extended_count < 3

        SessionSvc->>SessionSvc: Update expires_at += 4 hours
        SessionSvc->>SessionSvc: Increment extended_count

        SessionSvc->>DynamoDB: UPDATE session metadata
        DynamoDB-->>SessionSvc: 200 OK

        SessionSvc->>SQS: Update cleanup job delay
        Note over SQS: Delete old message<br/>Create new delayed message

        SQS-->>SessionSvc: Rescheduled

        SessionSvc-->>APIGW: ExtendedSessionResponse
        APIGW-->>WebApp: 200 OK (new expires_at)

        WebApp-->>User: Show "Extended to 18:00 UTC"

    else Cannot extend
        Note over SessionSvc: Reject extension:<br/>- Max extensions reached<br/>- Invalid state

        SessionSvc-->>APIGW: 400 Bad Request
        APIGW-->>WebApp: Error response
        WebApp-->>User: Show error message
    end

    Note over User,WebSocket: Max session lifetime: 16 hours<br/>(4 initial + 3 × 4 extensions)
```

---

## 6. Session Deletion Flow (Manual)

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant WebApp as Web Application
    participant APIGW as API Gateway
    participant SessionSvc as Session Service
    participant DynamoDB as DynamoDB
    participant OpenSearch as OpenSearch
    participant S3 as S3
    participant CloudWatch as CloudWatch Logs

    User->>WebApp: Click "Delete Session Now"
    WebApp->>APIGW: DELETE /sessions/{id}

    APIGW->>SessionSvc: DeleteSessionRequest
    SessionSvc->>DynamoDB: UPDATE state: DELETING

    SessionSvc->>OpenSearch: DELETE /vector_store_session_{id}
    Note over OpenSearch: Delete entire index<br/>All chunks and vectors removed

    OpenSearch-->>SessionSvc: 200 OK

    SessionSvc->>S3: DELETE /sessions/{id}/ (recursive)
    Note over S3: Delete all objects:<br/>- Original documents<br/>- Extracted text<br/>- Chunks

    S3-->>SessionSvc: 204 No Content

    SessionSvc->>DynamoDB: DELETE session metadata
    DynamoDB-->>SessionSvc: 200 OK

    SessionSvc->>CloudWatch: Log session_deleted event

    SessionSvc-->>APIGW: 202 Accepted
    APIGW-->>WebApp: Session deletion initiated

    WebApp-->>User: Show "Session deleted successfully"

    Note over User,CloudWatch: Total time: 2-5 seconds<br/>All data permanently removed
```

---

## 7. Automatic Cleanup Flow

```mermaid
sequenceDiagram
    autonumber
    participant EventBridge as EventBridge Scheduler
    participant CleanupLambda as Cleanup Lambda
    participant DynamoDB as DynamoDB
    participant OpenSearch as OpenSearch
    participant S3 as S3
    participant CloudWatch as CloudWatch Logs
    participant SNS as SNS Alerts

    Note over EventBridge: Runs every 5 minutes

    EventBridge->>CleanupLambda: Invoke cleanup function
    CleanupLambda->>DynamoDB: Query expired sessions
    Note over DynamoDB: Query GSI: expiration-index<br/>Filter: expires_at < now<br/>AND state != DELETED

    DynamoDB-->>CleanupLambda: List of expired sessions

    loop For each expired session
        CleanupLambda->>DynamoDB: UPDATE state: DELETING

        CleanupLambda->>OpenSearch: DELETE /vector_store_session_{id}

        alt OpenSearch deletion fails
            CleanupLambda->>CloudWatch: Log error
            CleanupLambda->>SNS: Send alert (failed cleanup)
        else OpenSearch deletion succeeds
            OpenSearch-->>CleanupLambda: 200 OK

            CleanupLambda->>S3: DELETE /sessions/{id}/ (recursive)

            alt S3 deletion fails
                CleanupLambda->>CloudWatch: Log error
                CleanupLambda->>SNS: Send alert
            else S3 deletion succeeds
                S3-->>CleanupLambda: 204 No Content

                CleanupLambda->>DynamoDB: DELETE session metadata

                CleanupLambda->>CloudWatch: Log cleanup_success
            end
        end
    end

    CleanupLambda-->>EventBridge: Cleanup complete

    Note over EventBridge,SNS: Orphaned session SLA:<br/>All expired sessions deleted<br/>within 5 minutes of expiry
```

---

## 8. End-to-End User Journey

```mermaid
graph TB
    Start([User starts]) --> CreateSession[Create session]
    CreateSession --> |~500ms| SessionReady[Session active]

    SessionReady --> UploadDocs[Upload documents]
    UploadDocs --> |5-30s per doc| DocsReady[All documents ready]

    DocsReady --> Query1[Query: Summarize]
    Query1 --> |2-5s| Summary[Summary displayed]

    Summary --> Query2[Query: Extract facts]
    Query2 --> |10-15s| Facts[Structured facts displayed]

    Facts --> Query3[Query: Specific question]
    Query3 --> |2-5s| Answer[Answer with citations]

    Answer --> Decision{User done?}

    Decision --> |No| Query3
    Decision --> |Yes, delete manually| ManualDelete[Delete session]
    Decision --> |Yes, wait for timeout| AutoDelete[Session expires]

    ManualDelete --> |2-5s| Deleted1([All data deleted])
    AutoDelete --> |max 5min after expiry| Deleted2([All data deleted])

    style SessionReady fill:#90EE90
    style DocsReady fill:#90EE90
    style Deleted1 fill:#FFB6C1
    style Deleted2 fill:#FFB6C1
```

---

## 9. Error Handling Flows

### 9.1 Document Upload Failure

```mermaid
sequenceDiagram
    participant User
    participant S3 as S3
    participant SQS as SQS
    participant Lambda as Ingestion Lambda
    participant DynamoDB as DynamoDB
    participant SNS as SNS

    User->>S3: Upload document
    S3->>SQS: Trigger event

    SQS->>Lambda: Process document

    Lambda->>Lambda: Parse document (PyPDF)

    alt Parse fails
        Lambda->>DynamoDB: UPDATE status: ERROR
        Lambda->>DynamoDB: Store error_message
        Lambda->>SNS: Notify user of error
        SNS-->>User: "Document upload failed: corrupted PDF"
    else Parse succeeds
        Lambda->>Lambda: Continue ingestion
    end
```

### 9.2 Query Timeout Handling

```mermaid
sequenceDiagram
    participant User
    participant QuerySvc as Query Service
    participant OpenSearch as OpenSearch
    participant Bedrock as Bedrock LLM

    User->>QuerySvc: Execute query

    QuerySvc->>OpenSearch: Retrieve chunks
    OpenSearch-->>QuerySvc: Top 10 chunks

    QuerySvc->>Bedrock: Synthesize answer

    alt Bedrock timeout (>30s)
        QuerySvc->>QuerySvc: Cancel request
        QuerySvc-->>User: 504 Gateway Timeout
        Note over User,QuerySvc: User can retry query
    else Bedrock responds
        Bedrock-->>QuerySvc: Answer
        QuerySvc-->>User: 200 OK with answer
    end
```

---

## 10. Performance Optimization Flows

### 10.1 Query Caching

```mermaid
sequenceDiagram
    participant User
    participant QuerySvc as Query Service
    participant Cache as ElastiCache
    participant OpenSearch as OpenSearch
    participant Bedrock as Bedrock

    User->>QuerySvc: Query: "Summarize allegations"
    QuerySvc->>Cache: Check cache

    alt Cache miss (first query)
        Cache-->>QuerySvc: Not found
        QuerySvc->>OpenSearch: Retrieve chunks
        QuerySvc->>Bedrock: Generate answer
        Bedrock-->>QuerySvc: Answer
        QuerySvc->>Cache: Store answer (TTL: 1 hour)
        QuerySvc-->>User: Answer
    else Cache hit (repeat query)
        Cache-->>QuerySvc: Cached answer
        QuerySvc-->>User: Answer (instant)
    end
```

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-03-17 | Principal AI Engineer | Initial session lifecycle diagrams |

---

**END OF DOCUMENT**
