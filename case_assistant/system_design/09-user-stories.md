# User Stories - Case Assistant Chat

**Domain**: Australian Taxation Law (100% Focus)
**Document Version**: 1.1.0
**Date**: 2026-03-25
**Status**: Product Requirements
**Audience**: Product Managers, Engineering, QA Teams

> **SCOPE**: This document defines user stories for the Case Assistant Chat system, an Australian tax law-focused conversational AI assistant that enables tax professionals to upload tax law documents and query them through natural language.

---

## Table of Contents

- [Epic Overview](#epic-overview)
- [User Story 1.1: Document Upload](#user-story-11-document-upload)
- [User Story 1.2: Natural Language Query](#user-story-12-natural-language-query)
- [User Story 1.3: Session Management](#user-story-13-session-management)
- [User Story 1.4: Table Extraction](#user-story-14-table-extraction)
- [Acceptance Criteria Summary](#acceptance-criteria-summary)

---

## Epic Overview

**Epic**: Australian Tax Law Case Assistant - Document Upload & Query

**Business Value**: Enable Australian tax professionals (tax agents, accountants, tax lawyers, ATO officers) to quickly find accurate tax law information and precedent from complex legal documents without manual review, reducing research time from hours to minutes.

**Target Users**:
- Individual taxpayers researching Australian tax law
- Registered tax agents and BAS agents
- CPAs Australia and CA ANZ members
- Tax lawyers and legal professionals
- ATO officers and tax compliance staff
- Tax policy advisors and analysts

**Key Differentiators**:
- **Australian Tax Law Only**: 100% focused on Australian taxation law (ITAA 1936, ITAA 1997, Taxation Rulings, AAT/Federal Court decisions)
- **Table Intelligence**: VLM+GPU processing preserves complex ATO form structures (tax return schedules, GST calculations, FBT schedules)
- **Session Persistence**: Conversation history persists indefinitely; documents expire after 7-day inactivity
- **Legal Citations**: Proper Australian tax law citation format (ITAA s, TR, TD, AAT decisions, Federal Court citations)

---

## User Story 1.1: Document Upload

**Title**: Upload Australian Tax Law Documents for Case Research

**As a** Australian tax professional
**I want to** upload PDF or Word documents containing Australian tax law materials
**So that** the system can index and make the content searchable through natural language queries

### User Personas

| Persona | Description | Typical Documents |
|---------|-------------|-------------------|
| **Taxpayer** | Individual researching personal tax matters | ATO publications, tax rulings |
| **Tax Agent** | Registered tax agent preparing client returns | ITAA sections, ATO rulings, ATO IDs |
| **Tax Lawyer** | Legal professional building case arguments | AAT decisions, Federal Court cases, High Court precedents |
| **ATO Officer** | Compliance officer verifying tax positions | ATO manuals, law administration practice statements, MT/PS guidance |
| **Accountant** | CPA Australia/CA ANZ advising clients | Taxation rulings, determination documents, interpretation guidance |

### Acceptance Criteria

#### Document Upload

| Criterion | Requirement |
|-----------|-------------|
| **Batch Upload** | User can upload single or multiple documents (up to 50 files per batch) |
| **Supported Formats** | PDF, DOCX (optimised for legal documents) |
| **Maximum File Size** | 100 MB per file (supports large AAT and Federal Court decisions) |
| **Progress Indicator** | Real-time upload status shown to user |

#### Document Metadata

| Criterion | Requirement |
|-----------|-------------|
| **Automatic Extraction** | System extracts title, author, creation date |
| **Table Detection** | System flags pages containing tables for VLM+GPU processing |
| **Delta Detection** | System calculates page-level SHA-256 hashes for efficient re-upload |
| **Custom Tags** | User can optionally add tags: tax category, jurisdiction (federal/state), income year |
| **Document Type** | System categorises: ITAA 1936, ITAA 1997, Taxation Ruling (TR), Tax Determination (TD), AAT Decision, Federal Court Case, High Court Case, ATO Interpretive Decision, Law Administration Practice Statement, Tax Ruling (TR), Other |

#### Upload Feedback

| Criterion | Requirement |
|-----------|-------------|
| **Upload Confirmation** | User receives confirmation when upload completes |
| **Ingestion Notification** | User notified when indexing complete (<10MB docs: <5 minutes) |
| **Error Messaging** | Clear error messages for invalid format or size limit exceeded |
| **Processing Status** | Status pipeline visible: uploading → extracting → chunking → embedding → ready |

#### Document Management

| Criterion | Requirement |
|-----------|-------------|
| **Document List** | User can view uploaded documents with status (processing, ready, failed) |
| **Delete Documents** | User can delete documents they uploaded |
| **Re-upload** | User can re-upload to update content (delta detection reduces processing time by 90%) |
| **Document Expiration** | Documents auto-deleted after 7 days of inactivity |
| **Session Persistence** | Conversation history persists even after document deletion |
| **Table Preservation** | Complex ATO form tables preserve structure integrity |

#### Search Verification

| Criterion | Requirement |
|-----------|-------------|
| **Immediate Search** | Search available immediately after indexing completes |
| **Relevant Excerpts** | Results show relevant excerpts from uploaded tax law documents |
| **Source References** | Results show document name, page number, and section reference |
| **Table Data** | Search includes both text content and table-extracted data |
| **Cross-Page Tracking** | Search handles content spanning page boundaries |

---

## User Story 1.2: Natural Language Query

**Title**: Ask Australian Tax Law Questions About Uploaded Documents

**As a** Australian tax professional
**I want to** ask questions in natural language about the uploaded Australian tax law documents
**So that** I can get accurate, contextual answers with proper legal citations without reading entire documents

### Acceptance Criteria

#### Query Input

| Criterion | Requirement |
|-----------|-------------|
| **Natural Language** | User can type natural language questions about Australian tax law |
| **Follow-up Questions** | Conversation context maintained for follow-up queries |
| **Comparative Queries** | System handles comparisons between code sections, regulations, or cases |
| **Precedent Queries** | System searches for supporting AAT, Federal Court, and High Court decisions |

#### Response Quality

| Criterion | Requirement |
|-----------|-------------|
| **Direct Answers** | System provides direct answers with source citations |
| **Confidence Levels** | System indicates confidence: high/medium/low |
| **Relevant Excerpts** | System shows relevant document excerpts with page references |
| **Source Distinction** | System distinguishes primary sources (ITAA, GST Act, FBTAA) from secondary (AAT decisions, Federal Court cases) |
| **Response Time** | <5 seconds for typical Australian tax law queries |

#### Conversation Context

| Criterion | Requirement |
|-----------|-------------|
| **Context Maintenance** | System maintains conversation context across multiple turns |
| **Conversation History** | User can view full conversation history |
| **Session Persistence** | User can start new conversation while preserving session history |
| **Document Tracking** | System tracks which documents were referenced in conversation |

#### Answer Quality

| Query Type | Examples | Expected Behaviour |
|------------|----------|-------------------|
| **Simple Lookup** | "What is the period of review under section 105-55 of schedule 1 to the Taxation Administration Act 1953?" | Direct answer with section citation |
| **Comparative** | "How does the general deduction provision in s 8-1 ITAA 1997 differ from s 8-5?" | Side-by-side comparison with distinctions |
| **Precedent-Based** | "What factors did the AAT consider in [case name]?" | Summary of case with citation |
| **Complex Analysis** | "How do the CGT main residence exemption rules apply when I move out and rent the property?" | Multi-source answer with ITAA 1997 and ruling citations |
| **Table Queries** | "What is the income tax-free threshold for 2024-25?" | Extracts from ATO tax table with proper row/column reference |
| **Ruling Queries** | "What does TR 95/D1 say about employee travel allowances?" | Direct ruling reference with paragraph citations |

#### Table Handling

| Criterion | Requirement |
|-----------|-------------|
| **Table Extraction** | VLM+GPU preserves table structure from ATO forms, tax return schedules, financial statements |
| **Table Queries** | Answers about table data include row/column references |
| **Cross-Page Tables** | Handles tables spanning multiple pages with merged cells |
| **Nested Tables** | Preserves nested header structures in complex ATO schedules |

#### Compliance & Safety

| Criterion | Requirement |
|-----------|-------------|
| **Tax Law Scope** | System operates exclusively within Australian tax law domain |
| **Scope Boundary** | System refuses general legal advice outside tax law |
| **Disclaimers** | Responses include disclaimer: "For informational purposes, not legal or tax advice" |
| **Citation Accuracy** | All claims include source citations |

---

## User Story 1.3: Session Management

**Title**: Manage Persistent Conversations Across Sessions

**As a** Australian tax professional
**I want to** return to previous conversations and continue my research
**So that** I don't lose context when working on complex tax matters over multiple days

### Acceptance Criteria

#### Session Lifecycle

| Criterion | Requirement |
|-----------|-------------|
| **Session Creation** | New session created on first interaction |
| **Session Persistence** | Conversation history persists indefinitely |
| **Session Retrieval** | User can view and resume past sessions |
| **Session Deletion** | User can delete sessions manually |

#### Document Lifecycle

| Criterion | Requirement |
|-----------|-------------|
| **Document TTL** | Documents auto-delete after 7 days of inactivity |
| **TTL Extension** | Document access resets TTL timer |
| **History Preservation** | Conversation history persists after document deletion |
| **Document Re-upload** | User can re-upload documents to continue research |

#### User Experience

| Criterion | Requirement |
|-----------|-------------|
| **Session List** | User can view all past sessions with timestamps |
| **Search Sessions** | User can search past sessions by topic or query |
| **Export Conversation** | User can export conversation history (PDF/DOCX) |
| **Clear Context** | User can start fresh conversation while preserving session history |

---

## User Story 1.4: Table Extraction

**Title**: Accurately Extract and Query Complex Australian Tax Tables

**As a** Australian tax professional
**I want to** ask questions about complex ATO tables and schedules
**So that** I can get accurate data from ATO forms and tax schedules without manual lookup

### Acceptance Criteria

#### Table Detection

| Criterion | Requirement |
|-----------|-------------|
| **Page-Level Detection** | System detects tables on each page before chunking |
| **Table Types** | Handles: simple tables, merged cells, nested headers, cross-page tables |
| **VLM Routing** | Table pages routed to VLM+GPU processing |
| **Text Routing** | Text-only pages use standard extraction (cost optimisation) |

#### Table Extraction Quality

| Table Type | Example | Expected Behaviour |
|------------|---------|-------------------|
| **Simple Tables** | Basic 2-column rate tables (e.g., Medicare levy) | Standard extraction, no GPU needed |
| **Merged Cells** | ATO tax return schedules with spanned cells | VLM+GPU preserves cell boundaries |
| **Nested Headers** | Multi-level column headers (e.g., GST calculations) | VLM+GPU extracts hierarchical structure |
| **Cross-Page Tables** | Tables spanning multiple pages (e.g., company tax return schedules) | Tracks continuity, preserves relationships |
| **Financial Tables** | Schedules with numbers, calculations (e.g., FBT return) | Preserves numeric formatting and calculations |
| **Tax Tables** | Individual income tax rate tables | Preserves bracket structures and thresholds |

#### Query Support

| Criterion | Requirement |
|-----------|-------------|
| **Table Queries** | "What is the tax-free threshold for 2024-25?" → Returns value from ATO tax table |
| **Cell References** | Answers include row/column references |
| **Table Context** | Answers include table headers and labels |
| **Comparison Queries** | "Compare the tax rates for the 3rd and 4th brackets" → Side-by-side table data |

---

## Acceptance Criteria Summary

### Functional Requirements Matrix

| Feature | Priority | Complexity | Dependencies |
|---------|----------|------------|--------------|
| **Document Upload** | P0 | Medium | S3 storage, ingestion pipeline |
| **Table Detection** | P0 | High | VLM+GPU infrastructure |
| **Vector Search** | P0 | Medium | Vector database, embeddings |
| **Natural Language Queries** | P0 | High | LLM integration, orchestrator |
| **Session Persistence** | P0 | Medium | Session store, TTL management |
| **Australian Legal Citations** | P1 | Medium | Citation parser, validator (ITAA, TR, TD, AAT) |
| **Export Conversations** | P2 | Low | PDF/DOCX generation |
| **Session Search** | P2 | Medium | Session metadata indexing |

### Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | Document ingestion: <5 min for <10MB docs; Query response: <5 seconds |
| **Scalability** | Support 10x more users through incremental ingestion (90% cost reduction) |
| **Availability** | Single-region deployment with 99.9% uptime target |
| **Security** | Documents auto-delete after 7-day inactivity; sessions persist indefinitely |
| **Compliance** | Australian tax law scope only; legal disclaimers included; no general legal advice |
| **Citation Standards** | Support Australian tax citation formats: ITAA 1936/1997, TR, TD, AAT decisions, Federal Court citations |

---

## Related Documents

- **[01-chat-architecture.md](./01-chat-architecture.md)** - Chat application architecture and flow
- **[02-document-ingestion.md](./02-document-ingestion.md)** - Document ingestion pipeline with VLM table processing
- **[03-message-routing.md](./03-message-routing.md)** - Message routing and orchestrator
- **[04-session-lifecycle.md](./04-session-lifecycle.md)** - Session state management and TTL
- **[05-evaluation-strategy.md](./05-evaluation-strategy.md)** - Quality metrics and testing framework

---

## Change History

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-03-25 | Updated for Australian taxation context (ITAA, ATO rulings, AAT decisions, Australian legal citations) |
| 1.0.0 | 2026-03-25 | Initial user story documentation for Case Assistant Chat |

---

**NOTE**: These user stories reflect the Australian tax law specialisation of the Case Assistant system. For general legal or internal knowledge assistant requirements, refer to separate product specifications.

## Key Australian Tax Law References

**Primary Legislation**:
- Income Tax Assessment Act 1936 (ITAA 1936)
- Income Tax Assessment Act 1997 (ITAA 1997)
- Fringe Benefits Tax Assessment Act 1986 (FBTAA)
- A New Tax System (Goods and Services Tax) Act 1999 (GST Act)
- Taxation Administration Act 1953 (TAA)

**ATO Guidance**:
- Taxation Rulings (TR)
- Tax Determinations (TD)
- ATO Interpretive Decisions (ATO ID)
- Law Administration Practice Statements (PS LA)
- Miscellaneous Taxation Rulings (MT)

**Tribunal & Court Decisions**:
- Administrative Appeals Tribunal (AAT) decisions
- Federal Court of Australia decisions
- Full Court of the Federal Court decisions
- High Court of Australia decisions

**Professional Bodies**:
- CPA Australia
- Chartered Accountants Australia and New Zealand (CA ANZ)
- Tax Institute of Australia
- Institute of Public Accountants (IPA)
