"""Testa o passo de "Incluir Documento" (documentos pessoais): pesquisa e
abre o processo pelo número, depois inclui um ou mais documentos EM
SEQUÊNCIA — para se algum falhar, não tenta o próximo.

Uso:
    python testar_documento_pessoal.py 00000.000000/0000-00 1234567 dados_pessoais
    python testar_documento_pessoal.py 00000.000000/0000-00 1234567 dados_pessoais dados_funcionais
"""

import sys

from playwright.sync_api import sync_playwright

from src.browser import abrir_sessao
from src.documento_pessoal import incluir_documentos_pessoais
from src.gerar_painel import main as gerar_painel
from src.sei_page import pesquisar_processo, screenshot


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        raise SystemExit(1)

    numero_processo, matricula = sys.argv[1], sys.argv[2]
    papeis = sys.argv[3:]

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)

        print(f"\nPesquisando processo {numero_processo}...")
        pesquisar_processo(page, numero_processo)
        screenshot(page, "00_processo_aberto_antes_do_documento")

        try:
            incluir_documentos_pessoais(page, numero_processo, matricula, papeis)
        finally:
            # Regera o painel mesmo se algo falhar acima — é justamente
            # quando você mais precisa ver a falha refletida no dashboard.
            print("\nAtualizando painel_documentos.html...")
            gerar_painel()


if __name__ == "__main__":
    main()
