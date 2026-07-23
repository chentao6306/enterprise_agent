from db.models import SessionLocal, Space, Category, Tag, FileRecord, FileVersion, Contract, file_tags, SimHistory
from datetime import datetime
import time
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import OperationalError
from sqlalchemy import text, func

def retry_on_lock(func):
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                else:
                    raise
    return wrapper

# --- 空间管理 ---
@retry_on_lock
def create_space(name, description=""):
    with SessionLocal() as db:
        space = Space(name=name, description=description)
        db.add(space)
        db.commit()
        db.refresh(space)
        return space

@retry_on_lock
def get_spaces():
    with SessionLocal() as db:
        return db.query(Space).all()

@retry_on_lock
def delete_space(space_id):
    with SessionLocal() as db:
        db.query(Space).filter(Space.id == space_id).delete()
        db.commit()

# --- 类别管理 ---
@retry_on_lock
def create_category(space_id, name, description=""):
    with SessionLocal() as db:
        cat = Category(space_id=space_id, name=name, description=description)
        db.add(cat)
        db.commit()
        db.refresh(cat)
        return cat

@retry_on_lock
def get_categories(space_id):
    with SessionLocal() as db:
        return db.query(Category).filter(Category.space_id == space_id).all()

@retry_on_lock
def delete_category(cat_id):
    with SessionLocal() as db:
        db.query(Category).filter(Category.id == cat_id).delete()
        db.commit()

# --- 标签管理 ---
@retry_on_lock
def get_or_create_tag(name):
    with SessionLocal() as db:
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.commit()
            db.refresh(tag)
        return tag

@retry_on_lock
def get_all_tags():
    with SessionLocal() as db:
        return db.query(Tag).all()

@retry_on_lock
def get_tags_by_space(space_id):
    """获取指定空间下所有文件关联的标签名称列表"""
    with SessionLocal() as db:
        files = db.query(FileRecord).options(joinedload(FileRecord.tags)).filter(FileRecord.space_id == space_id).all()
        tags = set()
        for f in files:
            for t in f.tags:
                tags.add(t.name)
        return sorted(list(tags))

# --- 文件记录 ---
@retry_on_lock
def create_file_record(space_id, title, filename, category_id=None, description="", tags=[]):
    with SessionLocal() as db:
        cleaned_tags = list(set(t.strip() for t in tags if t.strip()))
        file_rec = FileRecord(
            space_id=space_id, category_id=category_id, title=title,
            description=description, original_filename=filename
        )
        db.add(file_rec)
        db.flush()
        for tag_name in cleaned_tags:
            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.add(tag)
                db.flush()
            db.execute(
                text("INSERT OR IGNORE INTO file_tags (file_id, tag_id) VALUES (:file_id, :tag_id)"),
                {"file_id": file_rec.id, "tag_id": tag.id}
            )
        db.commit()
        db.refresh(file_rec)
        return file_rec

@retry_on_lock
def add_file_version(file_id, version_number, file_path, chunk_count=0):
    with SessionLocal() as db:
        fv = FileVersion(file_id=file_id, version_number=version_number, file_path=file_path, chunk_count=chunk_count)
        db.add(fv)
        file_rec = db.query(FileRecord).get(file_id)
        file_rec.current_version = version_number
        db.commit()
        return fv

@retry_on_lock
def get_files_by_space(space_id, category_id=None):
    with SessionLocal() as db:
        query = db.query(FileRecord).options(joinedload(FileRecord.tags)).filter(FileRecord.space_id == space_id)
        if category_id:
            query = query.filter(FileRecord.category_id == category_id)
        return query.all()

@retry_on_lock
def get_file_record(file_id):
    with SessionLocal() as db:
        return db.query(FileRecord).options(joinedload(FileRecord.tags), joinedload(FileRecord.versions)).get(file_id)

@retry_on_lock
def delete_file_record(file_id):
    with SessionLocal() as db:
        db.query(FileRecord).filter(FileRecord.id == file_id).delete()
        db.commit()

# --- 合同操作 ---
@retry_on_lock
def save_contract(contract_data):
    with SessionLocal() as db:
        contract = Contract(**contract_data)
        db.add(contract)
        db.commit()
        db.refresh(contract)
        return contract

@retry_on_lock
def update_contract_risk_report(contract_id, report):
    with SessionLocal() as db:
        contract = db.query(Contract).get(contract_id)
        if contract:
            contract.risk_report = report
            db.commit()
            return True
        return False

@retry_on_lock
def get_all_contracts():
    with SessionLocal() as db:
        return db.query(Contract).all()

@retry_on_lock
def get_contract_by_id(contract_id):
    with SessionLocal() as db:
        return db.query(Contract).get(contract_id)

# --- 模拟对话历史 ---
@retry_on_lock
def save_sim_history(space_id, question, answer, rating=None):
    with SessionLocal() as db:
        record = SimHistory(space_id=space_id, question=question, answer=answer, rating=rating)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

@retry_on_lock
def search_sim_histories(space_id, query_text, limit=5):
    with SessionLocal() as db:
        results = db.query(SimHistory).filter(
            SimHistory.space_id == space_id,
            SimHistory.question.contains(query_text) | SimHistory.answer.contains(query_text)
        ).order_by(SimHistory.created_at.desc()).limit(limit).all()
        return results

@retry_on_lock
def get_frequent_questions(space_id, top_n=10):
    with SessionLocal() as db:
        freq = db.query(SimHistory.question, func.count(SimHistory.id).label('count')).filter(
            SimHistory.space_id == space_id
        ).group_by(SimHistory.question).order_by(func.count(SimHistory.id).desc()).limit(top_n).all()
        return freq