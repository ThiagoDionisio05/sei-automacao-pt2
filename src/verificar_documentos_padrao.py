"""Confere se os 4 documentos padrão incluídos pelo sei-automacao (Parte 1)
estão presentes na árvore de um processo do SEI — antes de começar a
incluir os documentos pessoais desta Pt2, confirma que a Parte 1 realmente
rodou nesse processo.

Uso:
    python -m src.verificar_documentos_padrao --numero "00000.000000/0000-00"
"""

import argparse

from playwright.sync_api import Page, sync_playwright

from . import config
from .browser import abrir_sessao
from .sei_page import documento_existe_na_arvore, pesquisar_processo, screenshot


def documentos_padrao_faltando(page: Page) -> list[str]:
    """Retorna os nomes de config.DOCUMENTOS_PADRAO_PARTE1 que NÃO foram
    encontrados na árvore do processo atualmente aberto na tela — lista
    vazia se os 4 estiverem presentes. Usado como trava de segurança antes
    de incluir documento pessoal (ver documento_pessoal.py).
    """
    return [
        nome for nome in config.DOCUMENTOS_PADRAO_PARTE1 if not documento_existe_na_arvore(page, nome)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--numero",
        type=str,
        required=True,
        help="Número do processo SEI a conferir (ex.: 00000.000000/0000-00).",
    )
    args = parser.parse_args()

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)

        print(f"\nPesquisando processo {args.numero}...")
        pesquisar_processo(page, args.numero)
        screenshot(page, "verificacao_documentos_padrao")

        print(f"\nConferindo documentos padrão (Parte 1) no processo {args.numero}:\n")
        tudo_ok = True
        for nome in config.DOCUMENTOS_PADRAO_PARTE1:
            achou = documento_existe_na_arvore(page, nome)
            print(f"  [{'OK' if achou else 'FALTANDO'}] {nome}")
            if not achou:
                tudo_ok = False

        print(
            "\n"
            + (
                "TUDO OK — os 4 documentos padrão estão presentes."
                if tudo_ok
                else "FALTAM documentos — confira screenshots/verificacao_documentos_padrao.png e a árvore do processo."
            )
        )


if __name__ == "__main__":
    main()
