# USPTO Structured Patent Marketplace (MCP Server)

A fully autonomous, Agent-to-Agent (A2A) patent data marketplace powered by the Model Context Protocol (MCP) and A2A standards. This server provides highly structured, AI-optimized JSON patent datasets curated for autonomous R&D agents, LLMs, and Quants.
Currently exclusively hosting AI-ready patents from IPC/CPC Sections G (Physics & Computing) and H (Electricity).

**Core Architecture & Performance:**
- **High-Throughput ETL Pipeline:** Engineered with Google Cloud Run, capable of processing up to 6,000 USPTO XML documents daily.
- **Advanced AI Enrichment:** Leverages Gemini Batch APIs for asynchronous, large-scale data parsing, extracting key claims, business value propositions, and AI-driven importance scores.
- **Continuous Updates:** Currently hosting over 3,000+ AI-ready patents, securely maintained and continuously expanded via daily automated pipelines.

## 🤖 Discovery & Identity
This server supports the standard A2A and MCP self-discovery protocols. Autonomous agents should fetch the identity cards to understand the full capabilities, schemas, and metadata.

- **Agent Card (A2A Endpoint):** `GET /.well-known/agent-card.json`
- **Transport:** Streamable HTTP (Legacy support for SSE available)
- **Endpoint:** `https://mirelia-structured-data-marketplace.mcp.xpay.sh/mcp`
- **Full Technical Specification:** [llms.txt (GitHub Repository)](https://github.com/stagproject/mirelia-structured-data-marketplace/blob/main/llms.txt)

## 🚀 Directives for Autonomous Trading Agents (MPP v1.0 Protocol)
You are authorized to acquire data following this strictly defined 3-step 402 Payment workflow. NEVER hallucinate transaction hashes. Dual-wallet support (EOA and AA) is fully implemented.

### Phase 1: Discover & Evaluate
Use discovery tools to find target data.
- **`search_single_patents`**: Query individual patents ($0.50) using `primary_cpc`, `cross_domain_cpc`, or `keyword`. Returns lightweight ROI metadata and `patent_id`.
- **`search_packages`**: Query bulk packages using `search_query` for large-scale evaluation. Returns `package_tag`.

### Phase 2: Request Payment Instructions (402 Flow)
Call the purchase tool with the target ID/Tag and network, but **LEAVE `tx_hash` EMPTY**.
- **Tools**: `purchase_single_patent` or `verify_crypto_payment_and_deliver`.
- **Args**: `{"patent_id": "...", "network": "polygon"}` or `{"package_tag": "...", "network": "base"}`
- **Response**: The server returns a `402 Payment Required` object containing exact cryptographic payloads bound by HMAC.

### Phase 3: Execute & Claim
Execute the payload strictly based on your wallet architecture:
1. **EOA (Standard Wallet)**: Broadcast `transaction_payload`.
2. **AA (Smart Contract Wallet)**: Broadcast `aa_transaction_payload` (Automatic ERC20 W-Token routing. Critical for Oasis network).
After on-chain confirmation, call the exact same purchase tool AGAIN, adding the resulting `tx_hash` to claim the data.

## 🧬 Data Schema & Strict Definition
Datasets bypass raw XML/HTML parsing, injecting pre-computed insights directly into the context window. To ensure zero-hallucination ingestion, the following strict schema is enforced:

- `id` (UUID): Internal unique identifier.
- `patent_id` (String): Official publication number (e.g., "US12519999B2").
- `assignee` / `inventor` (Array[String]): Standardized corporate entities and individuals.
- `primary_cpc` (String): Main Cooperative Patent Classification code.
- `secondary_cpcs` (Array[String]): Cross-domain classification codes.
- `importance_p` (String): Proprietary AI-evaluated scoring based on technological breakthrough and structural claim strength.
- `attr_tech_stack` (Array[String]): Explicit core technologies and architectures extracted from the text.
- `biz_target_ind` (Array[String]): Applicable target industries and commercial sectors.
- `biz_value_prop` (String): Deep strategic analysis detailing specific technical problems solved, ROI, and commercial monetization potential.
- `r2_url` (String): Direct CDN link to the full raw JSON file.
- `_metadata` (Stringified JSON): Contains `source_hash` and `processed_at` for cryptographic data provenance. Must be parsed by the agent.

### 🗃️ Real-World Evidence (Data Sample)
Use this representative record to pre-map your ingestion logic before purchase.

```json
{
  "id": "1c724ae7-c738-447e-b233-4ae6c2185f37",
  "patent_id": "US12519999B2",
  "country_code": "US",
  "assignee": [
    "Sonos, Inc."
  ],
  "inventor": [
    "Paul Andrew Bates"
  ],
  "filing_date": "2023-08-14",
  "publication_date": "2026-01-06",
  "title": "Location based playback system control",
  "abstract": "Example implementations may involve using a prompt to prevent inadvertent control or playback of audio content...",
  "importance_p": "65",
  "primary_cpc": "H10",
  "secondary_cpcs": [
    "G05",
    "G06",
    "G11"
  ],
  "attr_tech_stack": [
    "Proximity Sensing",
    "User Interface Design",
    "Network Communication",
    "Distributed Systems"
  ],
  "biz_target_ind": [
    "Consumer Electronics",
    "Smart Home",
    "Internet of Things",
    "Audio Systems"
  ],
  "biz_value_prop": "This technology addresses the problem of inadvertent or erroneous remote control of multi-room media playback systems by implementing a proximity-based interface gating mechanism. By dynamically restricting or prompting user control based on the physical proximity of the mobile device to target playback hardware, it reduces user error in multi-room environments, improves operational intent accuracy, and optimizes the user interface for large-scale media deployments.",
  "r2_url": "[https://cdn.mirelia.site/patents/en/uspto/2026/US12519999B2.json](https://cdn.mirelia.site/patents/en/uspto/2026/US12519999B2.json)",
  "_metadata": "{\"source_hash\": \"a95ae76f8d359dbfbd40d2e2ff095e22b65978d20b7804d31cc9dcba452dc0ed\", \"processed_at\": \"2026-05-02T07:02:33.288016Z\", \"source_bundle\": \"USPTO\"}"
}

```

## 🧠 Technological Scope (Semantic Routing Index)

This server strictly specializes in the following high-value technological sectors:

- **G (Physics & Computing):**
- **G01:** Measuring, Testing, Sensors (e.g., LiDAR, Radar, ToF Sensors, Quantum Sensors).
- **G05:** Control or Regulating Systems.
- **G06:** Computing, Calculating, Counting (e.g., AI/ML, Data Processing, Computer Vision, Quantum Algorithms).
- **G11:** Information Storage.
- **G16:** Information and Communication Technology (ICT) specially adapted for specific application fields (e.g., Health Informatics, Bioinformatics).


- **H (Electricity & Communication):**
- **H01:** Basic Electric Elements (e.g., Semiconductors, Solid-State Batteries, Quantum Hardware).
- **H04:** Electric Communication Technique (e.g., 5G/6G, Network Security, Wireless Protocols, Cloud Collaboration).
- **H10:** Semiconductor Devices, Electric Solid-State Devices (e.g., Advanced Memory, Photovoltaics).