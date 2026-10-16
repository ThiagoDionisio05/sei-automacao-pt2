"""Validação pré-voo (pre-flight): confere, ANTES de rodar a automação real
no SEI, se toda pessoa da planilha tem uma pasta de documentos completa (os
5 arquivos esperados) — evita descobrir pasta/arquivo faltando no meio de um
lote de centenas de casos.

Uso:
    python -m src.validar_pastas
    python -m src.validar_pastas --planilha caminho/outro.csv --coluna matricula
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from . import config
from .documentos_pessoais import (
    DocumentosPessoaIncompletos,
    PastaPessoaNaoEncontrada,
    resolver_documentos,
)


def carregar_matriculas(caminho: Path, coluna: str) -> list[str]:
    """Lê a coluna-chave da planilha como texto puro (nunca deixa o pandas
    inferir tipo numérico) — é isso que preserva zero à esquerda em
    matrícula/CPF. Aceita .csv (detecta "," ou ";" automaticamente, já que
    Excel PT-BR costuma exportar com ";"; "utf-8-sig" descarta o BOM que o
    Excel grava ao salvar como "CSV UTF-8", que senão gruda no nome da
    primeira coluna) ou .xlsx.
    """
    if caminho.suffix.lower() == ".csv":
        df = pd.read_csv(
            caminho,
            dtype=str,
            keep_default_na=False,
            sep=None,
            engine="python",
            encoding="utf-8-sig",
        )
    else:
        df = pd.read_excel(caminho, dtype=str)

    if coluna not in df.columns:
        raise SystemExit(
            f"Coluna '{coluna}' não encontrada em {caminho}. "
            f"Colunas disponíveis: {list(df.columns)}"
        )

    return [str(v).strip() for v in df[coluna].tolist()]


def validar(matriculas: list[str]) -> bool:
    vazias = sum(1 for m in matriculas if not m)
    if vazias:
        print(f"AVISO: {vazias} linha(s) com matrícula vazia na planilha — ignoradas.")
    matriculas = [m for m in matriculas if m]

    duplicadas = sorted({m for m in matriculas if matriculas.count(m) > 1})

    ok, sem_pasta, incompletas = [], [], []
    for matricula in matriculas:
        try:
            resolver_documentos(matricula)
            ok.append(matricula)
        except PastaPessoaNaoEncontrada:
            sem_pasta.append(matricula)
        except DocumentosPessoaIncompletos as exc:
            incompletas.append((matricula, str(exc)))

    print(f"\n=== Validação de pastas ({len(matriculas)} matrícula(s) na planilha) ===")
    print(f"OK: {len(ok)}")
    print(f"Sem pasta: {len(sem_pasta)}")
    print(f"Pasta incompleta: {len(incompletas)}")
    print(f"Matrícula duplicada na planilha: {len(duplicadas)}")

    if duplicadas:
        print("\nMatrículas duplicadas na planilha:")
        for m in duplicadas:
            print(f"  - {m}")

    if sem_pasta:
        print("\nPastas não encontradas:")
        for m in sem_pasta:
            print(f"  - {m}")

    if incompletas:
        print("\nPastas incompletas:")
        for m, msg in incompletas:
            print(f"  - {m}: {msg}")

    orfas = _pastas_sem_planilha(matriculas)
    if orfas:
        print(
            f"\nAVISO: {len(orfas)} pasta(s) em {config.DOCUMENTOS_PESSOAIS_DIR} "
            "não correspondem a nenhuma matrícula da planilha (possível erro "
            "de digitação no nome da pasta):"
        )
        for p in orfas:
            print(f"  - {p}")

    tudo_ok = not duplicadas and not sem_pasta and not incompletas
    print(
        "\n"
        + ("TUDO OK — pode rodar o lote." if tudo_ok else "PROBLEMAS ENCONTRADOS — corrija antes de rodar o lote real.")
    )
    return tudo_ok


def _pastas_sem_planilha(matriculas: list[str]) -> list[str]:
    if not config.DOCUMENTOS_PESSOAIS_DIR.is_dir():
        return []
    esperadas = set(matriculas)
    existentes = {p.name for p in config.DOCUMENTOS_PESSOAIS_DIR.iterdir() if p.is_dir()}
    return sorted(existentes - esperadas)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--planilha", type=Path, default=config.PLANILHA_PESSOAS)
    parser.add_argument("--coluna", type=str, default=config.PLANILHA_COLUNA_MATRICULA)
    args = parser.parse_args()

    if not args.planilha.is_file():
        raise SystemExit(f"Planilha não encontrada: {args.planilha}")

    matriculas = carregar_matriculas(args.planilha, args.coluna)
    tudo_ok = validar(matriculas)
    sys.exit(0 if tudo_ok else 1)


if __name__ == "__main__":
    main()
