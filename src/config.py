"""
Configuração central da automação SEI (Pt2).

Continuação do projeto sei-automacao — reaproveita o mesmo esquema de
conexão a um Chrome já logado via CDP. O objetivo específico desta
automação ainda está sendo definido; por enquanto só a conexão está
montada.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

SEI_URL = "https://sei.exemplo.gov.br"  # URL real da sua instância vai em config_local.py

# Porta de depuração remota do Chrome que você abre manualmente antes de
# rodar a automação (veja README.md -> "Conectar num Chrome já logado").
CDP_URL = "http://localhost:9222"

# ---------------------------------------------------------------------------
# Seletores da interface do SEI (mesmos placeholders do sei-automacao — a
# navegação robusta é por rótulo/texto visível nos helpers de sei_page.py;
# estes SELECTORS entram só como fallback ou onde não há rótulo acessível).
# ---------------------------------------------------------------------------
SELECTORS = {
    "frame_conteudo": "ifrVisualizacao",  # TODO — nome ou seletor do iframe principal
    "campo_nivel_acesso_publico": "#optPublico",  # TODO
    "campo_nivel_acesso_restrito": "#optRestrito",  # TODO
    "campo_nivel_acesso_sigiloso": "#optSigiloso",  # TODO
    "campo_hipotese_legal": "#selHipoteseLegal",
    "campo_nome_arvore": "#txtNomeArvore",  # TODO
    "campo_data_documento": "#txtDataDocumento",  # TODO
}

# ---------------------------------------------------------------------------
# Comportamento
# ---------------------------------------------------------------------------
TIMEOUT_PADRAO_MS = 15_000

# ---------------------------------------------------------------------------
# Documentos pessoais (720 casos: 1 pasta por pessoa, 5 PDFs cada)
# ---------------------------------------------------------------------------
# Cada pessoa tem uma pasta em DOCUMENTOS_PESSOAIS_DIR, nomeada com a
# matrícula (chave estável vinda da planilha — não usa nome completo pra
# evitar acento/espaço/homônimo/caminho longo no Windows).
DOCUMENTOS_PESSOAIS_DIR = BASE_DIR / "data" / "documentos_pessoais"

# Papel (chave lógica do documento) -> nome de arquivo esperado dentro da
# pasta da pessoa. Busca por nome fixo, não pela ordem do sistema de
# arquivos (que não é garantida e desalinharia documento com papel errado).
# Todos os 5 papéis definidos.
DOCUMENTOS_PESSOAIS = {
    "dados_pessoais": "dados_pessoais.pdf",
    "dados_funcionais": "dados_funcionais.pdf",
    "ficha_financeira": "ficha_financeira.pdf",
    "termos_de_nao_ajuizamento": "termos_de_nao_ajuizamento.pdf",
    "planilha_calculo": "planilhaCalculo.pdf",
}

# Papel -> texto do campo "Nome na Árvore" no formulário "Registrar
# Documento Externo", ao incluir cada documento pessoal no processo.
NOMES_ARVORE_DOCUMENTOS_PESSOAIS = {
    "dados_pessoais": "Cadastro dados pessoais",
    "dados_funcionais": "Cadastro dados funcionais",
    "ficha_financeira": "Ficha financeira",
    "termos_de_nao_ajuizamento": "Declaração de Não Ajuizamento de Ação Judicial",
    "planilha_calculo": "Planilha de Cálculo",
}

# Tipo de documento aplicado a cada documento pessoal incluído — "Externo"
# = anexar um arquivo já pronto, em vez de gerar um documento nativo do SEI
# (mesma escolha usada no sei-automacao, Parte 1).
TIPO_DOCUMENTO_PADRAO = "Externo"

# Tipo do documento externo (o <select> dentro do formulário "Registrar
# Documento Externo") — texto completo pra não colidir com outra opção que
# contenha um trecho parecido (ex.: "Nota" também casa com "Anotação").
TIPO_DOCUMENTO_EXTERNO_PADRAO = "Anexo"

# Nível de acesso de cada documento pessoal — "restrito" (diferente do
# "publico" usado nos 4 documentos da Parte 1): estes 5 contêm dado pessoal
# de verdade (CPF, dados funcionais/financeiros), exigem hipótese legal.
NIVEL_ACESSO_DOCUMENTOS_PESSOAIS = "restrito"
HIPOTESE_LEGAL_PADRAO = "Informação Pessoal"

# Planilha com a lista de pessoas (720 casos) — cada linha vira uma pasta em
# DOCUMENTOS_PESSOAIS_DIR pelo valor da coluna abaixo.
PLANILHA_PESSOAS = BASE_DIR / "data" / "pessoas.csv"
PLANILHA_COLUNA_MATRICULA = "Matrícula"

# ---------------------------------------------------------------------------
# Documentos padrão incluídos pelo sei-automacao (Parte 1)
# ---------------------------------------------------------------------------
# Nome (ou trecho) como aparece na árvore do processo — mesmos valores de
# NOME_ARVORE_* em sei-automacao/src/config.py. Usado só pra CONFERIR que a
# Parte 1 já rodou nesse processo antes de incluir os documentos pessoais
# desta Pt2 — não recria nem edita esses documentos.
DOCUMENTOS_PADRAO_PARTE1 = [
    "Nota Técnica Nº X/AAAA/UNIDADE",
    "Despacho - Plano de Trabalho",
    "Despacho - Unificação de Planilhas",
    "Despacho - Aprovação do Plano de Trabalho",
]

# ---------------------------------------------------------------------------
# Overrides locais
# ---------------------------------------------------------------------------
# Os valores acima são exemplos genéricos. Dados reais (URL do SEI, nomes
# dos documentos da Parte 1) ficam em src/config_local.py, que não é
# versionado — veja src/config_local.example.py.
try:
    from .config_local import *  # noqa: F401,F403
except ImportError:
    pass
