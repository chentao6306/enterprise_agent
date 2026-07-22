import os
import tempfile
from langchain.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

def _load_from_path(path, filename):
    suffix = os.path.splitext(filename)[1]
    if suffix == '.pdf':
        loader = PyPDFLoader(path)
    elif suffix in ['.docx', '.doc']:
        loader = Docx2txtLoader(path)
    elif suffix == '.txt':
        loader = TextLoader(path, encoding='utf-8')
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")

    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""]
    )
    return text_splitter.split_documents(documents)

def load_and_split_bytes(file_bytes, filename):
    """从 bytes 加载文档（用于 Streamlit 直接上传）"""
    suffix = os.path.splitext(filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    chunks = _load_from_path(tmp_path, filename)
    os.unlink(tmp_path)
    return chunks

def load_and_split_path(file_path):
    """从文件路径加载文档（用于已保存文件）"""
    filename = os.path.basename(file_path)
    return _load_from_path(file_path, filename)
