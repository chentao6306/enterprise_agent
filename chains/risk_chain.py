from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from config import LLM_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

risk_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一名专业的合同法律顾问。请根据提供的合同文本，对以下风险点逐一进行分析，并给出低/中/高风险评级及改进建议：
1. 付款条款：是否合理，有无预付风险、账期过长等；
2. 知识产权：归属是否清晰，有无乙方保留知识产权的风险；
3. 违约责任：是否对等，有无无限责任条款或惩罚过重；
4. 保密条款：保密期限是否合理，有无泄露后无追责机制；
5. 验收标准：是否明确、可量化，有无模糊描述导致扯皮；
6. 合同期限与续约：自动续约是否对甲方不利。
请用中文回答，格式为：
风险项：xxx
风险等级：低/中/高
分析：xxx
改进建议：xxx
"""),
    ("human", "合同文本如下：\n{contract_text}")
])

def analyze_risks(contract_text: str):
    llm = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base=DEEPSEEK_BASE_URL,
        temperature=0
    )
    chain = LLMChain(llm=llm, prompt=risk_prompt)
    return chain.run(contract_text=contract_text)
