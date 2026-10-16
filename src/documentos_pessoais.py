"""Resolve a pasta de documentos pessoais de uma pessoa (por matrícula) e
mapeia os 5 documentos esperados dentro dela.

Cada pessoa tem uma pasta em `config.DOCUMENTOS_PESSOAIS_DIR`, nomeada com a
matrícula. Dentro da pasta, cada um dos 5 documentos é identificado por um
nome de arquivo fixo (não pela ordem em que o sistema de arquivos lista os
arquivos — essa ordem não é garantida e desalinharia o documento errado com
o papel errado), definido em `config.DOCUMENTOS_PESSOAIS`.
"""

from dataclasses import dataclass
from pathlib import Path

from . import config


class PastaPessoaNaoEncontrada(FileNotFoundError):
    """A pasta esperada para a chave (matrícula) não existe."""


class DocumentosPessoaIncompletos(ValueError):
    """A pasta existe mas está faltando um ou mais dos documentos esperados."""


@dataclass
class DocumentosPessoa:
    chave: str
    pasta: Path
    documentos: dict[str, Path]  # papel -> caminho do PDF


def resolver_pasta(chave: str) -> Path:
    """Retorna a pasta de documentos da pessoa identificada por `chave`
    (matrícula). Levanta PastaPessoaNaoEncontrada com uma mensagem clara se
    a pasta não existir.
    """
    chave = _normalizar_chave(chave)
    pasta = config.DOCUMENTOS_PESSOAIS_DIR / chave
    if not pasta.is_dir():
        raise PastaPessoaNaoEncontrada(
            f"Pasta não encontrada para a chave '{chave}': esperava "
            f"'{pasta}'. Confira se o nome da pasta bate exatamente com a "
            "matrícula da planilha (sem espaço/zero a mais ou a menos)."
        )
    return pasta


def resolver_documentos(chave: str) -> DocumentosPessoa:
    """Resolve a pasta da pessoa e confirma que os 5 documentos esperados
    (config.DOCUMENTOS_PESSOAIS) estão todos presentes dentro dela.

    Levanta DocumentosPessoaIncompletos listando TODOS os arquivos faltando
    de uma vez (não só o primeiro que faltar), pra não exigir rodar a
    validação várias vezes só pra descobrir cada um.
    """
    pasta = resolver_pasta(chave)

    encontrados: dict[str, Path] = {}
    faltando: list[str] = []

    for papel, nome_arquivo in config.DOCUMENTOS_PESSOAIS.items():
        caminho = pasta / nome_arquivo
        if caminho.is_file():
            encontrados[papel] = caminho
        else:
            faltando.append(nome_arquivo)

    if faltando:
        raise DocumentosPessoaIncompletos(
            f"Pasta '{pasta}' (chave '{chave}') está com documento(s) "
            f"faltando: {', '.join(faltando)}. Esperado: "
            f"{', '.join(config.DOCUMENTOS_PESSOAIS.values())}."
        )

    return DocumentosPessoa(chave=chave, pasta=pasta, documentos=encontrados)


def _normalizar_chave(chave: str) -> str:
    chave = str(chave).strip()
    if not chave:
        raise ValueError("Chave (matrícula) vazia — não é possível resolver a pasta.")
    return chave
