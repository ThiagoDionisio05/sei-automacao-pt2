"""Inclui os documentos pessoais em vários processos, numa sessão só do
Chrome — depois de terminar um processo, sai pra "Controle de Processos"
antes de pesquisar o próximo (sair_do_processo, mesma lógica do
sei-automacao/automatizaçao_PDF). Um processo falhar não impede os outros
do lote — a falha fica registrada no status e o lote continua.

Usa por padrão todos os papéis já prontos em
config.NOMES_ARVORE_DOCUMENTOS_PESSOAIS (os que não estão mais como TODO).

Uso:
    python rodar_lote_pessoal.py "00000.000000/0000-00" 1234567 "00000.000000/0000-01" 7654321
"""

import sys

from playwright.sync_api import sync_playwright

from src import config
from src.browser import abrir_sessao
from src.documento_pessoal import incluir_documentos_pessoais
from src.gerar_painel import main as gerar_painel
from src.sei_page import pesquisar_processo, sair_do_processo, screenshot

PAPEIS_PRONTOS = [
    papel
    for papel, nome in config.NOMES_ARVORE_DOCUMENTOS_PESSOAIS.items()
    if nome and not nome.startswith("TODO")
]


def main():
    args = sys.argv[1:]
    if len(args) < 2 or len(args) % 2 != 0:
        print(__doc__)
        raise SystemExit(1)

    pares = list(zip(args[0::2], args[1::2]))  # [(numero_processo, matricula), ...]

    print(f"Papéis a incluir em cada processo: {', '.join(PAPEIS_PRONTOS)}\n")

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)

        try:
            for i, (numero_processo, matricula) in enumerate(pares, start=1):
                print(f"\n=== [{i}/{len(pares)}] Processo {numero_processo} (matrícula {matricula}) ===")
                pesquisar_processo(page, numero_processo)
                screenshot(page, f"lote_{i}_00_processo_aberto")

                try:
                    incluir_documentos_pessoais(page, numero_processo, matricula, PAPEIS_PRONTOS)
                except Exception as exc:
                    print(f"ERRO no processo {numero_processo} (matrícula {matricula}): {exc}")
                    print("Registrado no status — continuando pro próximo do lote.")

                if i < len(pares):
                    try:
                        sair_do_processo(page)
                    except Exception as exc:
                        print(
                            f"\nAVISO: não consegui voltar pra 'Controle de Processos' ({exc})."
                            "\nParando o lote por segurança — os próximos processos não seriam "
                            "pesquisados corretamente com a tela num estado desconhecido."
                        )
                        break
        finally:
            print("\nAtualizando painel_documentos.html...")
            gerar_painel()


if __name__ == "__main__":
    main()
