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

def background_generate(question, space_ids, memory, output_state):
    """
    space_ids: 一个列表，包含需要检索的空间ID。若为空或None，则检索当前空间。
    """
    try:
        if not space_ids:
            space_ids = [None]  # 兼容，但实际上不会传入None

        all_docs = []
        # 遍历每个空间，检索文档
        for sid in space_ids:
            vectordb = get_vectorstore(sid)
            retriever = vectordb.as_retriever(search_kwargs={"k": 4})
            docs = retriever.get_relevant_documents(question)
            all_docs.extend(docs)

        # 按相似度取前4条（若需要更精确的排序，可改用Chroma的相似度分数，此处简单合并）
        # 限制数量避免token超限
        unique_docs = []
        seen = set()
        for d in all_docs:
            if d.page_content not in seen:
                seen.add(d.page_content)
                unique_docs.append(d)
        unique_docs = unique_docs[:4]

        context = "\n\n".join([d.page_content for d in unique_docs])

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