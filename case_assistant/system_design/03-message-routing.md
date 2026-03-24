# Message Types and Routing

## 1.4 Message Types and Routing

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

---

## What is an Orchestrator?

An **Orchestrator** is a message routing component that uses LLM-based intent classification to determine the appropriate processing path **before** any expensive operations (vector DB queries, LLM generation) are executed.

### Key Characteristics

| Aspect | Description |
|--------|-------------|
| **Decision Point** | First component that processes every incoming message |
| **Single LLM Call** | Determines intent + scope + routing in one efficient call |
| **Cost Optimization** | Routes ~30% of messages to low-cost paths (greetings, clarifications) |
| **Pre-DB Classification** | Makes routing decisions BEFORE hitting vector database |
| **Not an Agent** | It's a router/classifier, not an autonomous decision-maker |

### Orchestrator vs Agent

| Orchestrator | Agent |
|--------------|-------|
| Routes messages based on intent | Makes autonomous decisions |
| Single decision point per message | Multi-step reasoning chains |
| Pre-determined paths | Dynamic behavior |
| Fast, predictable | Slower, exploratory |
| Best for: Chat applications | Best for: Complex workflows |

---

## Message Types

### 1. Chat Messages
- **Description**: User questions or comments about documents
- **Examples**: "What are the key dates?", "Explain this section"
- **Processing**: Requires intent classification and routing

### 2. Command Messages
- **Description**: Structured commands with specific syntax
- **Examples**: `/summarize`, `/extract facts`, `/export csv`
- **Processing**: Specialized handlers with structured output

### 3. Document Actions
- **Description**: File operations related to documents
- **Examples**: Upload, delete, download documents
- **Processing**: Async pipeline with status updates

### 4. System Messages
- **Description**: Connection and lifecycle events
- **Examples**: User connected, session expired, error notifications
- **Processing**: Session management and notifications

---

## Intent Classification

The orchestrator classifies messages into one of four intents:

### 1. Greeting
- **Indicators**: "hi", "hello", "hey", greetings
- **Action**: Instant response, no vector DB query, no LLM generation
- **Example Response**: "Hello! How can I help you today?"

### 2. Vague
- **Indicators**: Insufficient context, unclear request
- **Action**: Ask clarification question (max 2 rounds)
- **Example**: User says "what" → System asks "What would you like to know about the document?"

### 3. Abusive
- **Indicators**: Offensive language, spam, inappropriate content
- **Action**: Reject immediately, no processing
- **Example Response**: "I'm here to help with tax law questions. Please rephrase your request."

### 4. RAG Query
- **Indicators**: Specific question about uploaded documents
- **Action**: Full retrieval-augmented generation path
- **Processing**: Vector DB search → LLM generation → Streaming response

---

## Cost-Optimized Paths

### Greeting Path
```
User: "hi"
  ↓
Orchestrator: Intent=greeting
  ↓
Response: "Hello! How can I help?"
  ↓
Cost: $0 (no vector DB, no LLM generation)
```

### Clarification Path
```
User: "what"
  ↓
Orchestrator: Intent=vague
  ↓
System: "What would you like to know about the document?"
  ↓
User: "key dates"
  ↓
Orchestrator: Intent=rag_query (now clarified)
  ↓
Full RAG processing
```

### Reject Path
```
User: [offensive content]
  ↓
Orchestrator: Intent=abusive
  ↓
Response: "Please rephrase your request appropriately."
  ↓
Cost: Minimal (single orchestrator call)
```

### RAG Path (Standard)
```
User: "What are the key tax dates?"
  ↓
Orchestrator: Intent=rag_query, Scope=user_only
  ↓
Vector DB search → LLM generation → Stream response
  ↓
Cost: Standard (vector DB + LLM)
```

---

## Search Scope Classification

The orchestrator also determines the appropriate search scope:

| Scope | Description | When Used |
|-------|-------------|-----------|
| **system_only** | Query about system features | "How do I upload a document?" |
| **user_only** | Query about uploaded documents | "What are the key dates in this case?" |
| **hybrid** | Combines system and document context | "Summarize this document using the system's format" |

---

## Response Types

### 1. Streaming Response
- **Use Case**: Chat messages requiring LLM generation
- **Delivery**: Token-by-token streaming
- **Example**: Explaining a tax law concept

### 2. Structured Data
- **Use Case**: Command messages requiring extraction
- **Format**: JSON or CSV
- **Example**: `/extract facts` returns structured fact list

### 3. Status Update
- **Use Case**: Document processing and system events
- **Content**: Progress indicators, completion notifications
- **Example**: "Document processed and ready for queries"

### 4. Error Response
- **Use Case**: Failed operations with recovery options
- **Tone**: User-friendly and actionable
- **Example**: "Document upload failed. Please try again or contact support."

---

## Routing Flow Summary

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

---

## Related Documents

- **[01-chat-architecture.md](./01-chat-architecture.md)** - Chat application architecture
- **[04-session-lifecycle.md](./04-session-lifecycle.md)** - Session lifecycle management
- **[06-core-components.md](./06-core-components.md)** - Component descriptions
