import streamlit as st
import json, os, threading
from datetime import datetime
import pandas as pd
from streamlit_autorefresh import st_autorefresh

from knowledge.manager import upload_document, upload_new_version, delete_document
from db.repository import (
    get_spaces, create_space, delete_space,
    get_categories, create_category, delete_category,
    get_files_by_space, get_file_record, get_all_tags,
    save_contract, get_all_contracts, get_contract_by_id,
    save_sim_history, search_sim_histories, get_frequent_questions,
    update_contract_risk_report
)
from chains.qa_chain import get_memory, load_history, background_generate
from chains.extraction_chain import extract_contract_info
from chains.risk_chain import analyze_risks
from chains.auto_classifier import suggest_category_and_tags
from ingest.document_loader import load_and_split_path, load_and_split_bytes
from ingest.vector_store import get_vectorstore, delete_from_store, add_documents_to_store
from analytics.viz import (
    load_contracts_df, plot_amount_distribution, plot_monthly_trend,
    plot_party_pie, get_expiring_contracts
)
from utils.sensitive_detect import detect_sensitive
from utils.contract_compare import compare_contracts
from config import REMIND_DAYS, UPLOAD_DIR

st.set_page_config(page_title="企业知识库 AI 助手", layout="wide")
st.title("📚 企业知识库智能助手")

# --- 初始化工作空间 ---
if "current_space_id" not in st.session_state:
    spaces = get_spaces()
    if spaces:
        st.session_state.current_space_id = spaces[0].id
    else:
        s = create_space("默认空间", "系统自动创建的默认工作空间")
        st.session_state.current_space_id = s.id
if "task" not in st.session_state:
    st.session_state.task = None
if "qa_memory" not in st.session_state:
    st.session_state.qa_memory = None

# --- 侧边栏：空间与类别管理 ---
st.sidebar.title("🏢 工作空间")
spaces = get_spaces()
space_names = [s.name for s in spaces]
if space_names:
    selected_space_name = st.sidebar.selectbox(
        "选择空间",
        space_names,
        index=space_names.index(
            next((s.name for s in spaces if s.id == st.session_state.current_space_id), space_names[0])
        )
    )
    selected_space = next((s for s in spaces if s.name == selected_space_name), None)
    st.session_state.current_space_id = selected_space.id
else:
    selected_space = None

with st.sidebar.expander("管理空间"):
    with st.form("new_space_form"):
        new_space_name = st.text_input("空间名称")
        new_space_desc = st.text_area("描述")
        if st.form_submit_button("创建"):
            create_space(new_space_name, new_space_desc)
            st.rerun()
    if selected_space and st.button("删除当前空间", type="secondary"):
        delete_space(selected_space.id)
        st.session_state.current_space_id = None
        st.rerun()

st.sidebar.divider()
st.sidebar.title("📂 知识类别")
if selected_space:
    categories = get_categories(selected_space.id)
    cat_names = [c.name for c in categories]
    with st.sidebar.expander("管理类别"):
        with st.form("new_cat_form"):
            new_cat_name = st.text_input("类别名称")
            new_cat_desc = st.text_input("描述")
            if st.form_submit_button("添加"):
                create_category(selected_space.id, new_cat_name, new_cat_desc)
                st.rerun()
        if categories:
            cat_to_del = st.selectbox("删除类别", cat_names)
            if st.button("删除选定类别"):
                cat_obj = next((c for c in categories if c.name == cat_to_del), None)
                if cat_obj:
                    delete_category(cat_obj.id)
                    st.rerun()

# --- 功能导航 ---
menu = st.sidebar.radio(
    "功能导航",
    ["📁 知识库", "💬 智能问答", "💬 对话模拟", "📄 合同工具", "📊 数据分析", "⚙️ 管理"]
)

# ================== 知识库页面 ==================
if menu == "📁 知识库":
    st.header("📁 知识库浏览")
    if not selected_space:
        st.warning("请先创建或选择一个工作空间")
        st.stop()

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("上传新文档")
        uploaded_file = st.file_uploader("选择文件", type=["pdf", "docx", "txt"], key="kb_upload")
        if uploaded_file:
            with st.expander("文档属性（可选）"):
                title = st.text_input("标题", value=uploaded_file.name.rsplit(".", 1)[0])
                description = st.text_area("描述")
                categories = get_categories(selected_space.id)
                cat_options = {"不指定（自动推荐）": None}
                for c in categories:
                    cat_options[c.name] = c.id
                selected_cat = st.selectbox("类别", list(cat_options.keys()))
                cat_id = cat_options[selected_cat]
                tags_str = st.text_input("标签（逗号分隔）")
                manual_tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
                auto_suggest = st.checkbox("启用AI自动推荐类别和标签", value=(cat_id is None))

            if st.button("确认上传"):
                with st.spinner("上传并分析中..."):
                    file_bytes = uploaded_file.getvalue()
                    file_record = upload_document(
                        space_id=selected_space.id,
                        file_bytes=file_bytes,
                        filename=uploaded_file.name,
                        title=title,
                        description=description,
                        category_id=cat_id,
                        tags=manual_tags,
                        auto_suggest=auto_suggest
                    )
                st.success(f"文档 '{file_record.title}' 上传成功！")
                st.rerun()

    with col2:
        st.subheader("筛选与搜索")
        categories = get_categories(selected_space.id)
        cat_filter_options = {"全部": None}
        for c in categories:
            cat_filter_options[c.name] = c.id
        selected_filter_cat = st.selectbox("按类别筛选", list(cat_filter_options.keys()))
        all_tags = get_all_tags()
        tag_filter_options = ["全部"] + [t.name for t in all_tags]
        selected_filter_tag = st.selectbox("按标签筛选", tag_filter_options)

    files = get_files_by_space(selected_space.id, category_id=cat_filter_options[selected_filter_cat])
    if selected_filter_tag != "全部":
        files = [f for f in files if hasattr(f, 'tags') and any(t.name == selected_filter_tag for t in f.tags)]

    if not files:
        st.info("当前空间暂无文档，请上传")
    else:
        cols = st.columns(3)
        for i, f in enumerate(files):
            with cols[i % 3]:
                with st.container(border=True):
                    st.write(f"**{f.title}**")
                    st.caption(f"📅 {f.created_at.strftime('%Y-%m-%d %H:%M') if f.created_at else ''}")
                    st.caption(f"📁 {f.original_filename}")
                    if f.description:
                        st.write(f.description[:100])
                    if hasattr(f, 'tags'):
                        tag_names = [t.name for t in f.tags]
                        if tag_names:
                            st.write("🏷️ " + " ".join([f"`{t}`" for t in tag_names]))
                    col_a, col_b = st.columns(2)
                    if col_a.button("查看详情", key=f"view_{f.id}"):
                        st.session_state['view_file_id'] = f.id
                        st.rerun()
                    if col_b.button("删除", key=f"del_file_{f.id}"):
                        delete_document(f.id)
                        st.rerun()
                    with st.expander("上传新版本"):
                        new_ver_file = st.file_uploader("新文件", key=f"newver_{f.id}")
                        if new_ver_file and st.button("确认更新", key=f"update_{f.id}"):
                            upload_new_version(f.id, new_ver_file.getvalue(), new_ver_file.name)
                            st.success("版本已更新")
                            st.rerun()

    if 'view_file_id' in st.session_state and st.session_state['view_file_id']:
        file_rec = get_file_record(st.session_state['view_file_id'])
        if file_rec:
            with st.expander(f"📄 {file_rec.title} 详情", expanded=True):
                st.write(f"描述: {file_rec.description}")
                st.write(f"当前版本: {file_rec.current_version}")
                if hasattr(file_rec, 'versions'):
                    for v in file_rec.versions:
                        st.write(f"版本 {v.version_number} - 上传于 {v.uploaded_at}")
                if st.button("关闭详情"):
                    del st.session_state['view_file_id']
                    st.rerun()

# ================== 智能问答 ==================
elif menu == "💬 智能问答":
    st.header("💬 知识问答")
    if not selected_space:
        st.warning("请先选择一个工作空间")
        st.stop()

    if st.session_state.qa_memory is None or st.session_state.get('qa_space_id') != selected_space.id:
        st.session_state.qa_memory = get_memory(selected_space.id)
        st.session_state.qa_space_id = selected_space.id
    mem = st.session_state.qa_memory

    categories = get_categories(selected_space.id)
    cat_choice = {"全部知识库": None}
    for c in categories:
        cat_choice[c.name] = c.id
    selected_cat = st.selectbox("限定搜索范围", list(cat_choice.keys()))
    cat_id = cat_choice[selected_cat]

    history = load_history(selected_space.id)
    for msg in history:
        if msg.type == "human":
            st.chat_message("user").write(msg.content)
        elif msg.type == "ai":
            st.chat_message("assistant").write(msg.content)

    task = st.session_state.task
    if task is not None:
        if not task["state"]["done"]:
            with st.chat_message("assistant"):
                placeholder = st.empty()
                st_autorefresh(interval=1000, limit=None, key="qa_auto")
                placeholder.markdown(task["state"]["tokens"] + "▌")
        else:
            st.session_state.task = None
            st.rerun()
    else:
        user_question = st.chat_input("请输入你的问题")
        if user_question:
            mem.chat_memory.add_user_message(user_question)
            state = {"tokens": "", "done": False}
            thread = threading.Thread(
                target=background_generate,
                args=(user_question, selected_space.id, cat_id, mem, state)
            )
            thread.start()
            st.session_state.task = {
                "question": user_question,
                "state": state,
                "thread": thread
            }
            st.rerun()

    if st.button("清空对话历史"):
        mem.clear()
        st.session_state.task = None
        st.rerun()

# ================== 对话模拟 ==================
elif menu == "💬 对话模拟":
    st.header("💬 用户对话模拟")
    if not selected_space:
        st.warning("请先选择一个工作空间")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["📞 模拟对话", "🔍 历史搜索", "📊 高频问题"])

    with tab1:
        st.subheader("输入客户问题，生成真人化回答")

        if "sim_memory" not in st.session_state:
            from langchain.memory import ConversationBufferMemory
            st.session_state.sim_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        sim_mem = st.session_state.sim_memory

        categories = get_categories(selected_space.id)
        cat_choice = {"全部知识库": None}
        for c in categories:
            cat_choice[c.name] = c.id
        selected_cat_name = st.selectbox("限定产品范围", list(cat_choice.keys()), key="sim_cat")
        cat_id = cat_choice[selected_cat_name]

        with st.form("sim_form", clear_on_submit=True):
            customer_question = st.text_area("客户问题", height=100, key="sim_input")
            submitted = st.form_submit_button("生成回答")

        if submitted and customer_question:
            with st.spinner("正在生成回答..."):
                from langchain.chat_models import ChatOpenAI
                from langchain.prompts import ChatPromptTemplate
                from config import LLM_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

                vectordb = get_vectorstore(selected_space.id, cat_id)
                retriever = vectordb.as_retriever(search_kwargs={"k": 4})
                docs = retriever.get_relevant_documents(customer_question)
                context = "\n\n".join([d.page_content for d in docs])

                prompt = ChatPromptTemplate.from_messages([
                    ("system", """你是一位经验丰富、富有同理心的资深产品顾问，根据公司产品知识库，以真实人类的沟通方式回答客户问题。
**核心要求：**
1. **情绪共鸣**：先理解客户情绪，用温暖、真诚的语言回应。
2. **思维过程展现**：像人一样“想一想再说”，例如“让我帮您梳理一下...”。
3. **口语化但不失专业**：用词自然，像朋友聊天。
4. **结构化回答**：用“首先...其次...最后”等口语化结构。
5. **主动提供额外价值**：补充小建议或常见误区。
6. **诚实与边界**：不知则说明，建议联系人工。

背景知识库：
{context}

对话历史（注意保持连贯）："""),
                    *sim_mem.chat_memory.messages,
                    ("human", "{question}")
                ])

                llm = ChatOpenAI(model=LLM_MODEL, openai_api_key=DEEPSEEK_API_KEY, openai_api_base=DEEPSEEK_BASE_URL, temperature=0.3)
                response = llm(prompt.format_prompt(context=context, question=customer_question).to_messages())
                answer = response.content

                sim_mem.chat_memory.add_user_message(customer_question)
                sim_mem.chat_memory.add_ai_message(answer)

                save_sim_history(selected_space.id, customer_question, answer)

                st.session_state['last_sim_answer'] = answer
                st.session_state['last_sim_question'] = customer_question

        if 'last_sim_answer' in st.session_state and 'last_sim_question' in st.session_state:
            st.subheader("AI 生成回答")
            st.write(st.session_state['last_sim_answer'])

            col_rate1, col_rate2 = st.columns([1, 1])
            with col_rate1:
                if st.button("👍 满意", key="satisfied"):
                    from db.models import SessionLocal, SimHistory
                    with SessionLocal() as db:
                        last_record = db.query(SimHistory).filter(
                            SimHistory.space_id == selected_space.id,
                            SimHistory.rating == None
                        ).order_by(SimHistory.created_at.desc()).first()
                        if last_record:
                            last_record.rating = "satisfied"
                            db.commit()
                    st.success("感谢反馈！已记录为满意。")
                    del st.session_state['last_sim_answer']
                    del st.session_state['last_sim_question']
                    st.rerun()
            with col_rate2:
                if st.button("👎 不满意", key="unsatisfied"):
                    from db.models import SessionLocal, SimHistory
                    with SessionLocal() as db:
                        last_record = db.query(SimHistory).filter(
                            SimHistory.space_id == selected_space.id,
                            SimHistory.rating == None
                        ).order_by(SimHistory.created_at.desc()).first()
                        if last_record:
                            last_record.rating = "unsatisfied"
                            db.commit()
                    st.success("感谢反馈！已记录为不满意，我们将优化知识库。")
                    del st.session_state['last_sim_answer']
                    del st.session_state['last_sim_question']
                    st.rerun()

        if st.button("清空对话历史"):
            sim_mem.clear()
            st.session_state.pop('last_sim_answer', None)
            st.session_state.pop('last_sim_question', None)
            st.rerun()

    with tab2:
        st.subheader("🔍 搜索历史相似问题")
        search_query = st.text_input("输入关键词或问题片段")
        if search_query:
            results = search_sim_histories(selected_space.id, search_query, limit=10)
            if results:
                for r in results:
                    with st.expander(f"问：{r.question[:80]}..."):
                        st.write(f"**完整问题：** {r.question}")
                        st.write(f"**回答：** {r.answer}")
                        st.caption(f"时间：{r.created_at}  |  评价：{r.rating or '暂无'}")
                        st.code(r.answer, language="")
            else:
                st.info("没有找到匹配的历史记录。")

    with tab3:
        st.subheader("📊 高频客户问题统计")
        top_n = st.slider("显示前 N 个问题", 5, 20, 10)
        freq_data = get_frequent_questions(selected_space.id, top_n=top_n)
        if freq_data:
            df = pd.DataFrame(freq_data, columns=["问题", "出现次数"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暂无模拟对话记录。")

# ================== 合同工具 ==================
elif menu == "📄 合同工具":
    st.header("📄 合同工具")
    if not selected_space:
        st.warning("请先选择一个工作空间")
        st.stop()

    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["合同解析", "风险审查", "合同对比"])
    with sub_tab1:
        st.subheader("从知识库文件解析合同")
        files = get_files_by_space(selected_space.id)
        file_options = [f"{f.id}: {f.title}" for f in files]
        if not file_options:
            st.info("请先在知识库上传合同文件")
        else:
            selected_file_str = st.selectbox("选择文件", file_options)
            file_id = int(selected_file_str.split(":")[0])
            file_rec = get_file_record(file_id)
            if file_rec and st.button("解析合同关键信息"):
                with st.spinner("解析中..."):
                    if hasattr(file_rec, 'versions') and file_rec.versions:
                        latest_ver = max(file_rec.versions, key=lambda v: v.version_number)
                        chunks = load_and_split_path(latest_ver.file_path)
                        full_text = "\n".join([c.page_content for c in chunks])
                        info = extract_contract_info(full_text)
                        if info:
                            st.session_state['contract_info'] = info
                            st.session_state['contract_file_id'] = file_id
                            st.session_state['contract_full_text'] = full_text
                            st.rerun()
                        else:
                            st.error("未能提取到合同信息")

        if 'contract_info' in st.session_state:
            info = st.session_state['contract_info']
            st.subheader("提取结果（可编辑）")
            col1, col2 = st.columns(2)
            with col1:
                party_a = st.text_input("甲方", value=info.party_a or "")
                party_b = st.text_input("乙方", value=info.party_b or "")
                amount = st.text_input("合同金额", value=str(info.contract_amount) if info.contract_amount else "")
                start_date = st.text_input("开始日期", value=info.start_date or "")
                end_date = st.text_input("结束日期", value=info.end_date or "")
            with col2:
                project = st.text_input("项目名称", value=info.project_name or "")
                payment = st.text_area("付款条件", value=info.payment_terms or "", height=100)
                ip = st.text_area("知识产权", value=info.ip_ownership or "", height=100)
                liability = st.text_area("违约责任", value=info.liability_clause or "", height=100)

            if st.button("保存合同到数据库"):
                def to_date(d):
                    if d:
                        try:
                            return datetime.strptime(d, "%Y-%m-%d").date()
                        except:
                            return None
                    return None

                contract_data = {
                    "file_record_id": st.session_state['contract_file_id'],
                    "party_a": party_a,
                    "party_b": party_b,
                    "contract_amount": float(amount) if amount else None,
                    "start_date": to_date(start_date),
                    "end_date": to_date(end_date),
                    "project_name": project,
                    "payment_terms": payment,
                    "ip_ownership": ip,
                    "liability_clause": liability,
                    "full_text": st.session_state['contract_full_text']
                }
                contract = save_contract(contract_data)
                st.success(f"合同已保存，ID: {contract.id}")
                del st.session_state['contract_info']
                del st.session_state['contract_file_id']
                del st.session_state['contract_full_text']
                st.rerun()

    # ===== 风险审查（修改后） =====
    with sub_tab2:
        st.subheader("合同风险审查")
        contracts = get_all_contracts()
        if not contracts:
            st.info("暂无已解析的合同，请先解析合同")
        else:
            contract_options = [f"{c.id}: {c.project_name or '未命名'} ({c.party_a} vs {c.party_b})" for c in contracts]
            selected_contract_str = st.selectbox("选择已保存的合同", contract_options)
            contract_id = int(selected_contract_str.split(":")[0])
            contract = get_contract_by_id(contract_id)

            if contract.risk_report:
                st.info("已存在风险报告：")
                st.text_area("历史风险报告", contract.risk_report, height=300)
                if st.button("重新生成风险报告"):
                    with st.spinner("分析中..."):
                        report = analyze_risks(contract.full_text)
                    st.text_area("新风险报告", report, height=400)
                    update_contract_risk_report(contract_id, report)
                    st.success("风险报告已更新！")
                    st.rerun()
            else:
                if st.button("生成风险报告"):
                    if contract and contract.full_text:
                        with st.spinner("分析中..."):
                            report = analyze_risks(contract.full_text)
                        st.text_area("风险报告", report, height=400)
                        update_contract_risk_report(contract_id, report)
                        st.success("风险报告已保存！")
                        st.rerun()
                    else:
                        st.error("合同全文缺失")

    with sub_tab3:
        st.subheader("合同条款差异对比")
        col_a, col_b = st.columns(2)
        with col_a:
            file1 = st.file_uploader("上传合同 A", type=["pdf", "docx", "txt"], key="cmp1")
        with col_b:
            file2 = st.file_uploader("上传合同 B", type=["pdf", "docx", "txt"], key="cmp2")
        if file1 and file2:
            chunks1 = load_and_split_bytes(file1.read(), file1.name)
            text1 = "\n".join([c.page_content for c in chunks1])
            chunks2 = load_and_split_bytes(file2.read(), file2.name)
            text2 = "\n".join([c.page_content for c in chunks2])
            diff = compare_contracts(text1, text2)
            st.text_area("差异报告", diff, height=400)

# ================== 数据分析 ==================
elif menu == "📊 数据分析":
    st.header("📊 合同数据分析")
    df = load_contracts_df()
    if df.empty:
        st.warning("暂无合同数据")
    else:
        col1, col2 = st.columns(2)
        with col1:
            fig1 = plot_amount_distribution(df)
            if fig1: st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = plot_monthly_trend(df)
            if fig2: st.plotly_chart(fig2, use_container_width=True)
        st.plotly_chart(plot_party_pie(df), use_container_width=True)
        st.subheader("合同明细")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("导出CSV", csv, "contracts.csv", "text/csv")

# ================== 管理工具 ==================
elif menu == "⚙️ 管理":
    st.header("⚙️ 管理工具")
    sub_a, sub_b, sub_c = st.tabs(["到期提醒", "敏感检测", "全局标签"])

    with sub_a:
        st.subheader(f"合同到期提醒（未来 {REMIND_DAYS} 天内）")
        df = load_contracts_df()
        if df.empty:
            st.info("无合同数据")
        else:
            expiring = get_expiring_contracts(df)
            if expiring:
                st.warning(f"有 {len(expiring)} 份合同即将到期！")
                st.table(expiring)
            else:
                st.success("没有即将到期的合同。")

    with sub_b:
        st.subheader("文档敏感信息检测")
        files = get_files_by_space(selected_space.id) if selected_space else []
        if not files:
            st.info("请先在工作空间上传文件")
        else:
            mode = st.radio("检测范围", ["选择文件", "全库扫描"])
            if mode == "选择文件":
                selected_file = st.selectbox("选择文件", [f"{f.id}: {f.title}" for f in files])
                file_id = int(selected_file.split(":")[0])
                if st.button("开始检测"):
                    file_rec = get_file_record(file_id)
                    if file_rec and hasattr(file_rec, 'versions') and file_rec.versions:
                        latest = max(file_rec.versions, key=lambda v: v.version_number)
                        chunks = load_and_split_path(latest.file_path)
                        text = "\n".join([c.page_content for c in chunks])
                        findings = detect_sensitive(text)
                        if findings:
                            st.error("发现潜在敏感信息")
                            st.table(findings)
                        else:
                            st.success("未发现常见敏感信息。")
            else:
                if st.button("扫描所有合同"):
                    all_findings = []
                    contracts = get_all_contracts()
                    for c in contracts:
                        if c.full_text:
                            found = detect_sensitive(c.full_text)
                            for f in found:
                                f["合同ID"] = c.id
                                f["文件名"] = c.project_name or ""
                            all_findings.extend(found)
                    if all_findings:
                        st.error(f"在 {len(contracts)} 份合同中发现敏感信息")
                        st.dataframe(pd.DataFrame(all_findings))
                    else:
                        st.success("所有合同均未发现常见敏感信息。")

    with sub_c:
        st.subheader("全局标签管理")
        all_tags = get_all_tags()
        if all_tags:
            for t in all_tags:
                st.write(f"🏷️ {t.name}")
        else:
            st.info("暂无标签")

st.sidebar.markdown("---")
st.sidebar.info("💡 在「管理空间」中创建不同工作空间，隔离企业知识库。")
