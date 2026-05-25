<div align="center">

# 📄 DocuMind

### AI-powered document analysis system

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![LangChain](https://img.shields.io/badge/LangChain-0.2-1C3C3C?style=for-the-badge&logo=chainlink&logoColor=white)](https://langchain.com)
[![Phi3](https://img.shields.io/badge/Phi3-Microsoft-0078D4?style=for-the-badge&logo=microsoft&logoColor=white)](https://ollama.com/library/phi3)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-000000?style=for-the-badge)](https://ollama.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-FF6B35?style=for-the-badge)](https://trychroma.com)

*Upload any PDF and ask questions about it in natural language — powered by RAG architecture*

[Features](#-features) · [Architecture](#️-architecture) · [Setup](#️-setup) · [API](#-api-reference)

</div>

---

## 📌 Overview

DocuMind is a **Retrieval-Augmented Generation (RAG)** system that allows users to upload PDF documents and interact with them through natural language questions.

The system retrieves semantically relevant fragments from the document and generates accurate, context-grounded answers using **Microsoft Phi3** running locally via Ollama — no data is sent to external servers.

Built as a portfolio project demonstrating real-world AI integration, async job queuing, and production-ready Flask architecture.

---

## ✨ Features

- 📤 **PDF Upload & Processing** — extracts and chunks text automatically
- 🔍 **Semantic Search** — finds relevant fragments using multilingual vector embeddings
- 🤖 **Local AI Engine** — Microsoft Phi3 via Ollama, runs 100% on your machine
- ⚡ **Async Job Queue** — handles multiple concurrent users without blocking
- 🧹 **Auto Cache Cleanup** — clears old documents automatically per session
- 🌐 **REST API** — clean endpoints for upload, ask, and status polling
- 📱 **Responsive UI** — dark Material Design interface

