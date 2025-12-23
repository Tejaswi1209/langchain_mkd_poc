# from pptx_converter import normalize_and_repair, PPTXConverter
# from postprocess_schema import strict_heading_value_markdown
import time
from markitdown import MarkItDown
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
import io
import tempfile
import hashlib
from PIL import Image
import pytesseract
import pandas as pd
import requests
from urllib.parse import urlparse
from typing import Union, BinaryIO

from code_parser_converter import CodeParserConverter
from markdown_table_converter import MarkdownTableConverter
from ocr_pdf_converter import OCRPDFConverter
#from pptx_converter import PPTXConverter

IMAGE_EXTS = {'.png', '.jpg', '.jpeg'}

class DocumentAgent:
   
    def __init__(self, llm, embeddings):
        self.llm = llm
        self.embeddings = embeddings
        self.vector_store = None
        

    def is_url(self, path: str) -> bool:
        """Check if the path is a URL."""
        return path.startswith(('http://', 'https://'))

    def extract_metadata(self, file_path):
        """Extract metadata for the given file."""
        file_stats = os.stat(file_path)
        file_size = file_stats.st_size
        readable_size = self.format_file_size(file_size)
        metadata = f"**File Name**: {os.path.basename(file_path)}\n"
        metadata += f"**File Size**: {readable_size}\n"
        metadata += f"**Created On**: {time.ctime(file_stats.st_ctime)}\n"
        return metadata

    def format_file_size(self, size):
        """Convert file size to a human-readable format."""
        for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0

    def process_stream(self, source: Union[str, bytes, BinaryIO], source_type: str = "auto", filename: str = None, **kwargs):
        """Process a stream source."""
        pass

    def process_file(self, file_or_url):
        """ handles both files and URLs."""
        # Check if it's a URL
        if self.is_url(file_or_url):
            return self.process_stream(file_or_url, source_type="url")
        
        # Original file processing logic
        md = MarkItDown()
        md.register_converter(MarkdownTableConverter(), priority=5.0)
        md.register_converter(OCRPDFConverter(), priority=5.0)
        try:
            if not os.path.exists(file_or_url):
                raise RuntimeError("❌ Only local files are supported.")

            ext = os.path.splitext(file_or_url)[1].lower()
            print(f"🔄 Detected file extension: {ext}")
            chunk_size, chunk_overlap = self.adjust_chunking_params(ext)
            self.splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            file_name = os.path.basename(file_or_url)
            file_hash = hashlib.md5(file_or_url.encode()).hexdigest()
            file_dir = os.getcwd()
            md_file_path = os.path.join(file_dir, f"{file_name}_{file_hash}.md")


            # Reuse markdown if already extracted
            if os.path.exists(md_file_path):
                print(f"✅ Markdown file already exists: {md_file_path}")
                with open(md_file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                print(f"Processing file: {file_or_url}")
                if ext in IMAGE_EXTS:
                    try:
                        img = Image.open(file_or_url)
                        text = pytesseract.image_to_string(img)
                    except pytesseract.TesseractNotFoundError:
                        raise RuntimeError("Tesseract OCR engine not found.")
                elif ext == ".csv":
                    try:
                        df = pd.read_csv(file_or_url, encoding='utf-8', engine='python')
                        text = df.head(20).to_markdown(index=False)
                        print("✅ CSV converted using pandas.")
                    except Exception as e:
                        raise RuntimeError(f"❌ CSV decoding failed: {e}")
                elif ext == ".pdf":
                    print(f"🔄 Invoking OCRPDFConverter for file: {file_or_url}")
                    result = md.convert(
                        file_or_url,
                        layout="multi_column",
                        ocr_langs="eng",
                        max_pages=20
                    )
                    text = result.text_content or ""
                elif ext == ".log":
                    md = MarkItDown()
                    result = md.convert(file_or_url)
                    text = result.text_content or ""
                elif ext in [".html", ".epub", ".zip"]:
                    result = md.convert(file_or_url)
                    text = result.text_content or ""
                elif ext == ".pptx":
                    result = md.convert(
                        file_or_url,
                        layout="multi_column",
                        ocr_langs="eng",
                        max_pages=20
                    )
                    text = result.text_content or ""
                
                elif ext in [".txt", ".md"]:
                    result = md.convert(file_or_url, encoding="utf-8")
                    text = result.text_content or ""
                elif ext == ".docx":
                    result = md.convert(file_or_url)
                    text = result.text_content or ""
                elif ext in [".py", ".js", ".java", ".cpp", ".c", ".ts"]:
                    md.register_converter(CodeParserConverter(), priority=5.0)
                    result = md.convert(file_or_url)
                    text = result.text_content or ""
                else:
                    result = md.convert(file_or_url)
                    text = result.text_content or ""

                if not text.strip():
                    return None, "❌ No text extracted—check file or OCR support."

                metadata = self.extract_metadata(file_or_url)
                text = f"{metadata}\n\n{text}"

                with open(md_file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"✅ Markdown file created: {md_file_path}")

            # Chunk & embed
            docs = self.splitter.split_text(text)
            self.vector_store = FAISS.from_texts(docs, self.embeddings)
            return len(docs), f"✅ Embedded {len(docs)} chunks from `{file_name}`."

        except Exception as e:
            print(f"❌ Error processing source: {e}")
            raise RuntimeError(f"Error processing source: {e}")
 
    async def rerank_chunks(self, query: str, docs: list):
        scored_docs = []

        for doc in docs:
            prompt = f"""
    You are an intelligent assistant. Rate how relevant the following document chunk is to the user query.

    Query: "{query}"

    Chunk:
    '''{doc.page_content}'''
    
    Respond with a single integer score between 1 (irrelevant) and 10 (highly relevant).
    """
            try:
                score_text = await self.llm.apredict(prompt)
                score = int(score_text.strip().split()[0])
            except:
                score = 5  # fallback mid-score
            scored_docs.append((score, doc))

        # Sort by score descending
        reranked = sorted(scored_docs, key=lambda x: x[0], reverse=True)
        top_docs = [doc for _, doc in reranked[:5]]
        return top_docs
    
    # def filter_relevant_chunks(self, query, docs, threshold=0.7):
    #     relevant_docs = []
    #     for doc in docs:
    #         similarity_score = self.vector_store.similarity_score(query, doc.page_content)
    #         if similarity_score >= threshold:
    #             relevant_docs.append(doc)
    #     return relevant_docs
    def adjust_chunking_params(self, file_type):
        if file_type in ['.py', '.java', '.js']:
            return 500, 50  # Smaller chunks for code
        elif file_type in ['.txt', '.md']:
            return 1500, 100  # Larger chunks for plain text
        else:
            return 1000, 75  # Default values
        
    def merge_chunks(self, top_docs, window_size=3):
        merged_docs = []
        for i in range(0, len(top_docs), window_size):
            merged_content = "\n\n".join(d.page_content for d in top_docs[i:i+window_size])
            merged_docs.append(merged_content)
        return merged_docs

    
    async def summarize_chunks(self, merged_docs):
        summaries = []
        seen_summaries = set()  # Track unique summaries
        for doc in merged_docs:
            prompt = f"Summarize the following document chunk:\n\n{doc}"
            try:
                summary = await self.llm.apredict(prompt)
                summaries.append(summary.strip())
                if summary not in seen_summaries:  # Avoid duplicates
                    summaries.append(summary)
                    seen_summaries.add(summary)
            except:
                summaries.append(doc.page_content)  # Fallback to raw content
        return seen_summaries

    async def answer_query(self, query, file_path=None):
        if not self.vector_store:
            return "❌ Upload a document first!"

        try:
            docs = self.vector_store.similarity_search(query, k=10)  # Retrieve more chunks
            #relevant_docs = self.filter_relevant_chunks(query, docs, threshold=0.7)
            top_docs = await self.rerank_chunks(query, docs)  # Rerank and select top chunks
            for doc in top_docs:
                print(f"top docs are:\n\n {doc} ")
            merged_docs = self.merge_chunks(top_docs, window_size=3)
            seen_summaries = await self.summarize_chunks(merged_docs)
            context = "\n\n".join(seen_summaries)

            prompt = f"""You are a helpful assistant. Based on this context:\n\n{context}\n\nQuestion: {query}\n\nAnswer:"""
            print(f"Prompt sent to LLM:\n{prompt}")

            response = await self.llm.apredict(prompt)
            print(f"LLM Response:\n{response}")
            return response.strip()
        except Exception as e:
            print(f"❌ Error in answer_query: {e}")
            return "❌ Failed to generate a response."
 