# 项目结构 ：
enterprise_agent/
├── app.py                        # 主界面，Streamlit 应用，所有页面逻辑
├── config.py                     # 配置文件，API密钥、模型、路径等
├── requirements.txt              # Python 依赖列表
├── .gitignore                    # Git 忽略规则
├── README.md                     # 项目说明文档
│
├── knowledge/                    # 知识库管理
│   └── manager.py                # 文档上传、版本更新、删除等业务逻辑
│
├── ingest/                       # 文档加载与向量化
│   ├── document_loader.py        # 加载 PDF/Word/TXT 并分割文本块
│   └── vector_store.py           # Chroma 向量库的增删查操作
│
├── chains/                       # LangChain 链条
│   ├── qa_chain.py               # 流式问答、历史记忆、后台生成线程
│   ├── extraction_chain.py       # 合同关键信息提取
│   ├── risk_chain.py             # 合同风险审查
│   └── auto_classifier.py        # 自动分类与标签建议
│
├── db/                           # 数据库相关
│   ├── models.py                 # SQLAlchemy 模型定义（空间、类别、标签、文件、合同、模拟反馈）
│   └── repository.py             # 数据库 CRUD 操作封装
│
├── analytics/                    # 数据分析与可视化
│   └── viz.py                    # 合同统计图表、到期提醒等
│
├── utils/                        # 实用工具
│   ├── sensitive_detect.py       # 敏感信息检测（身份证、手机号等）
│   └── contract_compare.py       # 合同文本差异对比
│
├── uploaded_files/               # 用户上传的原始文件（运行时生成）
├── chat_histories/               # 对话历史 JSON 文件（运行时生成）
├── chroma_db/                    # Chroma 向量数据库持久化目录（运行时生成）
└── knowledge_base.db             # SQLite 数据库文件（运行时生成）


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