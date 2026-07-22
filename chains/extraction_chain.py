from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Optional
from config import LLM_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

class ContractInfo(BaseModel):
    party_a: str = Field(description="甲方，通常为委托方或购买方")
    party_b: str = Field(description="乙方，通常为承接方或服务方")
    contract_amount: Optional[float] = Field(description="合同总金额，单位元")
    start_date: Optional[str] = Field(description="合同开始日期，格式YYYY-MM-DD")
    end_date: Optional[str] = Field(description="合同结束日期，格式YYYY-MM-DD")
    project_name: Optional[str] = Field(description="项目名称")
    payment_terms: Optional[str] = Field(description="付款条件或里程碑描述")
    ip_ownership: Optional[str] = Field(description="知识产权归属描述")
    liability_clause: Optional[str] = Field(description="违约责任条款描述")

def extract_contract_info(text: str):
    parser = PydanticOutputParser(pydantic_object=ContractInfo)
    format_instructions = parser.get_format_instructions()

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的合同解析助手。请从以下合同文本中提取关键信息，严格按照指定的 JSON 格式输出。\n{format_instructions}"),
        ("human", "合同文本：\n{contract_text}")
    ])

    llm = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base=DEEPSEEK_BASE_URL,
        temperature=0
    )

    _input = prompt.format_prompt(contract_text=text, format_instructions=format_instructions)
    output = llm(_input.to_messages())
    try:
        parsed = parser.parse(output.content)
        return parsed
    except Exception:
        return None