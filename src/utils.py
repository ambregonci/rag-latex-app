import os
import tempfile
import logging
import PyPDF2
import pdfplumber
from typing import List, Any
import base64

from config import logger

def extract_all_pages_as_images(file_uploads: List[Any]) -> List[Any]:
    """Extrai todas as páginas dos PDFs enviados como imagens para exibição."""
    logger.info(f"Extraindo páginas como imagens de {len(file_uploads)} arquivos.")
    pdf_pages = []
    for file_upload in file_uploads:
        # O file_uploader reseta a posição do ponteiro, então é preciso resetá-lo
        file_upload.seek(0)
        with pdfplumber.open(file_upload) as pdf:
            pdf_pages.extend([page.to_image(resolution=1080).original for page in pdf.pages])
    logger.info("Extração de imagens concluída.")
    return pdf_pages

def extract_pages_as_images_from_path(pdf_path: str) -> List[Any]:
    """Extrai todas as páginas de um PDF em um caminho local como imagens."""
    if not os.path.exists(pdf_path):
        logger.error(f"Arquivo PDF não encontrado em: {pdf_path}")
        return []
    
    logger.info(f"Extraindo páginas como imagens de {pdf_path}")
    pdf_pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Usamos uma resolução um pouco menor para a visualização dinâmica
            # para que a renderização seja mais rápida.
            pdf_pages.extend([page.to_image(resolution=1080).original for page in pdf.pages])
        logger.info("Extração de imagens do PDF compilado concluída.")
    except Exception as e:
        logger.error(f"Erro ao abrir PDF compilado com pdfplumber: {e}")

    return pdf_pages

def recortar_pdf_em_blocos(arquivo_entrada, paginas_por_bloco=30, prefixo_saida="recorte"):
    """
    Divide um PDF em vários arquivos, cada um com até 'paginas_por_bloco' páginas.
    :param arquivo_entrada: Caminho do PDF original.
    :param paginas_por_bloco: Número de páginas por recorte.
    :param prefixo_saida: Prefixo para os arquivos de saída.
    """
    with open(arquivo_entrada, "rb") as f_in:
        leitor = PyPDF2.PdfReader(f_in)
        total_paginas = len(leitor.pages)
        for inicio in range(0, total_paginas, paginas_por_bloco):
            escritor = PyPDF2.PdfWriter()
            fim = min(inicio + paginas_por_bloco, total_paginas)
            for i in range(inicio, fim):
                escritor.add_page(leitor.pages[i])
            nome_saida = f"{prefixo_saida}_pags_{inicio+1}_a_{fim}.pdf"
            with open(nome_saida, "wb") as f_out:
                escritor.write(f_out)
            logger.info(f"Criado arquivo de bloco PDF: {nome_saida}")

def get_base64_download_link(data: str, filename: str, text: str):
    """Gera um link de download base64 para um arquivo."""
    b64 = base64.b64encode(data.encode()).decode()
    href = f'<a href="data:file/html;base64,{b64}" download="{filename}" style="text-decoration: none; color: white; background-color: #16a34a; padding: 10px 20px; border-radius: 8px; font-weight: bold;">{text}</a>'
    return href