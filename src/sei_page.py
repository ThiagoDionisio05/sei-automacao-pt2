"""Helpers genéricos de navegação/diagnóstico no SEI.

Os helpers de busca/abertura de processo (localizar_campo_pesquisa,
pesquisar_processo, sair_do_processo) foram portados do projeto
automatizaçao_PDF; documento_existe_na_arvore e os helpers de formulário
abaixo (frame_conteudo, buscar_e_selecionar, selecionar_select_por_rotulo,
digitar_por_rotulo_ou_seletor, marcar_radio, anexar_arquivo, clicar_botao,
selecionar_nivel_acesso, selecionar_hipotese_legal) foram portados do
sei-automacao (mesma lógica de conexão/navegação usada nos dois).
"""

import re
import time

from playwright.sync_api import Frame, Page

from . import config

_ultimo_tempo: float | None = None


def marcar_tempo(rotulo: str) -> None:
    """Imprime quanto tempo passou desde a última chamada a esta função —
    diagnóstico pra ver onde o tempo está indo em cada etapa da inclusão de
    documento (útil num lote de centenas de casos)."""
    global _ultimo_tempo
    agora = time.perf_counter()
    if _ultimo_tempo is not None:
        print(f"  [tempo] {rotulo}: {agora - _ultimo_tempo:.1f}s")
    _ultimo_tempo = agora


def frame_conteudo(page: Page) -> Frame:
    """Retorna o frame principal onde os formulários do SEI são renderizados.

    O SEI organiza a tela em frames (menu, árvore, conteúdo). A maior parte
    dos formulários fica no frame de conteúdo. Ajuste o seletor em
    config.SELECTORS['frame_conteudo'] conforme a instância real.
    """
    nome = config.SELECTORS["frame_conteudo"]
    frame = page.frame(name=nome)
    if frame is None:
        handle = page.query_selector(f"iframe[name='{nome}'], {nome}")
        if handle:
            frame = handle.content_frame()
    if frame is None:
        outros_frames = [f for f in page.frames if f != page.main_frame]
        if not outros_frames:
            print(f"(Sem iframes nesta tela — usando a página principal em vez de '{nome}'.)")
            return page.main_frame
        print(f"\nFrames disponíveis na página (procurando por '{nome}'):")
        for f in page.frames:
            print(f"  name={f.name!r}  url={f.url!r}")
        raise RuntimeError(
            f"Não encontrei o frame de conteúdo ('{nome}'). "
            "Ajuste config.SELECTORS['frame_conteudo']."
        )
    return frame


def buscar_e_selecionar(frame, texto: str, timeout_ms: int = 8000) -> None:
    """Digita `texto` no campo de busca visível da tela e clica no item da
    lista de resultados que corresponde exatamente a esse texto.

    Usado em telas do SEI que são um campo de filtro + lista clicável
    (ex.: "Escolha o Tipo de Documento"), em vez de um <select> tradicional.
    """
    campo_busca = frame.locator("input[type='text'], input:not([type])").first
    campo_busca.fill(texto)
    item = frame.get_by_text(texto, exact=True).first
    item.wait_for(state="visible", timeout=timeout_ms)
    item.click()


def selecionar_select_por_rotulo(frame, rotulo: str, texto: str, timeout_ms: int = 5000) -> bool:
    """Seleciona, num <select> nativo achado pelo rótulo visível, a opção
    cujo texto contém `texto` (não precisa ser igual). Faz polling porque
    as opções desse tipo de campo no SEI às vezes carregam via AJAX depois
    do campo já estar visível. Retorna True se conseguiu selecionar.
    """
    try:
        campo = frame.get_by_label(rotulo, exact=False)
        campo.wait_for(state="visible", timeout=timeout_ms)
    except Exception:
        return False

    correspondente = None
    tentativas = max(1, timeout_ms // 300)
    for _ in range(tentativas):
        try:
            opcoes = campo.locator("option").all_inner_texts()
        except Exception:
            opcoes = []
        correspondente = next((o for o in opcoes if texto.lower() in o.lower()), None)
        if correspondente:
            break
        frame.wait_for_timeout(300)

    if not correspondente:
        try:
            todas = campo.locator("option").all_inner_texts()
        except Exception:
            todas = []
        primeiro_termo = texto.split()[0].lower() if texto.split() else texto.lower()
        parecidas = [o for o in todas if primeiro_termo in o.lower()]
        print(f"\nNão achei opção contendo '{texto}' em '{rotulo}'.")
        if parecidas:
            print(f"Opções parecidas (contêm '{primeiro_termo}'): {parecidas}")
        else:
            print(f"Nenhuma opção contém '{primeiro_termo}'. Todas as opções: {todas}")
        return False

    try:
        campo.select_option(label=correspondente)
        return True
    except Exception:
        return False


def digitar_por_rotulo_ou_seletor(
    frame, rotulo: str, seletor: str, texto: str, delay: int = 10
) -> bool:
    """Digita um texto tecla por tecla (não usa .fill()) num campo achado
    pelo rótulo visível, com fallback pro seletor configurado. Necessário
    para campos com máscara/validação em JS (ex.: data), que costumam não
    reagir a um .fill() direto — só a eventos reais de teclado.

    CONFIRMA que o valor realmente entrou no campo (lê input_value() depois
    de digitar), tentando de novo uma vez se vier vazio — visto na prática:
    press_sequentially às vezes não dá erro nenhum, mas o campo (ex.: "Data
    do Documento") fica vazio mesmo assim, e o SEI bloqueia o Salvar sem
    aviso claro. Retorna True só se confirmou.
    """

    def _tentar(localizador) -> bool:
        for _ in range(2):
            try:
                campo = localizador()
                campo.click()
                campo.press_sequentially(texto, delay=delay)
                if campo.input_value().strip():
                    return True
            except Exception:
                pass
        return False

    if _tentar(lambda: frame.get_by_label(rotulo, exact=False)):
        return True

    return _tentar(lambda: frame.locator(seletor))


def marcar_radio(frame, rotulo: str, timeout_ms: int = 2000) -> bool:
    """Marca um radio button pelo rótulo visível, direto com força (esses
    campos do SEI raramente passam na checagem normal de visibilidade, então
    a tentativa "normal" só perde tempo). Retorna True se conseguiu marcar.
    """
    try:
        frame.get_by_label(rotulo, exact=True).check(timeout=timeout_ms, force=True)
        return True
    except Exception:
        return False


def anexar_arquivo(frame, caminho_arquivo, timeout_ms: int = 5000) -> bool:
    """Anexa um arquivo direto no <input type="file"> escondido atrás do
    botão "Anexar Arquivo..." — não precisa clicar no botão nem interagir
    com a janela nativa do sistema, é bem mais rápido e confiável.

    Depois de setar o arquivo no input, CONFIRMA que o SEI realmente
    registrou o anexo, checando o contador "Lista de Anexos (N
    registros)". Visto na prática: o input aceita o caminho sem erro, mas
    o SEI às vezes não processa o anexo a tempo — se seguisse pro Salvar
    nesse instante, salvava um documento vazio ("Documento não contém
    anexo."), sem nenhum erro visível na hora.
    """
    try:
        campo = frame.locator("input[type='file']").first
        campo.set_input_files(str(caminho_arquivo), timeout=timeout_ms)
    except Exception:
        return False

    contador = frame.get_by_text(re.compile(r"Lista de Anexos \(\d+ registro"))
    tentativas = max(1, timeout_ms // 300)
    for _ in range(tentativas):
        try:
            texto = contador.first.inner_text()
            match = re.search(r"\((\d+) registro", texto)
            if match and int(match.group(1)) >= 1:
                return True
        except Exception:
            pass
        frame.wait_for_timeout(300)

    return False


def clicar_botao(frame, texto: str, timeout_ms: int = 8000) -> None:
    """Clica num botão pelo texto/rótulo visível (ex.: "Salvar").

    A tela pode ter mais de um elemento com esse texto (cópia fixa no topo
    + botão real embaixo, por exemplo) — em vez de confiar cegamente no
    primeiro (`.first`), procura especificamente um que esteja visível.
    """
    candidatos = [
        frame.get_by_role("button", name=texto, exact=True),
        frame.get_by_text(texto, exact=True),
    ]
    for loc in candidatos:
        try:
            total = loc.count()
        except Exception:
            continue
        for i in range(total):
            item = loc.nth(i)
            try:
                if item.is_visible():
                    item.click(timeout=timeout_ms)
                    return
            except Exception:
                continue

    raise RuntimeError(f"Não encontrei nenhum botão visível com o texto '{texto}'.")


def selecionar_nivel_acesso(frame, nivel: str) -> None:
    """Marca o rádio de Nível de Acesso (do processo ou do documento,
    conforme a tela) e CONFIRMA que marcou.

    `nivel` é "publico", "restrito" ou "sigiloso". Tenta várias estratégias
    e, ao final, verifica de fato o estado do rádio — se nenhuma estratégia
    realmente marcou o campo, mostra um diagnóstico de todos os rádios da
    tela em vez de seguir em frente silenciosamente.
    """
    rotulo = nivel.capitalize()
    erros = []

    def esta_marcado() -> bool:
        try:
            return frame.get_by_label(rotulo, exact=True).is_checked()
        except Exception:
            return False

    chave = f"campo_nivel_acesso_{nivel}"
    seletor = config.SELECTORS.get(chave)

    tentativas = [
        ("get_by_label (force)", lambda: frame.get_by_label(rotulo, exact=True).check(timeout=2000, force=True)),
        ("get_by_label", lambda: frame.get_by_label(rotulo, exact=True).check(timeout=2000)),
    ]
    if seletor:
        tentativas.append((f"seletor {seletor} (force)", lambda: frame.locator(seletor).first.check(timeout=2000, force=True)))
        tentativas.append((f"seletor {seletor}", lambda: frame.locator(seletor).first.check(timeout=2000)))

    for nome_tentativa, fn in tentativas:
        try:
            fn()
        except Exception as e:
            erros.append(f"{nome_tentativa}: {e}")
            continue
        if esta_marcado():
            return

    radios = frame.locator("input[type='radio']")
    total = radios.count()
    print(f"\nNão consegui marcar '{rotulo}' no Nível de Acesso. Tentativas:")
    for e in erros:
        print(f"  - {e}")
    if total:
        print("Rádios encontrados na tela:")
        for i in range(total):
            r = radios.nth(i)
            try:
                rid = r.get_attribute("id") or ""
                rname = r.get_attribute("name") or ""
                rvalue = r.get_attribute("value") or ""
                checked = r.is_checked()
                print(f"  id={rid!r} name={rname!r} value={rvalue!r} checked={checked}")
            except Exception:
                continue
    else:
        print("Nenhum input[type=radio] encontrado na tela.")

    raise RuntimeError(
        f"Não consegui marcar o nível de acesso '{rotulo}'. Veja a lista de rádios acima "
        "e ajuste config.SELECTORS['campo_nivel_acesso_" + nivel + "']."
    )


def selecionar_hipotese_legal(frame, texto: str, timeout_ms: int = 5000) -> None:
    """Seleciona a Hipótese Legal (campo <select> que aparece quando o
    nível de acesso é Restrito ou Sigiloso). `texto` casa por trecho
    contido na opção (ex.: "Informação Pessoal" casa com "Informação
    Pessoal (Art. 31 da Lei nº 12.527/2011)").
    """
    seletor = config.SELECTORS.get("campo_hipotese_legal")
    if seletor:
        try:
            loc = frame.locator(seletor)
            loc.wait_for(state="visible", timeout=timeout_ms)

            correspondente = None
            tentativas = max(1, timeout_ms // 300)
            for _ in range(tentativas):
                opcoes = loc.locator("option").all_inner_texts()
                correspondente = next((o for o in opcoes if texto.lower() in o.lower()), None)
                if correspondente:
                    break
                frame.wait_for_timeout(300)

            if correspondente:
                frame.select_option(seletor, label=correspondente)
                return
        except Exception:
            pass

    selects = frame.locator("select")
    total = selects.count()
    print(f"\nNão consegui selecionar '{texto}' com o seletor {seletor!r}.")
    if total:
        print("Campos <select> encontrados na tela:")
        for i in range(total):
            item = selects.nth(i)
            try:
                sid = item.get_attribute("id") or ""
                sname = item.get_attribute("name") or ""
                opcoes = item.locator("option").all_inner_texts()
                print(f"  id={sid!r} name={sname!r} opcoes={opcoes}")
            except Exception:
                continue
    else:
        print("Nenhum <select> visível na tela.")

    raise RuntimeError(
        f"Não encontrei a Hipótese Legal '{texto}'. Ajuste "
        "config.SELECTORS['campo_hipotese_legal'] com o id certo (veja lista acima)."
    )


def documento_existe_na_arvore(page: Page, texto: str, timeout_ms: int = 4000) -> bool:
    """Verifica se já existe, na árvore do processo atualmente aberto, um
    documento cujo nome contenha `texto` (comparação parcial, ignorando
    maiúsculas/minúsculas e diferenças de espaço).

    Restrito aos links (<a>) da página — os itens da árvore são sempre
    links — em vez do texto inteiro do body, pra não dar falso positivo com
    o conteúdo do PDF exibido na tela de visualização do documento. Procura
    em todos os frames (a árvore normalmente fica num iframe separado do
    conteúdo principal) e tenta algumas vezes, já que pode carregar de
    forma assíncrona.

    Compara só os primeiros 35 caracteres de `texto`: o SEI parece truncar
    nomes longos no "Nome na Árvore" — 35 caracteres já é suficiente pra
    distinguir os documentos usados neste projeto entre si.
    """
    alvo = re.sub(r"\s+", " ", texto).strip().lower()[:35]
    tentativas = max(1, timeout_ms // 400)

    for _ in range(tentativas):
        for fr in page.frames:
            try:
                links = fr.locator("a")
                candidatos = links.all_inner_texts()
                candidatos += links.evaluate_all(
                    "els => els.map(e => e.getAttribute('title') || '')"
                )
            except Exception:
                continue
            for candidato in candidatos:
                if alvo in re.sub(r"\s+", " ", candidato).strip().lower():
                    return True
        page.wait_for_timeout(400)

    return False


def localizar_campo_pesquisa(page: Page):
    """Procura o campo de pesquisa (placeholder "Pesquisar...") em todos os
    frames da página — o SEI costuma colocar a barra de topo num frame
    separado do conteúdo principal, então não dá pra assumir que está na
    página principal.
    """
    for fr in page.frames:
        candidatos = [
            fr.get_by_placeholder("Pesquisar", exact=False),
            fr.locator("input[placeholder*='Pesquisar' i]"),
        ]
        for loc in candidatos:
            try:
                if loc.count() > 0 and loc.first.is_visible():
                    return loc.first
            except Exception:
                continue
    return None


def clicar_por_texto_ou_icone(page: Page, texto: str) -> bool:
    """Clica em um item de menu/ícone localizando-o pelo texto visível ou,
    se não achar, pelo ícone associado (img/title/aria-label com o mesmo
    texto). Procura em todos os frames — mesma lógica usada em
    sei-automacao/automatizaçao_PDF pra navegar entre telas do SEI (ex.:
    "Controle de Processos"). Retorna True se conseguiu clicar.
    """
    for fr in page.frames:
        candidatos = [
            fr.get_by_text(texto, exact=True),
            fr.locator(f"a:has-text('{texto}')"),
            fr.locator(f"img[alt='{texto}'], img[title='{texto}']"),
            fr.locator(f"[title='{texto}']"),
            fr.get_by_text(texto, exact=False),
            fr.locator(f"[title*='{texto}' i]"),
            fr.locator(f"[aria-label*='{texto}' i]"),
            fr.locator(f"img[alt*='{texto}' i]"),
        ]
        for loc in candidatos:
            try:
                if loc.count() > 0 and loc.first.is_visible():
                    loc.first.click()
                    return True
            except Exception:
                continue
    return False


def pesquisar_processo(page: Page, numero_processo: str) -> None:
    """Digita o número do processo no campo de pesquisa do topo e confirma
    com Enter. Assume que a tela atual é a de Controle de Processos (ou
    qualquer tela com a barra de pesquisa visível)."""
    campo = localizar_campo_pesquisa(page)
    if campo is None:
        raise RuntimeError(
            "Não encontrei o campo de pesquisa (placeholder 'Pesquisar...') "
            "em nenhum frame da página."
        )
    campo.click()
    campo.fill(numero_processo)
    campo.press("Enter")
    page.wait_for_timeout(2000)  # espera o processo abrir


def sair_do_processo(page: Page) -> None:
    """Clica no menu "Controle de Processos" pra sair da tela do processo
    atual e voltar pra lista — chamado depois de terminar com um processo,
    antes de pesquisar o próximo."""
    if not clicar_por_texto_ou_icone(page, "Controle de Processos"):
        raise RuntimeError(
            "Não encontrei o menu 'Controle de Processos' pra voltar à tela inicial."
        )
    page.wait_for_timeout(1000)


def screenshot(page: Page, nome: str) -> None:
    config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    caminho = config.SCREENSHOTS_DIR / f"{nome}.png"
    page.screenshot(path=str(caminho), full_page=True)


def esperar_carregar(page: Page, timeout_ms: int = 2_500) -> None:
    """Espera a página "assentar" após uma navegação/ação, sem travar.

    O SEI mantém requisições de fundo (polling/heartbeat) que quase nunca
    deixam a rede ficar totalmente ociosa — por isso `networkidle` quase
    sempre estoura o timeout mesmo com a tela já pronta para uso. Por isso o
    timeout aqui é bem curto: só serve pra pegar de graça os casos em que a
    rede realmente fica ociosa rápido; no caso comum (não fica), cai direto
    na pausa fixa pequena em vez de ficar parado esperando à toa.
    """
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        page.wait_for_timeout(800)
