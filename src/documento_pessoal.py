"""Inclusão de um documento pessoal dentro de um processo já aberto no SEI.

Mesmo fluxo do sei-automacao (Parte 1) — Incluir Documento -> Externo ->
Anexo -> Nato-digital -> anexar arquivo -> Salvar -> confere na árvore —
com duas diferenças: o arquivo anexado vem da pasta da pessoa (por
matrícula, ver documentos_pessoais.py) e o nível de acesso é Restrito +
hipótese legal "Informação Pessoal" (a Parte 1 usa Público, porque os 4
documentos dela não têm dado pessoal sensível; estes 5 têm).
"""

from datetime import date

from playwright.sync_api import Page

from . import config, sei_page
from .documentos_pessoais import resolver_pasta
from .status_documentos import marcar_documento_anexado, marcar_documento_falhou
from .verificar_documentos_padrao import documentos_padrao_faltando


def incluir_documento_pessoal(page: Page, numero_processo: str, matricula: str, papel: str) -> None:
    """Registra, como Documento Externo, o documento pessoal `papel`
    (chave de config.DOCUMENTOS_PESSOAIS, ex.: "dados_pessoais") da pessoa
    `matricula`, dentro do processo `numero_processo` — assume que esse
    processo já está aberto na tela.
    """
    if papel not in config.DOCUMENTOS_PESSOAIS:
        raise ValueError(
            f"Papel '{papel}' não está em config.DOCUMENTOS_PESSOAIS "
            f"(válidos: {list(config.DOCUMENTOS_PESSOAIS)})."
        )

    nome_arvore = config.NOMES_ARVORE_DOCUMENTOS_PESSOAIS.get(papel)
    if not nome_arvore or nome_arvore.startswith("TODO"):
        raise ValueError(
            f"Nome na árvore de '{papel}' ainda não foi definido em "
            "config.NOMES_ARVORE_DOCUMENTOS_PESSOAIS."
        )

    pasta = resolver_pasta(matricula)
    arquivo_anexo = pasta / config.DOCUMENTOS_PESSOAIS[papel]
    if not arquivo_anexo.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado para o papel '{papel}' da matrícula {matricula}: "
            f"esperava '{arquivo_anexo}'."
        )

    numero_seguro = numero_processo.replace("/", "-")
    prefixo_screenshot = f"doc_{numero_seguro}_{matricula}_{papel}"

    try:
        _incluir_documento_pessoal_impl(
            page, numero_processo, matricula, papel, nome_arvore, arquivo_anexo, prefixo_screenshot
        )
    except Exception as exc:
        marcar_documento_falhou(matricula, numero_processo, papel, str(exc))
        raise


def _incluir_documento_pessoal_impl(
    page: Page,
    numero_processo: str,
    matricula: str,
    papel: str,
    nome_arvore: str,
    arquivo_anexo,
    prefixo_screenshot: str,
) -> None:
    sei_page.marcar_tempo(f"{prefixo_screenshot}: início")

    # Trava de segurança: não inclui documento pessoal num processo que não
    # passou pela Parte 1 (sei-automacao) direito — os 4 documentos padrão
    # precisam estar todos na árvore antes de continuar.
    faltando = documentos_padrao_faltando(page)
    sei_page.marcar_tempo(f"{prefixo_screenshot}: conferiu documentos padrão (Parte 1)")
    if faltando:
        sei_page.screenshot(page, f"{prefixo_screenshot}_00_documentos_padrao_faltando")
        raise RuntimeError(
            f"O processo {numero_processo} não tem todos os documentos padrão da Parte 1 "
            f"(sei-automacao) — faltando: {', '.join(faltando)}. Não vou incluir documento "
            "pessoal nesse processo até isso ser resolvido. Confira o screenshot "
            f"{prefixo_screenshot}_00_documentos_padrao_faltando.png."
        )

    page.wait_for_timeout(500)
    clicou = sei_page.clicar_por_texto_ou_icone(page, "Incluir Documento")
    sei_page.esperar_carregar(page)
    sei_page.screenshot(page, f"{prefixo_screenshot}_01_apos_clique")
    sei_page.marcar_tempo(f"{prefixo_screenshot}: clicou Incluir Documento")

    if not clicou:
        raise RuntimeError(
            f"Não encontrei o menu 'Incluir Documento' — a tela atual provavelmente não é "
            f"a do processo {numero_processo} aberto (ex.: ainda está em 'Controle de "
            f"Processos'). Confira o screenshot {prefixo_screenshot}_01_apos_clique.png."
        )

    frame = sei_page.frame_conteudo(page)
    sei_page.buscar_e_selecionar(frame, config.TIPO_DOCUMENTO_PADRAO)  # "Externo"
    sei_page.esperar_carregar(page)
    sei_page.screenshot(page, f"{prefixo_screenshot}_02_apos_escolher_tipo")
    sei_page.marcar_tempo(f"{prefixo_screenshot}: escolheu tipo Externo")

    frame = sei_page.frame_conteudo(page)

    ok_tipo = sei_page.selecionar_select_por_rotulo(
        frame, "Tipo do Documento", config.TIPO_DOCUMENTO_EXTERNO_PADRAO
    )

    data_hoje = date.today().strftime("%d/%m/%Y")
    ok_data = sei_page.digitar_por_rotulo_ou_seletor(
        frame, "Data do Documento", config.SELECTORS.get("campo_data_documento", ""), data_hoje
    )

    ok_nome_arvore = sei_page.digitar_por_rotulo_ou_seletor(
        frame, "Nome na Árvore", config.SELECTORS["campo_nome_arvore"], nome_arvore
    )

    marcou_formato = sei_page.marcar_radio(frame, "Nato-digital")

    sei_page.screenshot(page, f"{prefixo_screenshot}_03_apos_campos_basicos")
    sei_page.marcar_tempo(f"{prefixo_screenshot}: preencheu tipo/data/árvore/formato")

    if not ok_tipo:
        raise RuntimeError(
            f"Não consegui selecionar o Tipo do Documento (contendo "
            f"'{config.TIPO_DOCUMENTO_EXTERNO_PADRAO}') no processo {numero_processo}. "
            f"Confira o screenshot {prefixo_screenshot}_03_apos_campos_basicos.png."
        )
    if not ok_data:
        raise RuntimeError(
            f"Não consegui confirmar o preenchimento de 'Data do Documento' no processo "
            f"{numero_processo}. Confira o screenshot {prefixo_screenshot}_03_apos_campos_basicos.png."
        )
    if not ok_nome_arvore:
        raise RuntimeError(
            f"Não consegui confirmar o preenchimento de 'Nome na Árvore' no processo "
            f"{numero_processo}. Confira o screenshot {prefixo_screenshot}_03_apos_campos_basicos.png."
        )
    if not marcou_formato:
        raise RuntimeError(
            f"Não consegui marcar o Formato 'Nato-digital' no processo {numero_processo}. "
            f"Confira o screenshot {prefixo_screenshot}_03_apos_campos_basicos.png."
        )

    # Nível de acesso Restrito + hipótese legal — diferente do "Público"
    # simples da Parte 1, porque este documento tem dado pessoal real.
    sei_page.selecionar_nivel_acesso(frame, config.NIVEL_ACESSO_DOCUMENTOS_PESSOAIS)
    # O SEI carrega as opções de Hipótese Legal via AJAX depois de marcar
    # "Restrito" — essa pausa dá tempo desse carregamento terminar antes do
    # polling começar (visto na prática: falhava por 0 opções carregadas).
    page.wait_for_timeout(500)
    sei_page.selecionar_hipotese_legal(frame, config.HIPOTESE_LEGAL_PADRAO, timeout_ms=8000)

    sei_page.screenshot(page, f"{prefixo_screenshot}_04_apos_nivel_acesso")
    sei_page.marcar_tempo(f"{prefixo_screenshot}: marcou nível de acesso restrito + hipótese legal")

    anexou = sei_page.anexar_arquivo(frame, arquivo_anexo)
    sei_page.screenshot(page, f"{prefixo_screenshot}_05_apos_anexar")
    sei_page.marcar_tempo(f"{prefixo_screenshot}: anexou arquivo")

    if not anexou:
        raise RuntimeError(
            f"Campos preenchidos, mas não consegui anexar o arquivo ({arquivo_anexo}) "
            f"no processo {numero_processo}. Confira o screenshot {prefixo_screenshot}_05_apos_anexar.png."
        )

    sei_page.clicar_botao(frame, "Salvar")
    sei_page.esperar_carregar(page)
    page.wait_for_timeout(400)

    sei_page.screenshot(page, f"{prefixo_screenshot}_06_apos_salvar")
    sei_page.marcar_tempo(f"{prefixo_screenshot}: salvou")

    # Recarrega antes de verificar: a árvore às vezes não atualiza sozinha
    # logo após o Salvar (mesmo comportamento observado no sei-automacao).
    page.reload()
    sei_page.esperar_carregar(page)
    sei_page.marcar_tempo(f"{prefixo_screenshot}: recarregou pra verificar")

    if not sei_page.documento_existe_na_arvore(page, nome_arvore):
        sei_page.screenshot(page, f"{prefixo_screenshot}_erro_nao_apareceu_na_arvore")
        raise RuntimeError(
            f"Cliquei em Salvar, mas '{nome_arvore}' não apareceu na árvore do processo "
            f"{numero_processo} depois — o documento provavelmente NÃO foi anexado de "
            f"verdade. Confira o screenshot {prefixo_screenshot}_erro_nao_apareceu_na_arvore.png "
            "e verifique manualmente no SEI antes de tentar de novo."
        )

    marcar_documento_anexado(matricula, numero_processo, papel, nome_arvore)

    print(
        f"Documento pessoal '{papel}' ({nome_arvore}) salvo no processo {numero_processo} "
        f"(matrícula {matricula})."
    )


def incluir_documentos_pessoais(
    page: Page, numero_processo: str, matricula: str, papeis: list[str]
) -> None:
    """Inclui, NA ORDEM de `papeis`, os documentos pessoais informados.

    Pula (idempotente) os que já estiverem na árvore. PARA a sequência se
    algum documento falhar — incluir_documento_pessoal já levanta exceção
    se o documento não for confirmado na árvore depois de salvar, então um
    papel só é tentado se o anterior realmente foi anexado (ou já existia).
    """
    for papel in papeis:
        nome_arvore = config.NOMES_ARVORE_DOCUMENTOS_PESSOAIS.get(papel, "")
        if (
            nome_arvore
            and not nome_arvore.startswith("TODO")
            and sei_page.documento_existe_na_arvore(page, nome_arvore)
        ):
            print(
                f"Documento pessoal '{papel}' ({nome_arvore}) já existe no processo "
                f"{numero_processo} — pulando."
            )
            marcar_documento_anexado(matricula, numero_processo, papel, nome_arvore)
            continue

        incluir_documento_pessoal(page, numero_processo, matricula, papel)
