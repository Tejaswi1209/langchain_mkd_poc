import os
import chainlit as cl
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from rag_agent import DocumentAgent

# Load environment variables
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

# Initialize LLM and embeddings
llm = AzureChatOpenAI(
    openai_api_key=API_KEY,
    azure_endpoint=AZURE_ENDPOINT,
    deployment_name=AZURE_DEPLOYMENT,
    api_version=API_VERSION,
    temperature=0.3,
    timeout=120,
)

embeddings = AzureOpenAIEmbeddings(
    openai_api_key=API_KEY,
    azure_endpoint=AZURE_ENDPOINT,
    deployment=AZURE_EMBEDDING_DEPLOYMENT,
    api_version=API_VERSION,
    chunk_size=1000
)


# Initialize the agent
agent = DocumentAgent(llm, embeddings)

@cl.on_chat_start
async def start():
    await cl.Message(
        "📎 Please upload a file "
        "(PDF, PPTX, DOCX, XLSX, images, HTML, CSV/JSON/XML) to begin."
    ).send()

@cl.on_message
async def handle_message(message: cl.Message):
    upload = message.elements[0] if message.elements else None
    content = message.content.strip() or None

    # Check if content is a URL
    if content and agent.is_url(content):
        try:
            await cl.Message("🌐 Processing URL...").send()
            num_chunks, resp = agent.process_stream(content, source_type="url")
            await cl.Message(resp).send()
            await cl.Message("💬 Ask me anything about the processed content.").send()
            return
        except Exception as e:
            await cl.Message(f"❌ Error processing URL: {e}").send()
            return

    # Handle file upload
    if upload:
        source = upload.path 
        try:
            num_chunks, resp = agent.process_file(source)
            await cl.Message(resp).send()

            if content and not agent.is_url(content):
                try:
                    answer = await agent.answer_query(content)
                    await cl.Message(answer).send()
                except Exception as e:
                    await cl.Message(f"❌ Error processing query: {e}").send()
            else:
                await cl.Message("💬 Ask me anything about the uploaded document.").send()
            return
        except Exception as e:
            await cl.Message(f"❌ Error processing source: {e}").send()
            return

    # Handle regular queries
    if content and not agent.is_url(content):
        try:
            answer = await agent.answer_query(content)
            await cl.Message(answer).send()
        except Exception as e:
            await cl.Message(f"❌ Error processing query: {e}").send()
    else:
        await cl.Message("❌ Please upload a file, provide a URL, or ask a valid question.").send()