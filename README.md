📚 企业知识库 AI 助手
基于 LangChain + Streamlit 构建的企业级知识库智能助手，支持多工作空间隔离、文档管理、RAG 智能问答、对话模拟、合同解析与风险审查、数据分析等功能，帮助团队高效沉淀与利用知识资产。

🚀 主要功能
多工作空间：创建独立空间隔离不同部门或客户的知识库。
动态类别与标签：自定义知识分类，支持 AI 自动推荐。
文档管理：上传 PDF/Word/TXT，自动向量化，支持版本更新与删除。
智能问答：基于知识库的 RAG 对话，流式输出，对话历史持久化。
对话模拟：为销售人员提供产品顾问式的回答生成，支持历史检索、满意度评价和高频问题统计。
合同工具：合同关键信息提取、风险审查（报告自动保存）、文本差异对比。
数据分析：合同金额分布、月度趋势、合作方占比等可视化图表。
管理工具：合同到期提醒、敏感信息检测（身份证/手机号/银行卡等）、全局标签管理。
🛠️ 技术栈
界面：Streamlit
模型服务：DeepSeek (通过 OpenAI 兼容接口)
编排框架：LangChain
嵌入模型：sentence-transformers (all-MiniLM-L6-v2)
向量库：ChromaDB
数据库：SQLite (SQLAlchemy ORM)
文档解析：PyPDF, python-docx, docx2txt
可视化：Plotly, pandas
📦 安装与运行
1. 克隆项目
git clone https://github.com/chentao6306/enterprise_agent.git
cd enterprise_agent

2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

3. 安装依赖
pip install -r requirements.txt

4. 配置你的 API Key
编辑 config.py，将 DEEPSEEK_API_KEY 替换为自己的 DeepSeek API Key：
DEEPSEEK_API_KEY = "your-api-key"

5. 启动应用
streamlit run app.py
浏览器访问 http://localhost:8501 即可使用。


📖 使用指南
首次使用：侧边栏点击“管理空间”创建一个工作空间，然后“添加类别”以组织知识。

上传知识：在“知识库”页面上传产品手册、规章制度、合同等文档，支持自动类别推荐。

内部问答：进入“智能问答”，选择限定范围后提问，AI 将根据已索引的文档回答。

对外模拟：在“对话模拟”中输入客户问题，获得真人化回答，并可搜索历史或查看高频问题。

合同处理：在“合同工具”中解析合同字段、生成风险报告，报告会自动保存避免重复生成。

管理监控：“数据分析”提供合同统计图表，“管理”中可设置到期提醒、敏感检测等。


📁 项目结构
enterprise_agent/
├── app.py                  # 主界面
├── config.py               # 配置文件
├── requirements.txt        # Python 依赖
├── db/                     # 数据库模型与操作
│   ├── models.py
│   └── repository.py
├── ingest/                 # 文档加载与向量化
│   ├── document_loader.py
│   └── vector_store.py
├── chains/                 # LangChain 链条
│   ├── qa_chain.py
│   ├── extraction_chain.py
│   ├── risk_chain.py
│   └── auto_classifier.py
├── knowledge/              # 知识库管理逻辑
│   └── manager.py
├── analytics/              # 数据分析与可视化
│   └── viz.py
├── utils/                  # 工具函数
│   ├── sensitive_detect.py
│   └── contract_compare.py
├── uploaded_files/         # 用户上传文件目录
├── chat_histories/         # 对话历史存储
├── chroma_db/              # Chroma 向量库
└── knowledge_base.db       # SQLite 数据库（运行时生成）


# 项目版本：
(venv_new) (base) PS C:\Users\27757\PycharmProjects\enterprise_agent> python --version
Python 3.10.11


启动命令：
# 1. 进入项目目录（如果已在则跳过）
cd C:\Users\27757\PycharmProjects\enterprise_agent

# 2. 激活虚拟环境
.\venv_new\Scripts\Activate.ps1

# 3. 启动应用
streamlit run app.py