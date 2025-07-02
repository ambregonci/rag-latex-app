# Ferramentas para manipulação e melhoria de LaTeX
import os
import subprocess
import tempfile
import streamlit as st
import google.generativeai as genai
from typing import Tuple
import PyPDF2

from config import (
    logger,
    GEMINI_MODEL_NAME,
    LATEX_CONVERSION_PROMPT,
    LATEX_IMPROVEMENT_PROMPT,
    LATEX_CONCATENATE_PROMPT
)
from utils import recortar_pdf_em_blocos

class LatexTools:
    """Gerencia operações relacionadas a LaTeX."""

    def __init__(self, llm_model_name: str = GEMINI_MODEL_NAME):
        self.llm_model_name = llm_model_name

    def convert_pdf_to_latex(self, uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> str:
        """
        Converte um PDF manuscrito em código LaTeX usando o modelo Gemini.
        Divide PDFs grandes em blocos se necessário.
        """
        latex_code = ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getbuffer())
            caminho_do_pdf = tmp.name

        try:
            with open(caminho_do_pdf, "rb") as f_in:
                leitor = PyPDF2.PdfReader(f_in)
                total_paginas = len(leitor.pages)

            if total_paginas > 30:
                st.warning(f"O PDF possui {total_paginas} páginas. Ele será dividido em blocos de 30 páginas para processamento. Isso pode levar um tempo.")
                recortar_pdf_em_blocos(caminho_do_pdf, paginas_por_bloco=30, prefixo_saida=os.path.splitext(os.path.basename(caminho_do_pdf))[0] + "_parte")
                st.info("PDF recortado em blocos. Processando cada parte...")
                
                latex_final_parts = ""
                for file in sorted(os.listdir(".")): # Garante a ordem dos arquivos
                    if file.startswith(os.path.splitext(os.path.basename(caminho_do_pdf))[0] + "_parte") and file.endswith(".pdf"):
                        with st.spinner(f"Processando parte: {file}"):
                            with open(file, "rb") as f:
                                pdf_file = genai.upload_file(
                                    path=f,
                                    display_name=file,
                                    mime_type="application/pdf"
                                )
                                model = genai.GenerativeModel(model_name=self.llm_model_name)
                                response = model.generate_content([LATEX_CONVERSION_PROMPT, pdf_file])
                                latex_final_parts += f"% --- Parte: {file} ---\n" + response.text + "\n\n"
                                genai.delete_file(pdf_file.name) # Deleta o arquivo temporário do Gemini
                                os.remove(file) # Limpa o arquivo local do bloco

                with st.spinner("Concatenando e finalizando o LaTeX..."):
                    model = genai.GenerativeModel(model_name=self.llm_model_name)
                    response = model.generate_content([LATEX_CONCATENATE_PROMPT, latex_final_parts])
                    latex_code = response.text

            else:
                with st.spinner("Enviando PDF para Gemini..."):
                    pdf_file = genai.upload_file(
                        path=uploaded_file,
                        display_name=uploaded_file.name,
                        mime_type="application/pdf"
                    )
                    model = genai.GenerativeModel(model_name=self.llm_model_name)
                    response = model.generate_content([LATEX_CONVERSION_PROMPT, pdf_file])
                    latex_code = response.text
                    genai.delete_file(pdf_file.name) # Deleta o arquivo temporário do Gemini

            return latex_code

        except Exception as e:
            logger.error(f"Erro na conversão PDF para LaTeX: {e}", exc_info=True)
            st.error(f"Ocorreu um erro durante a conversão: {e}")
            return ""
        finally:
            if os.path.exists(caminho_do_pdf):
                os.remove(caminho_do_pdf) # Limpa o arquivo PDF temporário

    def improve_latex_code(self, latex_code: str) -> str:
        """Melhora um código LaTeX existente usando o modelo Gemini."""
        try:
            model = genai.GenerativeModel(model_name=self.llm_model_name)
            response = model.generate_content([LATEX_IMPROVEMENT_PROMPT, latex_code])
            return response.text
        except Exception as e:
            logger.error(f"Erro na melhoria do LaTeX: {e}", exc_info=True)
            st.error(f"Ocorreu um erro durante a melhoria: {e}")
            return ""

    def compile_latex_to_pdf(self, codigo_tex: str, nome_base_arquivo: str) -> Tuple[bool, str]:
        """
        Compila código LaTeX para PDF.
        Retorna (sucesso, caminho_do_pdf ou mensagem_de_erro).
        """
        nome_arquivo_tex = f"{nome_base_arquivo}.tex"
        with open(nome_arquivo_tex, "w", encoding="utf-8") as f:
            f.write(codigo_tex)
        
        comando = ["pdflatex", "-interaction=nonstopmode", f"-jobname={nome_base_arquivo}", nome_arquivo_tex]
        
        # Tenta compilar 2 vezes para resolver referências
        for i in range(2):
            try:
                result = subprocess.run(comando, check=True, capture_output=True, text=True, encoding='utf-8')
                logger.info(f"Compilação LaTeX (passo {i+1}) stdout:\n{result.stdout}")
                if result.stderr:
                    logger.warning(f"Compilação LaTeX (passo {i+1}) stderr:\n{result.stderr}")
            except FileNotFoundError:
                return False, "Erro Crítico: 'pdflatex' não foi encontrado. Instale uma distribuição LaTeX (ex: TeX Live, MiKTeX)."
            except subprocess.CalledProcessError as e:
                logger.error(f"Erro de compilação LaTeX:\n{e.stdout}\n{e.stderr}", exc_info=True)
                return False, f"Erro na compilação:\n{e.stdout}\n{e.stderr}"
        
        caminho_pdf = f"{nome_base_arquivo}.pdf"
        if os.path.exists(caminho_pdf):
            logger.info(f"PDF compilado com sucesso em: {caminho_pdf}")
            return True, caminho_pdf
        else:
            logger.error(f"PDF não encontrado após a compilação. Arquivos gerados: {os.listdir('.')}")
            return False, "PDF não encontrado após a compilação. Verifique os logs para mais detalhes."