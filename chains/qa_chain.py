import threading
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import FileChatMessageHistory
from langchain.prompts import ChatPromptTemplate
from ingest.vector_store import get_vectorstore
from config import LLM_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, HISTORY_DIR
import os

def get_memory(space_id):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    history_path = os.path.join(HISTORY_DIR, f"space_{space_id}.json")
    history = FileChatMessageHistory(history_path)
    return ConversationBufferMemory(
        memory_key="chat_history",
        chat_memory=history,
        return_messages=True,
        output_key="result"
    )

def load_history(space_id):
    history_path = os.path.join(HISTORY_DIR, f"space_{space_id}.json")
    if os.path.exists(history_path):
        history = FileChatMessageHistory(history_path)
        return history.messages
    return []

def background_generate(question, space_id, category_id, memory, output_state):
    try:
        vectordb = get_vectorstore(space_id, category_id)
        retriever = vectordb.as_retriever(search_kwargs={"k": 4})
        docs = retriever.get_relevant_documents(question)
        context = "\n\n".join([d.page_content for d in docs])

        history_msgs = memory.chat_memory.messages
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是企业的智能助手，根据提供的知识库文档回答。\n\n参考文档：\n{context}"),
            *history_msgs,
        ])

        llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base=DEEPSEEK_BASE_URL,
            temperature=0,
            streaming=True
        )

        full_response = ""
        messages = prompt.format_prompt(context=context).to_messages()
        for chunk in llm.stream(messages):
            full_response += chunk.content
            output_state["tokens"] = full_response

        if full_response.strip():
            memory.chat_memory.add_ai_message(full_response)
        output_state["done"] = True
    except Exception as e:
        output_state["tokens"] = f"生成失败：{e}"
        output_state["done"] = True
