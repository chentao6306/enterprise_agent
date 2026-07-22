from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Text, ForeignKey, DateTime, Table, event
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from datetime import datetime
from config import SQLITE_DB_PATH

engine = create_engine(
    f"sqlite:///{SQLITE_DB_PATH}",
    echo=False,
    connect_args={'check_same_thread': False, 'timeout': 30}
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

# ---------- 原有表 ----------
class Space(Base):
    __tablename__ = "spaces"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    space_id = Column(Integer, ForeignKey("spaces.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    files = relationship("FileRecord", secondary="file_tags", back_populates="tags")

class FileRecord(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True)
    space_id = Column(Integer, ForeignKey("spaces.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    title = Column(String, nullable=False)
    description = Column(Text)
    original_filename = Column(String, nullable=False)
    current_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    versions = relationship("FileVersion", back_populates="file", order_by="FileVersion.version_number")
    tags = relationship("Tag", secondary="file_tags", back_populates="files")

class FileVersion(Base):
    __tablename__ = "file_versions"
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)
    chunk_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.now)
    file = relationship("FileRecord", back_populates="versions")

file_tags = Table(
    "file_tags", Base.metadata,
    Column("file_id", Integer, ForeignKey("files.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True)
)

class Contract(Base):
    __tablename__ = "contracts"
    id = Column(Integer, primary_key=True, index=True)
    file_record_id = Column(Integer, ForeignKey("files.id"))
    party_a = Column(String)
    party_b = Column(String)
    contract_amount = Column(Float)
    start_date = Column(Date)
    end_date = Column(Date)
    project_name = Column(String)
    payment_terms = Column(Text)
    ip_ownership = Column(Text)
    liability_clause = Column(Text)
    full_text = Column(Text)
    risk_report = Column(Text, nullable=True)    # 新增：存储风险报告

# ---------- 新增：模拟对话历史表 ----------
class SimHistory(Base):
    __tablename__ = "sim_histories"
    id = Column(Integer, primary_key=True)
    space_id = Column(Integer, ForeignKey("spaces.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    rating = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

# 创建所有表
Base.metadata.create_all(bind=engine)
