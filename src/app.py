# Arquivo principal da aplicação Streamlit
import streamlit as st
import os
import warnings
import uuid
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from streamlit_ace import st_ace

from config import logger, GEMINI_MODEL_NAME
from utils import extract_all_pages_as_images, extract_pages_as_images_from_path, get_base64_download_link
from rag_core import RAGCore
from latex_tools import LatexTools
from web_generator import WebGenerator

# --- CONFIGURAÇÕES GLOBAIS E INICIALIZAÇÃO ---
warnings.filterwarnings('ignore', category=UserWarning, message='.*torch.classes.*')
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

st.set_page_config(
    page_title="Assistente de PDFs com Gemini",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

class PDFChatApp:
    """Classe principal para a aplicação Streamlit."""

    def __init__(self):
        """Inicializa a aplicação, o estado e os modelos."""
        self.llm = None
        self.rag_core = None
        self.latex_tools = None
        self.web_generator = None
        self.initialize_session_state()

    def initialize_session_state(self):
        """Define os valores padrão para o estado da sessão."""
        if "vector_db" not in st.session_state:
            st.session_state.vector_db = None
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "pdf_pages" not in st.session_state:
            st.session_state.pdf_pages = None
        if "file_uploads" not in st.session_state:
            st.session_state.file_uploads = []
        if "compiled_pdf_images" not in st.session_state:
            st.session_state.compiled_pdf_images = None
        if "compilation_success" not in st.session_state:
            st.session_state.compilation_success = None
        if "compilation_result" not in st.session_state:
            st.session_state.compilation_result = None
        if "code_to_compile" not in st.session_state:
            st.session_state.code_to_compile = ""
        if "compiled_pdf_path" not in st.session_state:
            st.session_state.compiled_pdf_path = None


    def setup_api_key_and_llm(self):
        """Configura a chave de API do Google e inicializa o LLM e as ferramentas."""
        try:
            google_api_key = st.secrets.get("GOOGLE_API_KEY")
            if not google_api_key:
                st.sidebar.warning("🔑 Insira sua Google API Key para continuar.")
                google_api_key = st.sidebar.text_input(
                    "Google API Key", type="password", label_visibility="collapsed"
                )

            if google_api_key:
                genai.configure(api_key=google_api_key)
                self.llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL_NAME, temperature=0.3)
                self.rag_core = RAGCore(self.llm)
                self.latex_tools = LatexTools(GEMINI_MODEL_NAME)
                self.web_generator = WebGenerator(GEMINI_MODEL_NAME)
                return True
            return False
        except Exception as e:
            st.sidebar.error(f"Erro ao configurar a API: {e}")
            logger.error(f"Erro de configuração da API: {e}")
            return False

    def _render_rag_tab(self):
        """Renderiza a interface da aba de Chat RAG."""
        st.sidebar.header("Gerenciar PDFs para Chat")
        file_uploads = st.sidebar.file_uploader(
            "Faça upload de um ou mais arquivos PDF",
            type="pdf",
            accept_multiple_files=True,
            key="pdf_uploader"
        )

        if st.sidebar.button("Processar PDFs", key="upload_button", disabled=not file_uploads):
            with st.spinner("Processando PDFs... Isso pode levar um momento."):
                st.session_state.vector_db = self.rag_core.create_vector_db_from_files(file_uploads)
                if st.session_state.vector_db:
                    st.session_state.file_uploads = file_uploads
                    st.session_state.pdf_pages = extract_all_pages_as_images(tuple(file_uploads))
                    st.success("PDFs processados e prontos para o chat!")
                else:
                    st.error("Falha ao processar os PDFs.")
        
        st.sidebar.markdown(
        """
        <hr style="margin-top:40px;margin-bottom:10px;">
        <div style='text-align: center; color: gray; font-size: 0.9em;'>
            &copy; 2025 Matheus Bregonci Pires
        </div>
        """,
        unsafe_allow_html=True
        )

        col1, col2 = st.columns([2, 3])

        with col1:
            st.subheader("Visualizador de PDF")
            if st.session_state.get("pdf_pages"):
                if st.button("⚠️ Limpar Base de Dados", use_container_width=True, type="primary"):
                    st.session_state.vector_db.delete_collection()
                    for key in ["vector_db", "messages", "pdf_pages", "file_uploads"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

                zoom_level = st.slider("Nível de Zoom", 100, 1000, 700, 50)
                with st.container(height=450, border=True):
                    for page_image in st.session_state.pdf_pages:
                        st.image(page_image, width=zoom_level)
            else:
                st.info("Faça o upload e processe os PDFs para visualizá-los aqui.")

        with col2:
            st.subheader("Chat")
            with st.container(height=550, border=True) as chat_container:
                for message in st.session_state.messages:
                    avatar = "🤖" if message["role"] == "assistant" else "👤"
                    with st.chat_message(message["role"], avatar=avatar):
                        st.markdown(message["content"])

                if prompt := st.chat_input("Faça uma pergunta sobre os PDFs...", disabled=not st.session_state.vector_db):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user", avatar="👤"):
                        st.markdown(prompt)

                    with st.spinner("Pensando..."):
                        response = self.rag_core.process_question(prompt)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.rerun()

    def _render_latex_conversion_tab(self):
        """Renderiza a interface para conversão de PDF para LaTeX."""
        st.header("PDF Manuscrito para LaTeX")
        uploaded_file = st.file_uploader(
            "Faça upload de um PDF manuscrito (limite de 30 páginas por processamento por bloco)",
            type="pdf",
            key="latex_pdf_upload"
        )

        if uploaded_file:
            if st.button("Converter para LaTeX", disabled=(not self.llm)):
                with st.spinner("Analisando o PDF e gerando o código LaTeX..."):
                    latex_code = self.latex_tools.convert_pdf_to_latex(uploaded_file)
                    if latex_code:
                        with st.spinner("Melhorando o LaTeX gerado..."):
                            improved_latex = self.latex_tools.improve_latex_code(latex_code)
                            st.subheader("Código LaTeX Gerado e Melhorado")
                            st.code(improved_latex, language="latex", line_numbers=True)
                    else:
                        st.error("Falha ao gerar o código LaTeX.")

    def _render_latex_improvement_tab(self):
        """Renderiza a interface para melhoria de código LaTeX."""
        st.header("Melhorar Código LaTeX com Gemini")
        st.write("Cole o código LaTeX abaixo para receber uma versão melhorada.")

        latex_code = st.text_area("Código LaTeX", height=300, key="improve_latex_code")
        
        if st.button("Analisar e Melhorar", disabled=(not latex_code or not self.llm)):
            st.write("Analisando o código LaTeX e enviando para Gemini...")
            with st.spinner("Enviando código para Gemini..."):
                improved_latex = self.latex_tools.improve_latex_code(latex_code)
                if improved_latex:
                    st.subheader("Código LaTeX Melhorado")
                    st.code(improved_latex, language="latex", line_numbers=True)
                else:
                    st.error("Falha ao melhorar o código LaTeX.")
                    
    def _latex_editor_tab(self):
        """
        Renderiza uma aba com layout de IDE para editar e visualizar LaTeX lado a lado.
        """
        st.header("📝 Compilador LaTeX Online")
        st.markdown("Escreva na esquerda e veja o resultado compilado na direita. Para compilar, use os controles abaixo.")

        st.markdown("---")
        control_cols = st.columns([3, 2, 1]) 

        with control_cols[0]:
            nome_arquivo_saida = st.text_input(
                "Nome do arquivo de saída (.pdf)",
                "documento_gerado",
                label_visibility="collapsed" 
            )

        with control_cols[1]:
            if st.button("▶️ Compilar para PDF", type="primary", use_container_width=True):
                st.session_state.code_to_compile = st.session_state.get('latex_code_input', '')
                if st.session_state.code_to_compile.strip() and nome_arquivo_saida.strip():
                    with st.spinner(f"Compilando '{nome_arquivo_saida}.tex'..."):
                        sucesso, resultado = self.latex_tools.compile_latex_to_pdf(st.session_state.code_to_compile, nome_arquivo_saida)
                        st.session_state.compilation_success = sucesso
                        st.session_state.compilation_result = resultado
                        if sucesso:
                            st.session_state.compiled_pdf_path = resultado
                            st.session_state.compiled_pdf_images = extract_pages_as_images_from_path(resultado)
                        else:
                            st.session_state.compiled_pdf_images = None
                else:
                    st.warning("Preencha o editor e o nome do arquivo.")

        with control_cols[2]:
            if st.button("🧹 Limpar Visualização", use_container_width=True):
                st.session_state.compiled_pdf_images = None
                st.session_state.compilation_success = None
                st.session_state.compilation_result = None
                st.rerun()

        st.markdown("---")

        col1, col2 = st.columns(2, gap="small")

        with col1:
            st.subheader("Editor de Código LaTeX")
            valor_padrao_latex = """\\documentclass[12pt, a4paper]{article}
\\usepackage[utf8]{inputenc}
\\usepackage[brazil]{babel}
\\usepackage{amsmath}
\\usepackage{graphicx}

\\title{Visualização Lado a Lado}
\\author{Streamlit App}
\\date{\\today}

\\begin{document}
\\maketitle

\\section{Layout de IDE}
Agora o editor de código e a visualização do PDF estão perfeitamente alinhados, proporcionando uma experiência de desenvolvimento muito mais fluida e intuitiva.

Altere qualquer parte deste documento e clique em \\textbf{Compilar} para ver a mágica acontecer!

$$ \\int_a^b f(x) \\, dx = F(b) - F(a) $$

\\end{document}
"""
            code_value = st.session_state.get('code_to_compile', valor_padrao_latex)
            st.session_state.latex_code_input = st_ace(
                value=code_value, language="latex", theme="tomorrow_night",
                show_gutter=True, font_size=16, height=700, wrap=True,
                key="ace_editor_main"
            )

        with col2:
            st.subheader("Visualização do PDF Compilado")

            if st.session_state.get("compiled_pdf_images"):
                viewer_controls = st.columns([3,2])
                with viewer_controls[0]:
                    zoom_level = st.slider("Nível de Zoom", 100, 1500, 1500, 50, key="latex_zoom_slider", label_visibility="collapsed")
                with viewer_controls[1]:
                    if st.session_state.get("compiled_pdf_path") and os.path.exists(st.session_state.compiled_pdf_path):
                         with open(st.session_state.compiled_pdf_path, "rb") as pdf_file:
                            st.download_button(
                                label="⬇️ Baixar PDF",
                                data=pdf_file,
                                file_name=os.path.basename(st.session_state.compiled_pdf_path),
                                mime="application/pdf",
                                use_container_width=True
                            )
                    else:
                        st.info("Compile o LaTeX para gerar o PDF para download.")

                with st.container(height=615, border=True):
                    for page_image in st.session_state.compiled_pdf_images:
                        st.image(page_image, width=zoom_level)

            elif st.session_state.get('compilation_success') is False:
                st.error("❌ Falha na compilação.")
                st.code(st.session_state.get('compilation_result', 'Nenhum log de erro disponível.'), language="log")

            else:
                st.info("O PDF compilado aparecerá aqui.")

    def _render_latex_to_html_tab(self):
        """Renderiza a aba para converter LaTeX em uma página web interativa."""
        st.header("📄 Gerador de Página Interativa a partir de LaTeX")
        st.markdown("Cole seu texto em LaTeX abaixo. A aplicação irá analisá-lo, renderizar as fórmulas e adicionar visualizações interativas relevantes, como a simulação do momento angular.")
        
        default_latex = """
\\section{Momento Angular em Mecânica Quântica}
Este é um exemplo de como o texto em LaTeX pode ser transformado.
O vetor momento angular orbital, $\\vec{L}$, tem uma magnitude quantizada:
$$ |\\vec{L}| = \\hbar \\sqrt{l(l+1)} $$
Sua projeção no eixo z, $L_z$, também é quantizada:
$$ L_z = m_l \\hbar $$
Como as componentes não comutam, o vetor $\\vec{L}$ precessa em torno do eixo z, como demonstrado na visualização ao lado.
        """
        
        latex_input = st.text_area("Insira seu código LaTeX aqui:", value=default_latex, height=400)
        
        if st.button("Gerar Página Interativa", type="primary"):
            if latex_input.strip():
                with st.spinner("Gerando página HTML..."):
                    html_output = self.web_generator.generate_interactive_page(latex_input)
                        
                if html_output:
                    st.success("Página HTML gerada com sucesso!")
                    st.subheader("Prévia da Página Interativa")
                    st.components.v1.html(html_output, height=600, scrolling=True)

                    href = get_base64_download_link(html_output, "pagina_interativa.html", "Baixar Arquivo HTML")
                    st.markdown(href, unsafe_allow_html=True)
                    
                    with st.expander("Ver Código-Fonte HTML Gerado"):
                        st.code(html_output, language="html")
                else:
                    st.error("Falha ao gerar a página HTML.")

            else:
                st.warning("Por favor, insira um texto em LaTeX.")


    def run(self):
        """Executa a aplicação Streamlit."""
        st.title("🧠 Assistente de PDFs com Gemini")
        st.markdown("""
        Use as abas abaixo para interagir com seus documentos de diferentes maneiras:
        - **Chat RAG PDFs:** Converse com seus documentos.
        - **PDF para LaTeX:** Converta um PDF manuscrito em código LaTeX.
        - **Melhorar LaTeX:** Peça à IA para aprimorar seu código LaTeX.
        - **Editor LaTeX:** Edite e compile seu código LaTeX diretamente na aplicação.
        - **Gerador de Página Interativa:** Transforme seu LaTeX em uma página web rica em insights.
        """)

        if self.setup_api_key_and_llm():
            tabs = st.tabs([
                "Chat RAG PDFs", 
                "PDF para LaTeX", 
                "Melhorar LaTeX", 
                "Editor LaTeX", 
                "Gerador de Página Interativa"
            ])
            with tabs[0]:
                self._render_rag_tab()
            with tabs[1]:
                self._render_latex_conversion_tab()
            with tabs[2]:
                self._render_latex_improvement_tab()
            with tabs[3]:
                self._latex_editor_tab()
            with tabs[4]:
                self._render_latex_to_html_tab()
        else:
            st.info("A aplicação aguarda a configuração da Google API Key na barra lateral.")
        
        st.markdown(
        """
        <hr style="margin-top:40px;margin-bottom:10px;">
        <div style='text-align: center; color: gray; font-size: 0.9em;'>
            &copy; 2025 Matheus Bregonci Pires
        </div>
        """,
        unsafe_allow_html=True
        )

if __name__ == "__main__":
    app = PDFChatApp()
    app.run()