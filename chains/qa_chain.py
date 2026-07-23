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

def background_generate(question, space_ids, memory, output_state, style="default"):
    """支持回答风格：
    - default: 专业严谨
    - friend: 朋友聊天，轻松江湖气
    """
    try:
        if not space_ids:
            space_ids = []

        all_docs = []
        for sid in space_ids:
            vectordb = get_vectorstore(sid)
            retriever = vectordb.as_retriever(search_kwargs={"k": 4})
            docs = retriever.get_relevant_documents(question)
            all_docs.extend(docs)

        # 去重并限制数量
        seen = set()
        unique_docs = []
        for d in all_docs:
            if d.page_content not in seen:
                seen.add(d.page_content)
                unique_docs.append(d)
        unique_docs = unique_docs[:4]
        context = "\n\n".join([d.page_content for d in unique_docs])

        # 根据风格选择不同的System Prompt
        if style == "friend":
            system_prompt = (
                "你是一个知识渊博又随性的朋友，说话带着江湖气和人情味，像在深夜烧烤摊上聊人生。"
                "你可以用轻松幽默的语气回答，但**所有事实信息必须严格来源于下面的参考文档**，不能凭空编造。"
                "如果文档里没有答案，就直接告诉朋友：“这事儿文档里没写，要不咱问下知情的同事？”"
                "\n\n参考文档：\n{context}"
            )
        else:  # default
            system_prompt = (
                "你是企业的智能助手，根据提供的知识库文档严谨、准确地回答。"
                "\n\n参考文档：\n{context}"
            )

        history_msgs = memory.chat_memory.messages
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            *history_msgs,
        ])

        llm = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base=DEEPSEEK_BASE_URL,
            temperature=0.3 if style == "friend" else 0,  # 朋友风格稍微提高创意度
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