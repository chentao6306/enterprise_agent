from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from config import EMBEDDING_MODEL_NAME, CHROMA_PERSIST_DIR
import os

def get_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

def _collection_name(space_id, category_id=None):
    """为每个空间-类别生成独立的集合名称"""
    base = f"space_{space_id}"
    if category_id:
        base += f"_cat_{category_id}"
    return base

def get_vectorstore(space_id, category_id=None):
    collection = _collection_name(space_id, category_id)
    embeddings = get_embeddings()
    vectordb = Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR
    )
    return vectordb

def add_documents_to_store(space_id, category_id, documents):
    vectordb = get_vectorstore(space_id, category_id)
    vectordb.add_documents(documents)
    vectordb.persist()

def delete_from_store(space_id, category_id, source_filename):
    vectordb = get_vectorstore(space_id, category_id)
    results = vectordb.get(where={"source": source_filename})
    ids = results['ids']
    if ids:
        vectordb.delete(ids=ids)
        vectordb.persist()