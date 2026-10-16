"""Ponto de entrada da automação SEI (Pt2).

Por enquanto: conecta no Chrome já logado e busca/abre um processo
específico do SEI pelo número — próximo passo (ainda não implementado)
é incluir os documentos pessoais depois de aberto.

Uso:
    python main.py --numero "00000.000000/0000-00"
"""

import argparse

from playwright.sync_api import sync_playwright

from src.browser import abrir_sessao
from src.sei_page import pesquisar_processo, screenshot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--numero",
        type=str,
        required=True,
        help="Número do processo SEI a pesquisar e abrir (ex.: 00000.000000/0000-00).",
    )
    args = parser.parse_args()

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)
        print(f"\nConectado. URL atual: {page.url}")

        print(f"Pesquisando processo {args.numero}...")
        pesquisar_processo(page, args.numero)
        screenshot(page, "processo_aberto")
        print("Screenshot salvo em screenshots/processo_aberto.png")

        # Não fecha o navegador — é o Chrome que você abriu manualmente,
        # continua sob seu controle depois que a automação termina.


if __name__ == "__main__":
    main()
