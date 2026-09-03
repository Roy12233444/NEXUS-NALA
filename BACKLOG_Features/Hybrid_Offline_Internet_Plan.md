# NALA Hybrid Orchestration: Offline-Capable Internet Integration

This backlog document outlines the architectural plan for introducing a **Hybrid Orchestration System** to NALA. This system allows NALA to operate completely offline (utilizing local LLMs, local databases, and a semantic web cache) while dynamically upscaling to cloud APIs and live web resources the moment internet connectivity is detected.

---

## 1. Dual-Core Model Routing (Local vs. Cloud)

### Goal
Equip NALA's `Cost-Aware Router` with the ability to toggle seamlessly between local inference endpoints and remote cloud APIs based on network availability and task complexity.

### Technical Design
* **Local Inference Providers:** Support integration with:
  * **Ollama API** (`http://localhost:11434`) running `llama3:8b`, `mistral`, or `qwen2.5-coder`.
  * **Llama.cpp / vLLM Server** for high-throughput local inference of quantized models (GGUF/AWQ).
* **Model Mapping Strategy:**
  * *Frontier Tasks (Planning, Done Validation):* Route to `gpt-4o`/`claude-3-5-sonnet` (Online) or locally hosted `llama-3-70b-instruct` / `qwen-2.5-coder-32b` (Offline).
  * *Reflexive Tasks (Sensory processing, tool output analysis):* Route to `gpt-4o-mini`/`claude-3-haiku` (Online) or local `llama3-8b`/`mistral-7b` (Offline).
* **Fallback Chain:** If a cloud model dispatch fails due to an `APIConnectionError` or DNS resolution failure, the router automatically catches the exception, shifts NALA to **Offline State**, and retries the prompt via the local inference provider.

---

## 2. Local Semantic Cache (Offline Search)

### Goal
Provide a local vector index of visited websites and documentation, allowing NALA to perform search queries and read references even without active internet connectivity.

### Technical Design
* **The Web Archiving Engine:**
  * Integrate a lightweight vector store (e.g., **ChromaDB** or **FAISS** running locally in the `/data` directory).
  * Integrate local embedding generation using a fast sentence-transformers model (e.g., `all-MiniLM-L6-v2` via `onnx` or `ollama` embedding API).
* **Online Scraping Pipeline:**
  * When online, every webpage fetched via `web_search` or scrapers is text-extracted, chunked, embedded, and cached in the local vector DB.
  * Pages are indexed by URL, timestamp, semantic content, and tags.
* **Offline Search Tool:**
  * If the agent is offline and requests a web search, the search tool intercepts the request and queries the local vector DB instead.
  * It returns the top-K relevant passages from previously visited sites and cached document libraries.

---

## 3. Graceful Network Detection (Connectivity Sensory Check)

### Goal
Monitor the host system's internet connection status in real-time, feeding network state updates into `SessionState` so the loop and tools can adapt immediately without throwing uncaught connection errors.

### Technical Design
* **Connectivity Sensory Hook:**
  * Add a network check in the `SensoryModule` run loop (polling at ~2.0s interval).
  * Check is performed via a fast non-blocking lookup (e.g., attempting a socket connection to a reliable DNS server like `1.1.1.1:53` or checking OS network interfaces).
* **State Updates:**
  * Maintain `SessionState.metadata["network_status"] = "online" | "offline"`.
* **Dynamic Constraint Adaptation:**
  * If `network_status` changes to `"offline"`:
    * Instruct the planner to avoid scheduling steps that require external API authentication (e.g., remote database syncs, non-local APIs).
    * Switch the `Cost-Aware Router` default target to the local Ollama/vLLM endpoints.

---

## 4. Localized Containerized Tool Runtime

### Goal
Ensure all executor tools (interpreters, database managers, sandbox environments) run locally on the host machine without calling out to cloud runtime sandboxes.

### Technical Design
* **Local Docker Sandboxing:**
  * Wrap tool executions in isolated local Docker containers (using the Python `docker` SDK).
  * Ensure the container image has pre-installed runtimes (Python, Node.js, bash tools) and does not pull remote packages at runtime.
* **Local Mocking of Remote APIs:**
  * Provide fallback mock classes for external APIs (e.g., mock cloud storage tools reading/writing to the local `/data` folder instead of AWS S3 / Google Cloud Storage).

---

**Jai Bajrang Bali 🙏**
