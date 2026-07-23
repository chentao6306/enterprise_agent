import os
from datetime import datetime
from db.repository import (
    create_file_record, add_file_version, get_file_record, delete_file_record,
    get_categories
)
from ingest.document_loader import load_and_split_path, load_and_split_bytes
from ingest.vector_store import add_documents_to_store, delete_from_store
from chains.auto_classifier import suggest_category_and_tags
from config import UPLOAD_DIR

def upload_document(space_id, file_bytes, filename, title=None, description="", category_id=None, tags=None, auto_suggest=True):
    if tags is None:
        tags = []
    # 保存原始文件
    file_path = os.path.join(UPLOAD_DIR, f"space{space_id}_{filename}")
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # 加载文本
    chunks = load_and_split_bytes(file_bytes, filename)
    full_text = " ".join([c.page_content for c in chunks])

    # 自动推荐类别和标签
    if auto_suggest and (category_id is None or len(tags) == 0):
        cats = get_categories(space_id)
        sug_cat, sug_tags = suggest_category_and_tags(full_text, cats)
        if category_id is None and sug_cat is not None:
            category_id = sug_cat
        if sug_tags:
            tags = list(set(tags + sug_tags))

    # 清洗标签
    tags = list(set(t.strip() for t in tags if t.strip()))

    # 生成标题
    if not title:
        title = os.path.splitext(filename)[0]

    # 创建文件记录
    file_record = create_file_record(space_id, title, filename, category_id, description, tags)

    # 添加版本1
    add_file_version(file_record.id, 1, file_path, len(chunks))

    # 索引到向量库（统一集合，category_id 存入 metadata 用于过滤）
    for chunk in chunks:
        chunk.metadata["source"] = filename
        chunk.metadata["file_id"] = file_record.id
        chunk.metadata["version"] = 1
    add_documents_to_store(space_id, category_id, chunks)

    return file_record

def upload_new_version(file_id, file_bytes, filename):
    rec = get_file_record(file_id)
    if not rec:
        return None
    space_id = rec.space_id
    new_version = rec.current_version + 1
    file_path = os.path.join(UPLOAD_DIR, f"space{space_id}_{filename}_v{new_version}")
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    chunks = load_and_split_bytes(file_bytes, filename)
    add_file_version(file_id, new_version, file_path, len(chunks))

    for chunk in chunks:
        chunk.metadata["source"] = filename
        chunk.metadata["file_id"] = file_id
        chunk.metadata["version"] = new_version
    add_documents_to_store(space_id, rec.category_id, chunks)

    return rec

def delete_document(file_id):
    rec = get_file_record(file_id)
    if not rec:
        return
    # 根据 source 文件名从向量库删除
    delete_from_store(rec.space_id, rec.original_filename)
    # 删除数据库记录
    delete_file_record(file_id)