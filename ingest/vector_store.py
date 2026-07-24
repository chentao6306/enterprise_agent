from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from config import EMBEDDING_MODEL_NAME, CHROMA_PERSIST_DIR
import os

def get_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

def _collection_name(space_id):
    return f"space_{space_id}"

def get_vectorstore(space_id):
    collection = _collection_name(space_id)
    embeddings = get_embeddings()
    vectordb = Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR
    )
    return vectordb

def add_documents_to_store(space_id, category_id, documents):
    # 如果文档列表为空，直接返回，避免Chroma报错
    if not documents:
        return
    for doc in documents:
        doc.metadata["category_id"] = category_id if category_id is not None else 0
    vectordb = get_vectorstore(space_id)
    vectordb.add_documents(documents)
    vectordb.persist()

def delete_from_store(space_id, source_filename):
    vectordb = get_vectorstore(space_id)
    results = vectordb.get(where={"source": source_filename})
    ids = results['ids']
    if ids:
        vectordb.delete(ids=ids)
        vectordb.persist()