"""Gera um dashboard HTML (só leitura) com o status de cada pessoa:
matrícula, nome, pasta de documentos, processo SEI vinculado e quantos dos
documentos pessoais foram CONFIRMADOS anexados no SEI.

Diferente do painel_processos.html do projeto original (tabela editada à
mão, salva em localStorage), este painel é sempre GERADO a partir de
data/pessoas.csv + status/documentos_pessoais.json (gravado pela automação
em documento_pessoal.py a cada documento confirmado na árvore do SEI) — a
fonte da verdade é o que a automação realmente fez no SEI, não o que existe
em disco local nem algo digitado no navegador. Rode de novo sempre que
quiser atualizar:

    python -m src.gerar_painel
"""

import json

import pandas as pd

from . import config
from .status_documentos import carregar_status

COLUNA_NOME = "Nome"
COLUNA_PROCESSO_SEI = "Processo SEI"
COLUNA_PATH = "PATH"

SAIDA_HTML = config.BASE_DIR / "painel_documentos.html"


def carregar_planilha() -> pd.DataFrame:
    if config.PLANILHA_PESSOAS.suffix.lower() == ".csv":
        return pd.read_csv(
            config.PLANILHA_PESSOAS,
            dtype=str,
            keep_default_na=False,
            sep=None,
            engine="python",
            encoding="utf-8-sig",
        )
    return pd.read_excel(config.PLANILHA_PESSOAS, dtype=str)


def montar_linhas(df: pd.DataFrame) -> list[dict]:
    total_esperado = len(config.DOCUMENTOS_PESSOAIS)
    status = carregar_status()
    linhas = []

    for _, row in df.iterrows():
        matricula = str(row.get(config.PLANILHA_COLUNA_MATRICULA, "")).strip()
        if not matricula:
            continue

        nome = str(row.get(COLUNA_NOME, "")).strip()
        processo_sei_planilha = str(row.get(COLUNA_PROCESSO_SEI, "")).strip()
        path_planilha = str(row.get(COLUNA_PATH, "")).strip()
        pasta = config.DOCUMENTOS_PESSOAIS_DIR / matricula

        pessoa_status = status.get(matricula, {})
        # Prioriza o processo confirmado pela automação (status.json); cai
        # pro valor da planilha só antes da automação ter rodado pra essa
        # matrícula.
        processo_sei = pessoa_status.get("processo_sei") or processo_sei_planilha
        documentos_status = pessoa_status.get("documentos", {})

        documentos_ok = 0
        falhas = []
        for papel in config.DOCUMENTOS_PESSOAIS:
            doc = documentos_status.get(papel)
            if doc is None:
                continue
            # entradas antigas (antes do campo "status" existir) só eram
            # gravadas em caso de sucesso — contam como confirmadas.
            estado = doc.get("status", "confirmado")
            if estado == "confirmado":
                documentos_ok += 1
            elif estado == "falhou":
                falhas.append({"papel": papel, "erro": doc.get("erro", "")})

        completo = documentos_ok == total_esperado

        linhas.append(
            {
                "matricula": matricula,
                "nome": nome,
                "path": path_planilha or str(pasta),
                "processo_sei": processo_sei,
                "falhas": falhas,
                "documentos_ok": documentos_ok,
                "documentos_total": total_esperado,
                "completo": completo,
            }
        )

    return linhas


def gerar_html(linhas: list[dict]) -> str:
    # json.dumps com ensure_ascii=False preserva acento; a barra de "</script"
    # é escapada manualmente pra não fechar a tag <script> se algum campo
    # (nome, path) contiver esse texto por acidente.
    dados_json = json.dumps(linhas, ensure_ascii=False).replace("</", "<\\/")

    return _TEMPLATE.replace("__DADOS_JSON__", dados_json)


_TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Painel de Documentos — SEI Pt2</title>
<style>
  :root {
    --bg: #f4f6f8;
    --card: #ffffff;
    --border: #dde2e7;
    --text: #1f2933;
    --text-muted: #6b7684;
    --accent: #0b6e4f;
    --danger: #c0392b;
    --danger-bg: #fdecea;
    --ok-bg: #eafaf1;
    --stripe: #f8fafb;
    --header-bg: #eef2f4;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 32px 24px 64px;
    background: var(--bg);
    color: var(--text);
    font-family: "Segoe UI", Tahoma, Verdana, Arial, sans-serif;
  }
  .wrap { max-width: 1200px; margin: 0 auto; }
  header { margin-bottom: 20px; }
  h1 { font-size: 22px; font-weight: 600; margin: 0 0 4px; }
  .subtitle { color: var(--text-muted); font-size: 13.5px; }
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(16, 24, 32, 0.04);
  }
  .toolbar {
    display: flex;
    gap: 16px;
    align-items: center;
    padding: 14px 16px;
    border-bottom: 1px solid var(--border);
    background: var(--header-bg);
    flex-wrap: wrap;
    font-size: 13px;
  }
  .toolbar .stat { color: var(--text-muted); }
  .toolbar .stat b { color: var(--text); }
  .toolbar button {
    margin-left: auto;
    font: inherit;
    font-size: 13px;
    font-weight: 600;
    border: 1px solid var(--border);
    border-radius: 7px;
    padding: 8px 14px;
    cursor: pointer;
    background: #fff;
    color: var(--text);
  }
  .toolbar button:hover { background: #f0f2f4; }
  table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
  thead th {
    text-align: left;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .04em;
    color: var(--text-muted);
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    background: var(--header-bg);
    position: sticky;
    top: 0;
  }
  tbody tr:nth-child(even) { background: var(--stripe); }
  tbody tr.incompleto { background: #fff9e8; }
  td {
    padding: 9px 16px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }
  td.col-matricula { font-variant-numeric: tabular-nums; font-weight: 600; }
  td.col-path { font-size: 12px; color: var(--text-muted); word-break: break-all; }
  td.col-sei { font-variant-numeric: tabular-nums; }
  .badge {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
  }
  .badge.ok { background: var(--ok-bg); color: var(--accent); }
  .badge.pendente { background: var(--header-bg); color: var(--text-muted); }
  .badge.falha { background: var(--danger-bg); color: var(--danger); cursor: help; }
  tbody tr.tem-falha { background: #fdecea; }
  .empty-state { padding: 40px 16px; text-align: center; color: var(--text-muted); font-size: 13.5px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Painel de Documentos — SEI Pt2</h1>
    <div class="subtitle">
      Gerado a partir de <code>data/pessoas.csv</code> e
      <code>status/documentos_pessoais.json</code> (o que a automação
      confirmou no SEI) — não editável aqui. Pra atualizar, rode
      <code>python -m src.gerar_painel</code> de novo.
    </div>
  </header>

  <div class="card">
    <div class="toolbar">
      <span class="stat">Total: <b id="statTotal"></b></span>
      <span class="stat">Completos: <b id="statCompletos"></b></span>
      <span class="stat">Pendentes: <b id="statPendentes"></b></span>
      <span class="stat">Com falha: <b id="statFalhas" style="color: var(--danger);"></b></span>
      <span class="stat">Sem Processo SEI: <b id="statSemSei"></b></span>
      <button id="btnExport">Exportar CSV</button>
    </div>
    <table>
      <thead>
        <tr>
          <th style="width:110px;">Matrícula</th>
          <th>Nome</th>
          <th>Path</th>
          <th style="width:190px;">Processo SEI</th>
          <th style="width:150px;">Documentos</th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
    <div class="empty-state" id="emptyState" hidden>Nenhuma linha na planilha.</div>
  </div>
</div>

<script>
  const linhas = __DADOS_JSON__;

  const tbody = document.getElementById("tbody");
  const emptyState = document.getElementById("emptyState");

  emptyState.hidden = linhas.length > 0;

  let completos = 0, semSei = 0, comFalha = 0;

  linhas.forEach(l => {
    if (l.completo) completos++;
    if (!l.processo_sei) semSei++;
    if (l.falhas && l.falhas.length) comFalha++;

    const tr = document.createElement("tr");
    if (l.falhas && l.falhas.length) tr.className = "tem-falha";
    else if (!l.completo) tr.className = "incompleto";

    const tdMatricula = document.createElement("td");
    tdMatricula.className = "col-matricula";
    tdMatricula.textContent = l.matricula;

    const tdNome = document.createElement("td");
    tdNome.textContent = l.nome;

    const tdPath = document.createElement("td");
    tdPath.className = "col-path";
    tdPath.textContent = l.path;

    const tdSei = document.createElement("td");
    tdSei.className = "col-sei";
    tdSei.textContent = l.processo_sei || "—";

    const tdDocs = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = "badge " + (l.completo ? "ok" : "pendente");
    badge.textContent = l.documentos_ok + "/" + l.documentos_total;
    tdDocs.appendChild(badge);

    if (l.falhas && l.falhas.length) {
      const badgeFalha = document.createElement("span");
      badgeFalha.className = "badge falha";
      badgeFalha.style.marginLeft = "6px";
      badgeFalha.textContent = l.falhas.length + " falha" + (l.falhas.length > 1 ? "s" : "");
      badgeFalha.title = l.falhas.map(f => f.papel + ": " + f.erro).join("\\n\\n");
      tdDocs.appendChild(badgeFalha);
    }

    tr.appendChild(tdMatricula);
    tr.appendChild(tdNome);
    tr.appendChild(tdPath);
    tr.appendChild(tdSei);
    tr.appendChild(tdDocs);
    tbody.appendChild(tr);
  });

  document.getElementById("statTotal").textContent = linhas.length;
  document.getElementById("statCompletos").textContent = completos;
  document.getElementById("statPendentes").textContent = linhas.length - completos;
  document.getElementById("statFalhas").textContent = comFalha;
  document.getElementById("statSemSei").textContent = semSei;

  document.getElementById("btnExport").addEventListener("click", () => {
    const cabecalho = "Matricula,Nome,Path,Processo SEI,Documentos,Falhas\\n";
    const esc = v => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
    const corpo = linhas.map(l =>
      [esc(l.matricula), esc(l.nome), esc(l.path), esc(l.processo_sei),
       esc(l.documentos_ok + "/" + l.documentos_total),
       esc((l.falhas || []).map(f => f.papel + ": " + f.erro).join(" | "))].join(",")
    ).join("\\n");
    const csv = cabecalho + corpo;
    const blob = new Blob(["\\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "painel_documentos.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
</script>
</body>
</html>
"""


def main():
    if not config.PLANILHA_PESSOAS.is_file():
        raise SystemExit(f"Planilha não encontrada: {config.PLANILHA_PESSOAS}")

    df = carregar_planilha()
    linhas = montar_linhas(df)
    html_final = gerar_html(linhas)
    SAIDA_HTML.write_text(html_final, encoding="utf-8")

    completos = sum(1 for l in linhas if l["completo"])
    print(f"Painel gerado em {SAIDA_HTML} ({len(linhas)} pessoa(s), {completos} completa(s)).")


if __name__ == "__main__":
    main()
