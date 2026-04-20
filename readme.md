### Advanced RAG System using MarkItDown(by Microsoft) and LangChain
🚀 Overview

This project implements an advanced Retrieval-Augmented Generation (RAG) system that supports multi-format document ingestion, intelligent chunking, reranking, and summarization.

Unlike basic RAG pipelines, this system focuses on improving retrieval quality through custom document parsing and LLM-based reranking.

🧠 Key Features

## Multi-format support:
PDF, DOCX, PPTX, TXT
Images (OCR-based extraction)
Code files (Python, Java, JS, etc.)
CSV, HTML, logs

## Custom MarkItDown converters:
OCR-based PDF processing
Markdown table extraction
Code structure parsing

## Intelligent Retrieval:
Dynamic chunking based on file type
FAISS vector store for semantic search

🧠 Advanced Enhancements:
LLM-based reranking of retrieved chunks
Chunk merging for better context
Summarization of retrieved content

💬 Interactive UI:
Built using Chainlit
⚙️ Architecture
User Input
   ↓
Document Upload / URL
   ↓
MarkItDown Extraction (Custom Converters)
   ↓
Chunking (Dynamic Strategy)
   ↓
Embeddings + FAISS
   ↓
Top-K Retrieval
   ↓
LLM-based Reranking
   ↓
Chunk Merging + Summarization
   ↓
Final Answer Generation

## Tech Stack
Python
LangChain
Azure OpenAI
FAISS
MarkItDown
Chainlit
Tesseract OCR

## Setup Instructions
git clone <repo>
cd markitdown-rag

pip install -r requirements.txt

Create .env file:

AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_DEPLOYMENT_NAME=your_model
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=your_embedding_model

Run the app:

chainlit run app.py
📌 Usage
Upload a document OR provide a URL
System extracts content using MarkItDown
Ask questions about the content
System retrieves, reranks, and summarizes before answering

## Limitations
No persistent vector storage
LLM-based reranking increases latency
OCR accuracy depends on input quality
