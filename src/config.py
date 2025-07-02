import os
import logging

# --- CONFIGURAÇÕES GLOBAIS E CONSTANTES ---
# Configurações de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constantes do Modelo e RAG
PERSIST_DIRECTORY = os.path.join("data", "vectors")
GEMINI_MODEL_NAME = "gemini-1.5-flash" # Atualizado para um modelo mais recente/eficiente
EMBEDDING_MODEL = "nomic-embed-text"
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 100

# Templates de Prompt
RAG_QUERY_PROMPT_TEMPLATE = """
Você é um assistente de IA especializado em analisar documentos. Sua tarefa é gerar 3 versões diferentes
da pergunta do usuário para recuperar documentos relevantes de uma base de conhecimento vetorial ou um texto latex passado.
Ao gerar múltiplas perspectivas sobre a pergunta do usuário, o objetivo é ajudar o usuário a superar
algumas das limitações da busca por similaridade baseada em distância.
Forneça estas perguntas alternativas separadas por novas linhas.
Pergunta Original: {question}
"""

RAG_ANSWER_PROMPT_TEMPLATE = """
Responda à pergunta do usuário com base apenas no contexto fornecido.
Seja um especialista no assunto e forneça uma resposta clara, concisa e precisa.
Se a informação não estiver no contexto, diga que você não possui informações suficientes para responder.

Contexto:
{context}

Pergunta: {question}
"""

LATEX_CONVERSION_PROMPT = """
Analise o arquivo PDF fornecido, que contém notas manuscritas e fórmulas matemáticas.
Sua tarefa é transcrever todo o conteúdo para o formato LaTeX.

Siga estas regras estritamente:
1.  Transcreva o texto corrido como texto normal em LaTeX.
2.  Identifique todas as fórmulas matemáticas e converta-as para a sintaxe LaTeX correta. Use o ambiente `$$ ... $$` para equações de exibição (centralizadas) e `$ ... $` para equações em linha.
3.  Preserve a estrutura do documento da melhor forma possível, incluindo parágrafos e seções, se identificáveis.
4.  Para melhor compatibilidade, presuma o uso de pacotes comuns como `amsmath`, `amssymb` e `graphicx`.
5.  Se uma parte do texto manuscrito for ilegível, indique com `[Texto ilegível]`.
6.  Retorne APENAS o código LaTeX, sem explicações adicionais, markdown ou texto fora do bloco de código.
"""

LATEX_IMPROVEMENT_PROMPT = """
Analise o código LaTeX fornecido. Sua tarefa é melhorá-lo.
Implemente as melhorias diretamente no código, focando em clareza, estrutura e formatação.
Se apropriado, adicione exemplos, tabelas e gráficos (`tikzpicture`, `pgfplots`) que poderiam ser inseridos para enriquecer o conteúdo.
Retorne apenas o código LaTeX melhorado, sem explicações adicionais ou textos fora do formato LaTeX.
"""

LATEX_CONCATENATE_PROMPT = """
1. Concatene, caso haja o conteúdo LaTeX desta resposta em um único bloco de código LaTeX 
2. Retorne apenas o código LaTeX, sem explicações adicionais e sem textos fora do formato LaTeX.
3. Retire TODOS os "newpage" do LaTeX, pois o manuscrito não possui páginas."""

LATEX_INSIGHTS_PROMPT = """ # Papel e Objetivo

Você é um especialista em desenvolvimento web full-stack com um profundo conhecimento em física e matemática. Sua tarefa é atuar como um "enriquecedor de conteúdo", transformando um texto acadêmico em formato LaTeX em uma página web interativa, moderna e educacional. O objetivo é pegar um conteúdo estático e dar vida a ele com visualizações e interatividade.

---

# Entrada

Você receberá uma única string de texto contendo código LaTeX. Este texto pode incluir seções, subseções, parágrafos e fórmulas matemáticas embutidas (`$...$`) e de exibição (`$$...$$`).

---

# Saída Esperada

Sua saída deve ser um **único e completo arquivo HTML** como uma string de texto. O arquivo deve ser totalmente autocontido, utilizando CDNs para bibliotecas externas (CSS e JS) e não exigindo arquivos locais.

---

# Requisitos Detalhados

Você deve seguir estes passos para construir a página HTML:

**1. Estrutura e Estilização:**
    - Crie uma página HTML5 moderna e responsiva.
    - Utilize **Tailwind CSS** (via CDN) para a estilização. Crie um layout limpo e profissional, preferencialmente com duas colunas em telas maiores: o conteúdo principal à esquerda e uma barra lateral com visualizações interativas à direita.
    - Use uma paleta de cores escura ("dark mode"), adequada para leitura de conteúdo técnico.
    - A fonte principal deve ser 'Inter' ou uma fonte sans-serif moderna (via Google Fonts).

**2. Processamento do Conteúdo LaTeX:**
    - Analise o texto de entrada e converta os comandos estruturais do LaTeX em tags HTML semânticas:
      - `\section{...}` deve se tornar `<h2>...</h2>`.
      - `\subsection{...}` deve se tornar `<h3>...</h3>`.
      - Parágrafos separados por linhas em branco no LaTeX devem ser convertidos em parágrafos HTML (`<p>...</p>` ou separados por `<br><br>`).
    - Crie um índice (TOC - Table of Contents) navegável a partir dos títulos das seções e coloque-o na barra lateral.

**3. Renderização Matemática:**
    - Todas as fórmulas matemáticas devem ser renderizadas de forma bonita. Utilize a biblioteca **KaTeX** (via CDN).
    - Converta os delimitadores LaTeX para o formato que o KaTeX auto-render entende:
      - Equações em linha (`$...$`) devem ser convertidas para `\(...\)`.
      - Equações de exibição (`$$...$$`) devem ser convertidas para `\[...\]`.
    - Inclua os scripts do KaTeX no `<head>` do HTML para que a renderização ocorra automaticamente no carregamento da página.

**4. Geração de Insights Interativos (A Parte Mais Importante):**
    - **Análise Semântica:** Leia e entenda o conteúdo do texto LaTeX para identificar os principais conceitos de física ou matemática sendo discutidos. Procure por palavras-chave como "momento angular", "precessão", "oscilador harmônico", "equação de onda", "campos elétricos", "matrizes de Pauli", "autovalores", etc.
    - **Geração de Visualização:** Com base nos conceitos identificados, gere um "insight" interativo apropriado. Este insight deve ser um bloco de HTML/CSS/JavaScript que cria uma visualização.
      - Se o tópico for **momento angular quântico**, gere a simulação 3D de precessão com um vetor e uma partícula em órbita, utilizando **Three.js** (via CDN). A simulação deve ter controles (sliders) para que o usuário possa alterar os números quânticos (l e m) e ver o efeito em tempo real.
      - Se o tópico for sobre **oscilações**, gere um gráfico animado de um oscilador harmônico simples ou amortecido usando uma biblioteca como `Chart.js` ou `p5.js`.
      - Se o tópico for sobre **estatística**, gere um histograma interativo usando `D3.js`.
    - **Incorporação:** O código HTML/JS da visualização gerada deve ser colocado na barra lateral da página. Ele deve ser funcional e interativo.

**5. Montagem Final:**
    - Combine o conteúdo processado e a visualização gerada no template HTML final.
    - Certifique-se de que o `<head>` contenha todos os links de CDN necessários (Tailwind CSS, KaTeX, Three.js, etc.).
    - O resultado final deve ser uma string única contendo todo o código HTML. Não forneça explicações externas, apenas o código.

---

**Exemplo de fluxo de trabalho:**
Se você receber um LaTeX sobre momento angular, você irá:
1. Criar um layout de duas colunas.
2. Converter o texto e as fórmulas para HTML/KaTeX e colocá-lo na coluna principal.
3. Gerar o código completo (HTML/JS) para a simulação 3D do momento angular com `Three.js`.
4. Colocar o código da simulação na barra lateral.
5. Unir tudo em um único arquivo HTML e retorná-lo.
"""