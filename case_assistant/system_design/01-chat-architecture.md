# 1. High-Level Architecture

## Table of Contents

- [1.1 Chat Application Architecture (Conceptual)](#11-chat-application-architecture-conceptual)
- [1.2 Chat Conversation Flow](#12-chat-conversation-flow)

---

## 1.1 Chat Application Architecture (Conceptual)

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

### Layer Descriptions

#### Client Layer
- **Web Application**: React SPA providing the primary interface
- **Mobile Apps**: Native iOS and Android applications

#### Connection Layer
- **REST API**: HTTP/HTTPS endpoints for stateless operations
- **WebSocket API**: Real-time bidirectional communication for streaming
- **Authentication Service**: JWT token-based authentication

#### Application Layer
- **Connection Manager**: Manages WebSocket connections and sessions
- **Chat Engine**: Core orchestration for chat conversations
- **Session Manager**: Manages temporary session lifecycle
- **Document Manager**: Handles document upload, processing, and retrieval

#### Intelligence Layer
- **Retriever**: Hybrid search combining vector and keyword search
- **Synthesizer**: LLM integration for response generation
- **Fact Extractor**: Structured data extraction
- **Citation Validator**: Source verification and accuracy checking

#### Storage Layer
- **Vector Database**: Per-session vector indices with embeddings and metadata
- **Document Storage**: Original files and processed chunks
- **Session Store**: Conversation history
- **Metadata Store**: Session info, document tracking, status

#### Background Processing
- **Document Ingestion Pipeline**: Async processing (extract → chunk → embed)
- **Cleanup Service**: Session expiration and auto-deletion

---

## 1.2 Chat Conversation Flow

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

### Flow Phases

#### Session Initialization
1. User connects to chat application
2. Session manager creates new session
3. Storage initializes session-specific resources
4. Session ready for user interaction

#### Document Upload
1. User uploads legal document
2. Document stored in document storage
3. Ingestion pipeline triggered for processing

#### Query Processing
1. User message stored in session
2. Retriever searches vector database for relevant content
3. Context retrieved and assembled
4. LLM generates response with citations
5. Citation validation runs asynchronously
6. Complete response streamed to user

#### Follow-up Questions
1. Subsequent messages include conversation context
2. Retriever refines search based on conversation history
3. Contextual responses generated

#### Session Persistence
1. On disconnect, session marked inactive
2. Conversation history persisted
3. User can return and resume conversation

---

## Related Documents

- **[02-document-ingestion.md](./02-document-ingestion.md)** - Document ingestion pipeline details
- **[03-message-routing.md](./03-message-routing.md)** - Message routing and orchestrator
- **[04-session-lifecycle.md](./04-session-lifecycle.md)** - Session lifecycle management
- **[06-core-components.md](./06-core-components.md)** - Component descriptions
