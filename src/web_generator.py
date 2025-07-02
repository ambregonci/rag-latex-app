# Geração de páginas web interativas a partir de LaTeX
import streamlit as st
import google.generativeai as genai

from config import logger, GEMINI_MODEL_NAME, LATEX_INSIGHTS_PROMPT

class WebGenerator:
    """Classe para gerar páginas web interativas a partir de LaTeX."""

    def __init__(self, llm_model_name: str = GEMINI_MODEL_NAME):
        self.llm_model_name = llm_model_name

    def generate_interactive_page(self, latex_input: str) -> str:
        """Gera uma página HTML interativa a partir do código LaTeX."""
        try:
            model = genai.GenerativeModel(model_name=self.llm_model_name)
            response = model.generate_content([LATEX_INSIGHTS_PROMPT, latex_input])
            return response.text
        except Exception as e:
            logger.error(f"Erro ao gerar página web interativa: {e}", exc_info=True)
            st.error(f"Ocorreu um erro ao gerar a página interativa: {e}")
            return ""