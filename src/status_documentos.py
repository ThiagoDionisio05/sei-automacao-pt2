"""Status de anexação dos documentos pessoais no SEI.

Grava, por matrícula, qual processo SEI foi usado e o status de cada
documento pessoal: "confirmado" (documento_existe_na_arvore confirmou no
SEI de verdade, não só presença local) ou "falhou" (a inclusão foi tentada
e deu erro — guarda o motivo).

É a fonte da verdade que o painel (gerar_painel.py) lê — sem isso, o
dashboard não tinha como saber o que a automação realmente fez no SEI, nem
onde ela travou num lote de centenas de casos.
"""

import json
from datetime import datetime, timezone

from . import config

STATUS_FILE = config.BASE_DIR / "status" / "documentos_pessoais.json"


def carregar_status() -> dict:
    if not STATUS_FILE.is_file():
        return {}
    return json.loads(STATUS_FILE.read_text(encoding="utf-8"))


def salvar_status(status: dict) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _registrar(matricula: str, numero_processo: str, papel: str, status_doc: str, **campos) -> None:
    status = carregar_status()
    pessoa = status.setdefault(matricula, {})
    pessoa["processo_sei"] = numero_processo
    documentos = pessoa.setdefault("documentos", {})
    documentos[papel] = {
        "status": status_doc,
        "atualizado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **campos,
    }
    salvar_status(status)


def marcar_documento_anexado(
    matricula: str, numero_processo: str, papel: str, nome_arvore: str
) -> None:
    """Registra que `papel` foi confirmado anexado no `numero_processo` da
    `matricula` — chamado logo depois de confirmar o documento na árvore
    do SEI (sucesso real, não tentativa)."""
    _registrar(matricula, numero_processo, papel, "confirmado", nome_arvore=nome_arvore)


def marcar_documento_falhou(matricula: str, numero_processo: str, papel: str, erro: str) -> None:
    """Registra que a inclusão de `papel` foi TENTADA no `numero_processo`
    da `matricula` e falhou — guarda o motivo pra dar pra ver depois, sem
    precisar reler o log/screenshots de uma rodada de centenas de casos."""
    _registrar(matricula, numero_processo, papel, "falhou", erro=erro)


def status_documento(matricula: str, papel: str) -> str | None:
    """"confirmado", "falhou" ou None (nunca tentado) — entradas gravadas
    antes desse campo existir (só tinham 'nome_arvore') contam como
    "confirmado", já que só eram gravadas em caso de sucesso."""
    doc = carregar_status().get(matricula, {}).get("documentos", {}).get(papel)
    if doc is None:
        return None
    return doc.get("status", "confirmado")


def documento_anexado(matricula: str, papel: str) -> bool:
    return status_documento(matricula, papel) == "confirmado"
