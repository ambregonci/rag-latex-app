# Núcleo de lógica RAG para PDFs
import os
import tempfile
import logging
from typing import List, Optional
import streamlit as st

from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_core.runnables import RunnablePassthrough
import google.generativeai as genai

from config import (
    logger,
    PERSIST_DIRECTORY,
    GEMINI_MODEL_NAME,
    EMBEDDING_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    RAG_QUERY_PROMPT_TEMPLATE,
    RAG_ANSWER_PROMPT_TEMPLATE
)

class RAGCore:
    """Encapsula a lógica de RAG (Retrieval Augmented Generation)."""

    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm

    def create_vector_db_from_files(self, file_uploads: List[st.runtime.uploaded_file_manager.UploadedFile]) -> Optional[Chroma]:
        """Cria ou carrega um banco de dados vetorial a partir dos arquivos PDF enviados."""
        logger.info("Iniciando a criação do banco de dados vetorial.")
        all_docs = []
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                for file_upload in file_uploads:
                    temp_path = os.path.join(temp_dir, file_upload.name)
                    with open(temp_path, "wb") as f:
                        f.write(file_upload.read())
                    loader = PyPDFLoader(temp_path)
                    all_docs.extend(loader.load())

                text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
                chunks = text_splitter.split_documents(all_docs)

                if not chunks:
                    st.warning("Nenhum texto pôde ser extraído dos PDFs. Verifique os arquivos.")
                    return None

                embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
                
                # Criar um nome de coleção único baseado nos nomes e tamanhos dos arquivos
                collection_name = f"pdfs_{hash(tuple((f.name, f.size) for f in file_uploads))}"

                vector_db = Chroma.from_documents(
                    documents=chunks,
                    embedding=embeddings,
                    persist_directory=PERSIST_DIRECTORY,
                    collection_name=collection_name
                )
                logger.info("Banco de dados vetorial criado com sucesso.")
                return vector_db
        except Exception as e:
            st.error(f"Erro ao criar o banco de dados vetorial: {e}")
            logger.error(f"Falha na criação do Vector DB: {e}", exc_info=True)
            return None

    def process_question(self, question: str) -> str:
        """Processa uma pergunta usando a cadeia RAG."""
        if st.session_state.vector_db is None:
            return "O sistema não está pronto. Por favor, faça o upload de PDFs e verifique a API Key."
        
        logger.info(f"Processando pergunta: {question}")
        
        query_prompt = PromptTemplate(input_variables=["question"], template=RAG_QUERY_PROMPT_TEMPLATE)
        
        retriever = MultiQueryRetriever.from_llm(
            st.session_state.vector_db.as_retriever(), self.llm, prompt=query_prompt
        )
        
        answer_prompt = ChatPromptTemplate.from_template(RAG_ANSWER_PROMPT_TEMPLATE)
        
        chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | answer_prompt
            | self.llm
            | StrOutputParser()
        )
        
        response = chain.invoke(question)
        logger.info("Resposta gerada pela cadeia RAG.")
        return response