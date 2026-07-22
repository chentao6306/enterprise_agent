# chains/auto_classifier.py
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from config import LLM_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
import json


def suggest_category_and_tags(text: str, existing_categories: list):
    """利用LLM建议最适合的类别和标签"""
    categories_str = "\n".join([f"- {c.name}: {c.description}" for c in existing_categories])

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个企业知识库管理助手。请根据文档内容，从以下现有类别中选择最合适的一个类别ID，并生成3-5个标签。
输出格式必须是JSON：{{"category_id": 整数或null, "tags": ["标签1", "标签2"]}}
如果没有合适的类别，category_id可以为null。

现有类别：
{categories_str}"""),
        ("human", "文档内容片段：\n{text}")
    ])

    llm = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base=DEEPSEEK_BASE_URL,
        temperature=0
    )

    messages = prompt.format_prompt(categories_str=categories_str, text=text[:3000]).to_messages()
    res = llm(messages).content
    try:
        data = json.loads(res)
        return data.get("category_id"), data.get("tags", [])
    except:
        return None, []