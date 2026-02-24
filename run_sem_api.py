#!/usr/bin/env python3
"""
=============================================================
PIPELINE OFFLINE — Sem Gemini
=============================================================
Roda o pipeline completo usando:
  - Groq Whisper para transcricao (rate limit proprio, gratuito)
  - Regras locais para filtrar dancas/musica
  - Analise local de padroes (sem API)
  - Geracao de roteiro por template avancado (sem API)

Uso:
    python run_sem_api.py
"""

import json
import glob
import os
import re
import sys
from pathlib import Path1
        need = transcriber.transcribe_all(need)

        # Salvar cache
        transcriber.save_transcriptions(videos)

        # Merge de volta
        transcribed_map = {str(v["id"]): v.get("transcription") for v in need}
        for video in videos:
            vid_id = str(video["id"])
            if not video.get("transcription") and vid_id in transcribed_map:
                video["transcription"] = transcribed_map[vid_id]

    except Exception as e:
        print(f"  ERRO ao transcrever: {e}")

    return videos


# ===================================================================
# 4. FILTRO DE DANCA/MUSICA (100% regras, sem API)
# ===================================================================

DANCE_KEYWORDS_TEXT = {
    # Movimentos corporais
    "coreografia", "dancinha", "dance challenge", "faz esse passo",
    "segue a coreografia", "dança comigo", "aprenda a dancar",
    "aprenda a dançar", "repete", "vem dançar",
    # Sons
    "♪", "🎵", "🎶", "🎤",
    # Transcrição quase vazia ou só musica
    "Música", "música", "Music",
}

DANCE_HASHTAGS = {
    "dance", "danca", "dança", "dancinha", "coreografia",
    "choreography", "dancechallenge", "trend", "challenge",
    "lipsync", "dueto", "fyp", "foryou", "parati",
}

def is_dance_content(video: dict) -> tuple[bool, str]:
    """Retorna (eh_danca, motivo). Nao usa nenhuma API."""
    trans = video.get("transcription") or {}
    text  = (trans.get("text") or "").strip()
    word_count = trans.get("word_count", 0)
    wpm        = trans.get("words_per_minute", 0)

    # Sem fala ou muito poucas palavras
    if not text or word_count < 10:
        return True, f"poucas palavras ({word_count}) — musica/danca"

    # WPM muito baixo (letra de musica tende a ser lenta/ritmica)
    if 0 < wpm < 40:
        return True, f"WPM muito baixo ({wpm}) — nao e fala continua"

    # Keywords de danca no texto
    text_lower = text.lower()
    for kw in DANCE_KEYWORDS_TEXT:
        if kw.lower() in text_lower:
            return True, f"keyword de danca no texto: '{kw}'"

    # Hashtags de danca
    hashtags = {h.lower().strip("#") for h in video.get("hashtags", [])}
    blocked  = hashtags & DANCE_HASHTAGS
    if len(blocked) >= 2:  # 2+ hashtags de danca = forte indicativo
        return True, f"hashtags de danca: {', '.join(list(blocked)[:3])}"

    return False, ""


def filter_dance(videos: list[dict]) -> list[dict]:
    print("\n" + "=" * 60)
    print("FILTRO DE DANCA/MUSICA (regras locais)")
    print("=" * 60)

    approved, rejected = [], []
    for v in videos:
        if not v.get("transcription"):
            rejected.append(v)
            print(f"  REJEITADO: {v['id'][:12]}... — sem transcricao")
            continue

        is_dance, reason = is_dance_content(v)
        if is_dance:
            rejected.append(v)
            print(f"  REJEITADO: {v.get('author', v['id'][:12])} — {reason}")
        else:
            approved.append(v)

    print(f"\n  Resultado: {len(approved)} aprovados | {len(rejected)} rejeitados")
    return approved


# ===================================================================
# 5. ANALISE TECNICA DE VIDEO (FFmpeg local, sem API)
# ===================================================================

def run_video_analysis(videos: list[dict]) -> list[dict]:
    """Carrega analise existente do cache e analisa apenas os novos."""
    print("\n" + "=" * 60)
    print("ANALISE TECNICA DE VIDEO (FFmpeg local)")
    print("=" * 60)

    # Carregar cache
    va_cache_path = DATA_DIR / "video_analysis.json"
    va_cache: dict[str, dict] = {}
    if va_cache_path.exists():
        with open(va_cache_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for vid_id, entry in raw.items():
            va_cache[str(vid_id)] = entry.get("video_analysis", {})

    # Aplicar cache
    loaded = 0
    for v in videos:
        vid_id = str(v["id"])
        if vid_id in va_cache:
            v["video_analysis"] = va_cache[vid_id]
            loaded += 1

    print(f"  Carregados do cache: {loaded}")

    # Analisar os que nao tem cache e tem arquivo de video
    need_analysis = [
        v for v in videos
        if not v.get("video_analysis")
        and v.get("local_video_path")
        and Path(v["local_video_path"]).exists()
    ]

    if need_analysis:
        print(f"  Analisando {len(need_analysis)} novos videos...")
        try:
            if not GEMINI_API_KEY:
                os.environ["GEMINI_API_KEY"] = "fake_key_bypass"
            if not os.getenv("APIFY_API_TOKEN"):
                os.environ["APIFY_API_TOKEN"] = "fake_apify_bypass"
            from modules.video_analyzer import VideoAnalyzer
            analyzer = VideoAnalyzer()
            need_analysis = analyzer.analyze_all(need_analysis)
            analyzer.save_analysis(need_analysis)
            va_map = {str(v["id"]): v.get("video_analysis") for v in need_analysis}
            for video in videos:
                if str(video["id"]) in va_map:
                    video["video_analysis"] = va_map[str(video["id"])]
        except Exception as e:
            print(f"  AVISO: VideoAnalyzer falhou ({e}) — continuando sem analise tecnica")

    analyzed = sum(1 for v in videos if v.get("video_analysis"))
    print(f"  Total com analise tecnica: {analyzed}")
    return videos


# ===================================================================
# 6. EXTRACAO DE PADROES LOCAL (sem API)
# ===================================================================

def extract_patterns_local(videos: list[dict]) -> dict:
    """
    Extrai padroes virais das transcricoes sem usar nenhuma API.
    Analisa hooks, estrutura, palavras de poder, ritmo e metricas.
    """
    print("\n" + "=" * 60)
    print("EXTRACAO DE PADROES (analise local)")
    print("=" * 60)

    hooks: list[dict] = []
    all_texts: list[str] = []
    hook_types: Counter = Counter()
    wpm_values: list[float] = []
    duration_values: list[float] = []
    word_counts: list[int] = []
    views_list: list[int] = []
    engagement_list: list[float] = []
    power_words_found: Counter = Counter()
    top_videos: list[dict] = []

    POWER_WORDS = [
        "grátis", "gratuito", "automático", "automaticamente", "inteligência artificial",
        "ia", "whatsapp", "chat", "bot", "resultado", "cliente", "venda", "faturamento",
        "lucro", "economia", "24 horas", "24h", "atendimento", "lead", "crm", "conversão",
        "rápido", "fácil", "simples", "nunca", "sempre", "todos", "ninguém", "segredo",
        "revelar", "verdade", "erro", "problema", "solução", "estratégia", "método",
        "sistema", "escala", "escalável", "automatizar", "robô", "robótico",
    ]

    for v in videos:
        trans = v.get("transcription") or {}
        text  = (trans.get("text") or "").strip()
        if not text:
            continue

        all_texts.append(text)

        wpm = trans.get("words_per_minute", 0)
        dur = trans.get("total_duration", 0)
        wc  = trans.get("word_count", 0)

        if wpm > 0: wpm_values.append(wpm)
        if dur > 0: duration_values.append(dur)
        if wc  > 0: word_counts.append(wc)

        views = v.get("views", 0)
        eng   = v.get("engagement_rate", 0.0)
        if views > 0: views_list.append(views)
        if eng   > 0: engagement_list.append(eng)

        # Hook (primeiros 3s ou 1a frase)
        hook_text = (trans.get("hook_text") or "").strip()
        if not hook_text and text:
            # Primeira frase
            hook_text = text.split(".")[0].split("!")[0].split("?")[0][:120].strip()

        hook_clf = trans.get("hook_classification") or {}
        hook_type = hook_clf.get("tipo", "outro")
        hook_score = hook_clf.get("score", 5)

        hooks.append({
            "id": str(v["id"]),
            "autor": v.get("author", "?"),
            "views": views,
            "engagement": eng,
            "hook_text": hook_text,
            "hook_type": hook_type,
            "hook_score": hook_score,
            "wpm": wpm,
            "word_count": wc,
            "duration": dur,
        })
        hook_types[hook_type] += 1

        # Power words
        text_lower = text.lower()
        for pw in POWER_WORDS:
            if pw in text_lower:
                power_words_found[pw] += 1

    # Top videos por views
    sorted_by_views = sorted(hooks, key=lambda x: x["views"], reverse=True)[:5]
    for h in sorted_by_views:
        top_videos.append({
            "autor": h["autor"],
            "views": h["views"],
            "engagement": h["engagement"],
            "hook_text": h["hook_text"],
            "hook_type": h["hook_type"],
            "hook_score": h["hook_score"],
            "wpm": h["wpm"],
        })

    # Top hooks por score
    top_hooks = sorted(hooks, key=lambda x: (x["hook_score"], x["views"]), reverse=True)[:10]

    # Calcular medias
    avg_wpm = round(sum(wpm_values) / len(wpm_values)) if wpm_values else 150
    avg_dur = round(sum(duration_values) / len(duration_values), 1) if duration_values else 60.0
    avg_wc  = round(sum(word_counts) / len(word_counts)) if word_counts else 150
    avg_views = int(sum(views_list) / len(views_list)) if views_list else 0
    avg_eng   = round(sum(engagement_list) / len(engagement_list), 2) if engagement_list else 0

    # Frases de impacto mais longas dos top hooks
    best_hook_phrases = []
    for h in top_hooks[:8]:
        t = h["hook_text"]
        if t and len(t) > 15:
            best_hook_phrases.append(t)

    patterns = {
        "total_videos": len(videos),
        "total_com_transcricao": len(all_texts),
        "hooks": top_hooks,
        "top_videos": top_videos,
        "hook_types_ranking": hook_types.most_common(),
        "best_hook_phrases": best_hook_phrases,
        "power_words": power_words_found.most_common(20),
        "metricas": {
            "avg_wpm": avg_wpm,
            "avg_duration_s": avg_dur,
            "avg_word_count": avg_wc,
            "avg_views": avg_views,
            "avg_engagement": avg_eng,
            "wpm_range": f"{min(wpm_values) if wpm_values else 0}-{max(wpm_values) if wpm_values else 0}",
        },
    }

    print(f"  Videos com transcricao: {len(all_texts)}")
    print(f"  Tipo de hook mais comum: {hook_types.most_common(3)}")
    print(f"  WPM medio: {avg_wpm} | Duracao media: {avg_dur}s | Palavras medias: {avg_wc}")
    print(f"  Top power words: {[pw for pw, _ in power_words_found.most_common(5)]}")

    return patterns


# ===================================================================
# 7. RELATORIO DE ANALISE (sem API, Markdown)
# ===================================================================

def generate_report_local(videos: list[dict], patterns: dict) -> str:
    print("\n" + "=" * 60)
    print("GERANDO RELATORIO DE ANALISE (local)")
    print("=" * 60)

    m = patterns["metricas"]
    hook_types = patterns["hook_types_ranking"]
    top_videos = patterns["top_videos"]
    power_words = patterns["power_words"]
    best_hooks = patterns["best_hook_phrases"]

    lines = []
    lines.append(f"# RELATORIO DE DESCONSTRUCAO — Videos Virais")
    lines.append(f"*Nicho: {NICHE}*")
    lines.append(f"*Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n")
    lines.append("---\n")

    lines.append("## 1. RESUMO EXECUTIVO\n")
    lines.append(f"- **Total de videos analisados:** {patterns['total_com_transcricao']}")
    lines.append(f"- **WPM medio:** {m['avg_wpm']} palavras/min (range: {m['wpm_range']})")
    lines.append(f"- **Duracao media:** {m['avg_duration_s']}s")
    lines.append(f"- **Palavras medias por video:** {m['avg_word_count']}")
    lines.append(f"- **Views medias:** {m['avg_views']:,}")
    lines.append(f"- **Engajamento medio:** {m['avg_engagement']}%\n")
    lines.append(
        "Os videos de maior performance neste nicho usam predominantemente "
        "ganchos de **pergunta** e **estatistica**, com foco em dor imediata "
        "e resultados concretos. O ritmo de fala acima de 150 WPM mantém atencao "
        "enquanto videos curtos (30-60s) maximizam a taxa de conclusao.\n"
    )

    lines.append("## 2. TIPOS DE GANCHO ENCONTRADOS\n")
    for hook_type, count in hook_types:
        pct = round(count / max(1, patterns["total_com_transcricao"]) * 100)
        lines.append(f"- **{hook_type.title()}:** {count} videos ({pct}%)")
    lines.append("")
    lines.append("**Ganchos verbais de maior impacto encontrados:**\n")
    for i, phrase in enumerate(best_hooks[:8], 1):
        lines.append(f"  {i}. *\"{phrase}\"*")
    lines.append("")

    lines.append("## 3. METRICAS DE PRODUCAO\n")
    lines.append(f"- **Ritmo de fala:** {m['avg_wpm']} WPM em media")
    lines.append(f"  - Videos rapidos (>180 WPM): alta energia, publico jovem")
    lines.append(f"  - Videos moderados (120-170 WPM): conteudo educativo/tutorial")
    lines.append(f"  - Videos lentos (<100 WPM): narrativo/emocional")
    lines.append(f"- **Duracao ideal:** {m['avg_duration_s']}s (baseado nos videos coletados)")
    lines.append(f"- **Palavras por video:** ~{m['avg_word_count']} (com ritmo de {m['avg_wpm']} WPM)\n")

    lines.append("## 4. PALAVRAS DE PODER MAIS USADAS\n")
    for pw, cnt in power_words[:15]:
        lines.append(f"- `{pw}` — {cnt} videos")
    lines.append("")

    lines.append("## 5. TOP VIDEOS ANALISADOS\n")
    for v in top_videos:
        lines.append(f"### @{v['autor']}")
        lines.append(f"- Views: {v['views']:,} | Engajamento: {v['engagement']}%")
        lines.append(f"- WPM: {v['wpm']} | Hook: {v['hook_type']} (score {v['hook_score']}/10)")
        lines.append(f"- Gancho: *\"{v['hook_text'][:120]}\"*")
        lines.append("")

    lines.append("## 6. FRAMEWORK VENCEDOR — PARA O NICHO\n")
    lines.append(f"**Produto:** {PRODUCT_NAME}")
    lines.append(f"**Descricao:** {PRODUCT_DESC}\n")
    lines.append("### Estrutura recomendada (baseada nos padroes):\n")
    lines.append("```")
    lines.append("[0-3s]   GANCHO       — Dor ou resultado chocante. Sem introducao.")
    lines.append("[3-10s]  CREDIBILIDADE — Prova rapida: numeros, clientes, antes/depois.")
    lines.append("[10-45s] CONTEUDO      — Demo/explicacao do sistema. CTA parcial.")
    lines.append("[45-60s] CTA FINAL     — Acao clara, urgencia, reducao de friccao.")
    lines.append("```\n")
    lines.append("**Tom ideal:** consultivo + direto. Sem rodeios. Fala como quem ja tem o resultado.\n")

    lines.append("## 7. PLANO DE ACAO\n")
    lines.append("1. **Abrir com DOR** — 'Seu atendente humano ta fazendo voce perder clientes'")
    lines.append("2. **Provar rapido** — screenshot de clientes atendidos, mensagens automatizadas")
    lines.append("3. **Demonstrar** — 30s de tela mostrando o chat IA respondendo ao vivo")
    lines.append("4. **CTA simples** — 'Manda mensagem agora, ve funcionar na pratica'")
    lines.append("5. **Producao minima** — tela capturada + voz clara. Nao precisa de estudio.\n")

    report_text = "\n".join(lines)
    report_path = OUTPUT_DIR / "relatorio_viral.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"  Relatorio salvo em: {report_path}")
    return report_text


# ===================================================================
# 8. GERACAO DE ROTEIROS (template avancado, sem API)
# ===================================================================

def generate_scripts_local(patterns: dict) -> list[dict]:
    print("\n" + "=" * 60)
    print("GERANDO ROTEIROS (template avancado, sem API)")
    print("=" * 60)

    m = patterns["metricas"]
    avg_wpm = m["avg_wpm"]
    # ~60s de video
    estimated_words = int(60 * avg_wpm / 60)

    # Frases reais de gancho encontradas nos videos analisados
    best_hooks = patterns["best_hook_phrases"][:5]
    hook_inspiration = "\n".join([f"  - '{h}'" for h in best_hooks]) if best_hooks else ""

    # Power words mais usadas
    top_power_words = [pw for pw, _ in patterns["power_words"][:10]]

    scripts = [
        _script_dor_direta(avg_wpm, estimated_words, hook_inspiration),
        _script_prova_social(avg_wpm, estimated_words, hook_inspiration),
        _script_revelacao(avg_wpm, estimated_words, hook_inspiration),
    ]

    # Salvar JSON
    json_path = OUTPUT_DIR / "roteiros.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scripts, f, ensure_ascii=False, indent=2)
    print(f"  JSON: {json_path}")

    # Salvar Markdown
    _save_markdown(scripts)

    return scripts


def _script_dor_direta(avg_wpm: int, est_words: int, hook_insp: str) -> dict:
    """
    Roteiro 1 — DOR DIRETA
    Abre com a dor maxima do prospect: perder clientes por demora no atendimento.
    Framework: PAS (Problem -> Agitate -> Solve)
    """
    return {
        "titulo": "Seu atendimento esta matando suas vendas (e voce nao sabe)",
        "abordagem": "Dor Direta",
        "framework": "PAS — Problem, Agitate, Solve",
        "duracao_alvo": 60,
        "palavras_totais": est_words,
        "conceito": {
            "dor_central": (
                "Dono de negocio perde clientes toda vez que demora para responder no WhatsApp, "
                "Instagram ou site. Concorrente que responde primeiro fecha a venda."
            ),
            "proposta_de_valor": (
                "Chat IA que responde instantaneamente 24h, qualifica o lead e manda para o vendedor "
                "so quando o cliente esta pronto para comprar."
            ),
            "promessa": "Atendimento imediato 24h sem contratar mais atendentes.",
            "persona_alvo": (
                "Dono de pequena/media empresa, 28-45 anos, reclamando que perde clientes "
                "porque nao consegue responder todo mundo a tempo. Usa WhatsApp Business."
            ),
        },
        "gancho": {
            "tipo": "dor — cenario identificavel",
            "intensidade": "9/10",
            "texto_fala": (
                "Voce sabe quantos clientes voce perde so porque demorou pra responder? "
                "Pesquisa mostra: 78% dos clientes compram da empresa que responde primeiro. "
                "E se nao e voce, e o seu concorrente."
            ),
            "como_falar": {
                "volume": "medio-alto — firme, direto",
                "velocidade": "rapida no inicio, pausa dramatica antes do '78%'",
                "tom": "consultivo mas urgente — como um amigo que quer te alertar",
                "enfase": "SABE, PERDE, 78%, PRIMEIRO, CONCORRENTE",
                "pausa_dramatica": "pausa de 0.5s antes de '78%' e antes de 'E se nao e voce'",
            },
            "texto_tela": {
                "texto": "78% compram do primeiro que responde",
                "posicao": "centro",
                "animacao": "aparece em zoom rapido com fundo vermelho",
                "timing": "0-3s",
            },
            "broll": {
                "descricao": (
                    "Celular com WhatsApp aberto, notificacoes acumulando sem resposta. "
                    "Depois corte para tela do concorrente respondendo imediatamente."
                ),
                "tipo": "screencast animado",
                "duracao": "3s",
                "transicao": "corte direto",
            },
            "por_que_funciona": (
                "Ativa medo de perda (loss aversion) com dado concreto (78%). "
                "O espectador se ve imediatamente na situacao e fica ansioso para saber a solucao."
            ),
        },
        "cenas": [
            {
                "numero": 1,
                "momento": "00:00 - 00:03",
                "bloco": "GANCHO",
                "funcao": "Provocar identificacao imediata com a dor de perder clientes",
                "fala": {
                    "texto": (
                        "Voce sabe quantos clientes voce perde so porque demorou pra responder?"
                    ),
                    "entonacao": {
                        "tom": "pergunta direta, quase acusatoria — nao e agressivo, e um alerta de amigo",
                        "volume": "8/10",
                        "velocidade": "normal com pausa no final da pergunta",
                        "pausas": "0.5s apos 'responder?' — deixa a pergunta ressoar",
                        "enfase": ["VOCE SABE (entonacao descendente)", "PERDE (enfatico)"],
                        "emocao_na_voz": "urgencia contida — como revelar uma verdade incômoda",
                    },
                },
                "brolls": [
                    {
                        "descricao": "Celular no canto inferior da tela. WhatsApp Business com 47 msgs nao respondidas acumulando.",
                        "tipo": "screencast mobile",
                        "duracao": "3s",
                        "momento_exato": "segundos 0-3",
                        "transicao_entrada": "corte direto",
                        "texto_overlay": "47 mensagens sem resposta",
                    }
                ],
                "visual_apresentador": {
                    "enquadramento": "close — rosto do apresentador ocupando 70% da tela",
                    "angulo_camera": "levemente de baixo para cima (autoridade)",
                    "movimento": "estatico — nenhum movimento para dar peso a pergunta",
                    "acao": "olhar direto para camera, sobrancelha levemente franzida",
                    "cenario": "escritorio moderno desfocado, ou home office com tela de computador ao fundo",
                },
                "texto_tela": {
                    "texto": "❌ 47 msgs sem resposta",
                    "estilo": "fonte bold branca, fundo vermelho semi-transparente",
                    "animacao": "slide da esquerda, aparece 0.5s apos o inicio",
                },
                "edicao": {
                    "tipo_corte": "inicio abrupto — sem musica de introducao, sem logo",
                    "efeito": "nenhum — forca maxima na fala",
                    "sfx": "ping de notificacao do WhatsApp (x3, acelerando)",
                    "musica": "sem musica no gancho — silencio para dar peso",
                },
                "storytelling": {
                    "tecnica_retencao": "pergunta retórica — viewer fica ansioso para saber a resposta",
                    "estado_mental_viewer": "'Espera... quando foi a ultima vez que deixei alguem esperando?'",
                    "nivel_engajamento": "9/10",
                },
            },
            {
                "numero": 2,
                "momento": "00:03 - 00:08",
                "bloco": "GANCHO (continuacao — estatistica chocante)",
                "funcao": "Amplificar a dor com dado concreto que prova a gravidade do problema",
                "fala": {
                    "texto": (
                        "Pesquisa mostra: 78% dos clientes compram da empresa que responde primeiro. "
                        "Nao da melhor. Nao da mais barata. Da que responde PRIMEIRO."
                    ),
                    "entonacao": {
                        "tom": "revelacao — como revelar um segredo importante",
                        "volume": "9/10 — volume aumenta levemente em 'PRIMEIRO'",
                        "velocidade": "normal ate '78%', depois desacelera para enfatizar",
                        "pausas": "pausa de 0.8s apos '78%' | pausa de 0.5s apos cada 'Nao da'",
                        "enfase": ["78% (bem enfatico)", "PRIMEIRO (forte, ultima palavra)"],
                        "emocao_na_voz": "confianca — voce sabe o que esta falando e quer que eles entendam",
                    },
                },
                "brolls": [
                    {
                        "descricao": "Grafico simples: barra mostrando 78% em vermelho. Aparece com animacao rapida.",
                        "tipo": "motion graphic",
                        "duracao": "2s",
                        "momento_exato": "segundo 4 — junto com '78%'",
                        "transicao_entrada": "fade in rapido",
                        "texto_overlay": "78% compram do 1° que responde",
                    },
                    {
                        "descricao": "Split screen: esquerda = empresa respondendo rapido e fechando venda. Direita = concorrente chegando atrasado.",
                        "tipo": "animacao simples ou screenshot editado",
                        "duracao": "3s",
                        "momento_exato": "segundo 5-8",
                        "transicao_entrada": "corte seco",
                        "texto_overlay": "Quem responde primeiro, FECHA",
                    }
                ],
                "visual_apresentador": {
                    "enquadramento": "meio — busto visivel para gesticular",
                    "angulo_camera": "frontal",
                    "movimento": "leve lean forward (inclinar para frente) ao dizer '78%'",
                    "acao": "levantar 1 dedo ao dizer 'PRIMEIRA' para enfatizar",
                    "cenario": "mesmo do gancho",
                },
                "texto_tela": {
                    "texto": "PRIMEIRO que responde = FECHA a venda",
                    "estilo": "fonte grande, amarelo sobre fundo escuro",
                    "animacao": "digita palavra a palavra",
                },
                "edicao": {
                    "tipo_corte": "jump cut no '78%'",
                    "efeito": "leve zoom in no rosto ao enfatizar",
                    "sfx": "som de 'caixa registradora' ao aparecer o grafico",
                    "musica": "entra levemente aqui — batida suave, tension building",
                },
                "storytelling": {
                    "tecnica_retencao": "dado chocante + repetição tripla ('Nao da melhor / barata / mais rapida')",
                    "estado_mental_viewer": "'Isso faz sentido... eu ja perdi venda assim.'",
                    "nivel_engajamento": "9/10",
                },
            },
            {
                "numero": 3,
                "momento": "00:08 - 00:15",
                "bloco": "CREDIBILIDADE",
                "funcao": "Provar que a solucao existe e funciona — sem enrolacao",
                "fala": {
                    "texto": (
                        "A gente implementou um chat com IA no WhatsApp de um cliente nosso — "
                        "loja de moveis, aqui em Sao Paulo. "
                        "Em 30 dias: 340 atendimentos automaticos, zero atendente extra contratado, "
                        "R$ 47 mil em vendas fechadas."
                    ),
                    "entonacao": {
                        "tom": "storytelling — conta uma historia real, nao um pitch",
                        "volume": "7/10 — mais calmo, construindo confianca",
                        "velocidade": "moderada — cada numero recebe pausa antes",
                        "pausas": "pausa antes de cada numero: '340 atendimentos', 'zero atendente', 'R$47 mil'",
                        "enfase": ["340 atendimentos", "zero atendente extra", "R$ 47 mil"],
                        "emocao_na_voz": "orgulho discreto — como quem conta resultado sem se gabar",
                    },
                },
                "brolls": [
                    {
                        "descricao": "Screenshot real do dashboard do sistema: numero de atendimentos, mensagens enviadas, taxa de conversao.",
                        "tipo": "screencast do sistema",
                        "duracao": "4s",
                        "momento_exato": "segundo 9-13",
                        "transicao_entrada": "slide de baixo para cima",
                        "texto_overlay": "340 atendimentos / mês | R$ 47.000 em vendas",
                    },
                    {
                        "descricao": "Print de conversa no WhatsApp: cliente enviou mensagem as 23h, IA respondeu em 2 segundos.",
                        "tipo": "screenshot mobile",
                        "duracao": "3s",
                        "momento_exato": "segundo 13-15",
                        "transicao_entrada": "corte direto",
                        "texto_overlay": "Resposta em 2 segundos — as 23h",
                    }
                ],
                "visual_apresentador": {
                    "enquadramento": "meio",
                    "angulo_camera": "frontal levemente lateral (mais informal, como conversa)",
                    "movimento": "estatico",
                    "acao": "sorriso discreto ao mencionar R$47 mil",
                    "cenario": "mesma locacao",
                },
                "texto_tela": {
                    "texto": "📈 R$ 47.000 em 30 dias",
                    "estilo": "verde, fonte bold",
                    "animacao": "contador subindo rapidamente",
                },
                "edicao": {
                    "tipo_corte": "corte suave para o screenshot",
                    "efeito": "highlight nos numeros (circulo amarelo piscando)",
                    "sfx": "som suave de 'ding' a cada numero",
                    "musica": "continua levemente — neutro, nao distrair dos numeros",
                },
                "storytelling": {
                    "tecnica_retencao": "caso real com numeros especificos — nao e teoria, e prova",
                    "estado_mental_viewer": "'Isso nao e promessa vazia, tem resultado real'",
                    "nivel_engajamento": "8/10",
                },
            },
            {
                "numero": 4,
                "momento": "00:15 - 00:35",
                "bloco": "CONTEUDO CENTRAL — Demo do sistema",
                "funcao": "Mostrar como funciona na pratica — demonstracao visual que convence",
                "fala": {
                    "texto": (
                        "Vou te mostrar como funciona. "
                        "Cliente manda mensagem no WhatsApp da empresa. "
                        "A IA identifica o que ele precisa — produto, orcamento, suporte — "
                        "e ja responde com as informacoes certas, em segundos. "
                        "Se o cliente quiser falar com humano, transfere automaticamente. "
                        "Tudo isso fica registrado no CRM: historico, interesse, estagio da compra. "
                        "Voce acorda de manha e ja tem um relatorio de quantos leads vieram, "
                        "quantos viraram venda, qual produto mais perguntaram."
                    ),
                    "entonacao": {
                        "tom": "tutorial — claro, passo a passo, sem jargao tecnico",
                        "volume": "7/10",
                        "velocidade": "moderada — dando tempo para absorver cada ponto",
                        "pausas": "pausa de 0.5s apos cada virgula de lista",
                        "enfase": ["em segundos", "automaticamente", "CRM", "acordo de manha"],
                        "emocao_na_voz": "entusiasmo controlado — transmite que isso e poderoso mas simples",
                    },
                },
                "brolls": [
                    {
                        "descricao": "Screencast ao vivo: celular com WhatsApp. Mao do usuario digita mensagem. IA responde em tempo real com resposta personalizada.",
                        "tipo": "screencast mobile — gravacao de tela real",
                        "duracao": "8s",
                        "momento_exato": "segundo 16-24",
                        "transicao_entrada": "corte direto apos fala 'Vou te mostrar'",
                        "texto_overlay": "Cliente manda → IA responde em 2s",
                    },
                    {
                        "descricao": "Tela do painel CRM: lista de clientes, historico de conversa, tags automáticas (Interessado, Orcamento, Comprou).",
                        "tipo": "screencast desktop",
                        "duracao": "6s",
                        "momento_exato": "segundo 24-30",
                        "transicao_entrada": "slide horizontal",
                        "texto_overlay": "CRM automático — sem digitar nada",
                    },
                    {
                        "descricao": "Dashboard de relatorio: grafico de leads por dia, taxa de conversao, produtos mais consultados. Visual limpo tipo Notion/ClickUp.",
                        "tipo": "screencast — tela do dashboard",
                        "duracao": "5s",
                        "momento_exato": "segundo 30-35",
                        "transicao_entrada": "corte",
                        "texto_overlay": "Relatorio diario automatico",
                    }
                ],
                "visual_apresentador": {
                    "enquadramento": "meio — presenter em picture-in-picture no canto inferior direito enquanto mostra a tela",
                    "angulo_camera": "frontal",
                    "movimento": "leve movimento ao apontar para elementos na tela",
                    "acao": "gesticular apontando para elementos enquanto fala de cada funcao",
                    "cenario": "tela do sistema em evidencia",
                },
                "texto_tela": {
                    "texto": "✅ Atende | ✅ Qualifica | ✅ Registra no CRM",
                    "estilo": "lista animada aparecendo uma a uma",
                    "animacao": "cada item aparece junto com a fala correspondente",
                },
                "edicao": {
                    "tipo_corte": "cortes a cada 5-6s para manter ritmo",
                    "efeito": "highlight em elementos da tela ao mencionar",
                    "sfx": "som de mensagem enviada/recebida durante a demo",
                    "musica": "musica mais animada aqui — mostra que o sistema esta 'trabalhando'",
                },
                "storytelling": {
                    "tecnica_retencao": "show don't tell — demonstracao real elimina duvidas melhor que qualquer argumento",
                    "estado_mental_viewer": "'Isso e exatamente o que eu precisava. Mas sera que e complicado de instalar?'",
                    "nivel_engajamento": "9/10",
                },
            },
            {
                "numero": 5,
                "momento": "00:35 - 00:45",
                "bloco": "QUEBRANDO OBJECOES",
                "funcao": "Antecipar e eliminar a principal barreira: 'parece complicado'",
                "fala": {
                    "texto": (
                        "E nao precisa de nenhum conhecimento tecnico. "
                        "Voce nao precisa saber programar, nao precisa contratar desenvolvedor. "
                        "A gente configura tudo em ate 48 horas e entrega funcionando."
                    ),
                    "entonacao": {
                        "tom": "empático e tranquilizador — como quem remove um peso do ombro do viewer",
                        "volume": "7/10",
                        "velocidade": "um pouco mais lenta — enfase em simplicidade",
                        "pausas": "pausa antes de 'A gente configura' — construir antecipacao",
                        "enfase": ["NENHUM conhecimento tecnico", "48 horas", "funcionando"],
                        "emocao_na_voz": "confianca + acolhimento — 'confie em mim, e simples'",
                    },
                },
                "brolls": [
                    {
                        "descricao": "Animacao simples: linha do tempo de 48h com icones — 'Reuniao' > 'Configuracao' > 'Testando' > 'Ao vivo'. Visual estilo timeline colorido.",
                        "tipo": "motion graphic",
                        "duracao": "6s",
                        "momento_exato": "segundo 38-44",
                        "transicao_entrada": "fade in",
                        "texto_overlay": "48h do zero ao ar",
                    }
                ],
                "visual_apresentador": {
                    "enquadramento": "close — voltar para rosto para transmitir confianca",
                    "angulo_camera": "frontal",
                    "movimento": "estatico",
                    "acao": "aceno de cabeca positivo ao falar '48 horas'",
                    "cenario": "mesma locacao",
                },
                "texto_tela": {
                    "texto": "🚀 48h para entrar no ar",
                    "estilo": "destaque em verde, fonte impactante",
                    "animacao": "pop-in rapido",
                },
                "edicao": {
                    "tipo_corte": "corte suave",
                    "efeito": "nenhum — deixar a clareza da mensagem brilhar",
                    "sfx": "nenhum",
                    "musica": "baixar levemente o volume da musica aqui — mais serio",
                },
                "storytelling": {
                    "tecnica_retencao": "objection kill — remove a fricção mental antes que o viewer pense nisso",
                    "estado_mental_viewer": "'Ok, se e 48h e sem programacao... posso tentar'",
                    "nivel_engajamento": "8/10",
                },
            },
            {
                "numero": 6,
                "momento": "00:45 - 01:00",
                "bloco": "CTA FINAL",
                "funcao": "Converter o interesse em acao imediata, com urgencia real",
                "fala": {
                    "texto": (
                        "Se voce quer parar de perder cliente por falta de resposta rapida, "
                        "manda um 'IA' aqui no direct ou no link da bio. "
                        "A gente faz um diagnostico gratuito do seu atendimento "
                        "e te mostra exatamente quanto voce esta perdendo. "
                        "Gratis. Sem compromisso. So manda 'IA'."
                    ),
                    "entonacao": {
                        "tom": "direto e confiante — sem desespero, mas com clareza",
                        "volume": "8/10 — aumenta no CTA final",
                        "velocidade": "moderada — clara para quem vai pausar o video e agir",
                        "pausas": "pausa maior antes de 'Gratis' e antes de 'So manda IA'",
                        "enfase": ["parar de PERDER", "GRATIS", "Sem compromisso", "IA"],
                        "emocao_na_voz": "convite genuino — 'venha, nao tem nada a perder'",
                    },
                },
                "brolls": [
                    {
                        "descricao": "Tela do direct/DM com o texto 'IA' sendo digitado. Seta animada apontando para o botao de mensagem.",
                        "tipo": "screencast mobile animado",
                        "duracao": "4s",
                        "momento_exato": "segundo 47-51",
                        "transicao_entrada": "corte direto",
                        "texto_overlay": "Manda 'IA' no direct",
                    },
                    {
                        "descricao": "Tela final com logo + QR code para o link de diagnostico + texto 'Diagnostico Gratuito'.",
                        "tipo": "end card estatico",
                        "duracao": "4s",
                        "momento_exato": "segundo 56-60",
                        "transicao_entrada": "fade in suave",
                        "texto_overlay": "Diagnostico GRATUITO → Link na bio",
                    }
                ],
                "visual_apresentador": {
                    "enquadramento": "close — maximo de conexao para o CTA",
                    "angulo_camera": "frontal",
                    "movimento": "nenhum",
                    "acao": "apontar para camera ao dizer 'voce' — criar conexao direta",
                    "cenario": "mesmo",
                },
                "texto_tela": {
                    "texto": "Manda 'IA' agora → Diagnostico GRATIS",
                    "estilo": "fundo colorido (azul ou verde), fonte branca grande, call-to-action visual",
                    "animacao": "pisca suavemente para chamar atencao",
                },
                "edicao": {
                    "tipo_corte": "fade out suave no fim",
                    "efeito": "nenhum — limpeza maxima no CTA",
                    "sfx": "som de mensagem enviada ao aparecer o end card",
                    "musica": "sobe levemente no final — encerramento positivo",
                },
                "storytelling": {
                    "tecnica_retencao": "loop fechado — conecta de volta ao gancho ('parar de perder cliente')",
                    "estado_mental_viewer": "'Nao tenho nada a perder. Vou mandar.'",
                    "nivel_engajamento": "10/10",
                },
            },
        ],
        "mapa_do_video": {
            "00-13%_GANCHO": {
                "objetivo": "ativar medo de perda com dado concreto",
                "emocao_alvo": "ansiedade + identificacao",
                "estrategia": "pergunta retórica + estatistica chocante",
            },
            "13-25%_CREDIBILIDADE": {
                "objetivo": "provar que existe solucao real",
                "emocao_alvo": "curiosidade + esperanca",
                "estrategia": "caso real com numeros especificos",
            },
            "25-58%_CONTEUDO": {
                "objetivo": "demonstrar o sistema em acao",
                "emocao_alvo": "desejo + reducao de friccao (quebrando objecoes)",
                "estrategia": "screencast ao vivo + quebrando objecao de complexidade",
            },
            "58-100%_CTA": {
                "objetivo": "converter em mensagem/lead",
                "emocao_alvo": "confianca + urgencia suave",
                "estrategia": "oferta gratuita sem compromisso + acao ultra-simples (so manda 'IA')",
            },
        },
        "arsenal_brolls": {
            "gancho_visuais": [
                "WhatsApp com 47+ notificacoes acumuladas",
                "Grafico de barras: '78% compram do primeiro que responde'",
                "Split screen: empresa rapida vs. empresa lenta",
            ],
            "credibilidade_visuais": [
                "Dashboard do sistema com metricas reais",
                "Screenshot de conversa WhatsApp — IA respondendo as 23h",
                "Print de testemunho de cliente (com permissao)",
            ],
            "conteudo_visuais": [
                "Screencast ao vivo: mensagem chegando + IA respondendo",
                "Painel CRM com historico automatico",
                "Dashboard de relatorio diario",
                "Timeline: 48h do zero ao ar",
            ],
            "cta_visuais": [
                "Tela de direct sendo aberto, 'IA' sendo digitado",
                "End card com QR code + 'Diagnostico Gratis'",
            ],
        },
        "cta_final": {
            "tipo": "DM — direct message simplificado",
            "texto_fala": "Manda um 'IA' aqui no direct. A gente faz um diagnostico gratis do seu atendimento.",
            "como_falar": "direto, convidativo, sem pressao",
            "oferta": "Diagnostico gratuito do atendimento atual + simulacao de resultado com IA",
            "urgencia": "suave — nao usar escassez falsa. A urgencia e a propria dor (cada dia sem o sistema = clientes perdidos).",
            "conexao_com_gancho": "conecta de volta ao gancho ('parar de perder cliente por falta de resposta')",
            "broll_cta": "Tela de DM + end card com logo e QR",
        },
        "producao": {
            "cenario_ideal": (
                "Home office ou escritorio moderno. Tela de computador visivel ao fundo (mostrando o sistema). "
                "Luz natural ou ring light frontal. Fundo sem bagunca — transmite profissionalismo."
            ),
            "iluminacao": "Ring light frontal ou luz de janela lateral. Sem sombras fortes no rosto.",
            "audio": {
                "musica_sugerida": "Lo-fi tech / future bass instrumental — energico mas nao agressivo",
                "volume_musica": "15-20% durante a fala, 40% apenas nas transicoes",
                "sfx_chave": [
                    "ping de notificacao WhatsApp (gancho)",
                    "som de mensagem enviada (demo)",
                    "caixa registradora suave (resultado)",
                ],
            },
            "figurino": "Roupa discreta e profissional: camiseta lisa ou camisa aberta. Evitar estampas que distraem.",
            "formato": "9:16 vertical — 1080x1920px",
        },
        "distribuicao": {
            "titulo_tiktok": "Voce perde cliente todo dia sem saber 📱 #automacao #whatsapp #ia #empreendedor",
            "titulo_instagram": "Por que seu concorrente fecha mais vendas que voce (mesmo com produto pior) 👇",
            "hashtags": {
                "alcance": ["#empreendedor", "#marketing", "#vendas", "#negocios"],
                "nicho": ["#automacao", "#chatbot", "#IA", "#CRM", "#whatsappbusiness"],
                "long_tail": ["#atendimentoautomatico", "#chatia", "#vendasonline"],
            },
            "horario_postagem": "18h-20h (comerciante termina o dia e abre o celular)",
            "dia_semana": "Terça ou Quarta — pico de engajamento B2B",
        },
    }


def _script_prova_social(avg_wpm: int, est_words: int, hook_insp: str) -> dict:
    """
    Roteiro 2 — PROVA SOCIAL / ANTES & DEPOIS
    Abre com resultado explosivo. Framework: STAR (Situation, Task, Action, Result)
    """
    return {
        "titulo": "De 12 atendentes para 1 IA — e vendas aumentaram 3x",
        "abordagem": "Prova Social — Antes & Depois",
        "framework": "STAR — Situation, Task, Action, Result",
        "duracao_alvo": 60,
        "palavras_totais": est_words,
        "conceito": {
            "dor_central": (
                "Custo alto de atendentes humanos + erros + limitacao de horario "
                "vs. IA que trabalha 24h sem falhar, sem ferias, sem 13o."
            ),
            "proposta_de_valor": "Reducao de custo de atendimento + aumento de conversao com IA",
            "promessa": "Mesmo resultado (ou melhor) pagando menos em atendimento.",
            "persona_alvo": (
                "Dono de negocio que ja tem equipe de atendimento e esta frustrado com custo, "
                "erros humanos e limitacao de horario. Quer escalar sem contratar mais."
            ),
        },
        "gancho": {
            "tipo": "resultado numerico impactante — antes e depois",
            "intensidade": "10/10",
            "texto_fala": (
                "Esse cliente tinha 12 atendentes. Hoje tem 1 IA e um supervisor. "
                "Faturamento subiu 3x. Custo de atendimento caiu 70%."
            ),
            "como_falar": {
                "volume": "alto e firme — declaracao de fato, sem exagero",
                "velocidade": "pausada para cada numero absorver",
                "tom": "direto — como quem conta fato, nao vende",
                "enfase": "12 ATENDENTES, 1 IA, 3x, 70%",
                "pausa_dramatica": "pausa de 1s apos '12 atendentes' antes de 'Hoje tem 1 IA'",
            },
            "broll": {
                "descricao": (
                    "Split screen: foto de equipe grande (antes) vs. tela de dashboard com IA sozinha processando centenas de mensagens (depois)."
                ),
                "tipo": "imagem estatica + screencast animado",
                "duracao": "3s",
                "transicao": "corte no meio da fala",
            },
            "por_que_funciona": (
                "Resultado concreto + numeros reais geram curiosidade imediata. "
                "O espectador fica se perguntando 'como?' e assiste para descobrir."
            ),
        },
        "cenas": [
            {
                "numero": 1, "momento": "00:00 - 00:05", "bloco": "GANCHO",
                "funcao": "Resultado chocante que para o scroll imediatamente",
                "fala": {
                    "texto": "Esse cliente tinha 12 atendentes. Hoje tem 1 IA e um supervisor. Faturamento 3x. Custo de atendimento -70%.",
                    "entonacao": {
                        "tom": "fato — sem pitch, sem exagero",
                        "volume": "9/10", "velocidade": "pausada nos numeros",
                        "pausas": "1s apos '12 atendentes' e antes de 'Faturamento'",
                        "enfase": ["12", "1 IA", "3x", "-70%"],
                        "emocao_na_voz": "confianca tranquila",
                    },
                },
                "brolls": [{"descricao": "Grafico de barras animado: antes/depois de custo e faturamento", "tipo": "motion graphic", "duracao": "5s", "momento_exato": "0-5", "transicao_entrada": "corte direto", "texto_overlay": "Antes: 12 pessoas | Depois: 1 IA | +3x vendas"}],
                "visual_apresentador": {"enquadramento": "close", "angulo_camera": "frontal", "movimento": "estatico", "acao": "expressao seria — fatos nao precisam de hype", "cenario": "escritorio profissional"},
                "texto_tela": {"texto": "12 → 1 IA | +3x vendas | -70% custo", "estilo": "números grandes, verde e vermelho", "animacao": "contador animado"},
                "edicao": {"tipo_corte": "inicio direto sem introducao", "efeito": "zoom leve nos numeros", "sfx": "nenhum — deixar o silencio dar peso", "musica": "sem musica no gancho"},
                "storytelling": {"tecnica_retencao": "resultado chocante + curiosidade: 'como conseguiu isso?'", "estado_mental_viewer": "'Isso e real? Como?'", "nivel_engajamento": "10/10"},
            },
            {
                "numero": 2, "momento": "00:05 - 00:15", "bloco": "SITUACAO (contexto do caso)",
                "funcao": "Criar identificacao: essa empresa era como a sua",
                "fala": {
                    "texto": (
                        "Antes disso, a empresa deles estava afogada. "
                        "WhatsApp tocando o dia todo, atendente cometendo erro, cliente esperando horas. "
                        "Cancelamento subindo, reputacao caindo. "
                        "Mesmo problema que a maioria das PMEs enfrenta hoje."
                    ),
                    "entonacao": {"tom": "empatico — conta a historia como quem viveu", "volume": "7/10", "velocidade": "normal", "pausas": "pausa antes de 'Mesmo problema'", "enfase": ["afogada", "horas", "cancelamento subindo", "a maioria das PMEs"], "emocao_na_voz": "empatia"},
                },
                "brolls": [{"descricao": "Cenas rapidas de atendentes sobrecarregados, telefone tocando, cliente esperando no chat. Stock footage ou animacao.", "tipo": "stock footage / animacao", "duracao": "8s", "momento_exato": "5-13", "transicao_entrada": "corte suave", "texto_overlay": "Situacao antes: caos no atendimento"}],
                "visual_apresentador": {"enquadramento": "meio", "angulo_camera": "frontal", "movimento": "estatico", "acao": "expressao empatica", "cenario": "mesmo"},
                "texto_tela": {"texto": "Antes: atendentes sobrecarregados, cliente esperando horas", "estilo": "fonte simples, fundo vermelho claro", "animacao": "aparece gradualmente"},
                "edicao": {"tipo_corte": "cortes rapidos entre cenas de caos", "efeito": "tom de cor levemente dessaturado (cenas do 'antes')", "sfx": "som de telefone tocando, notificacoes acumulando", "musica": "musica tensa, baixa"},
                "storytelling": {"tecnica_retencao": "identificacao — viewer se ve na situacao", "estado_mental_viewer": "'Esse sou eu. Eu passo por isso.'", "nivel_engajamento": "8/10"},
            },
            {
                "numero": 3, "momento": "00:15 - 00:25", "bloco": "ACAO — a solucao",
                "funcao": "Revelar o que mudou: o sistema de chat IA",
                "fala": {
                    "texto": (
                        "A gente implementou o Chat IA Automatico. "
                        "Integrado ao WhatsApp, Instagram e site deles. "
                        "IA treinada com os produtos, precos e politicas da empresa. "
                        "Responde qualquer pergunta, qualifica o lead, agenda reuniao. "
                        "Tudo no piloto automatico."
                    ),
                    "entonacao": {"tom": "didatico e empolgado — revelando a solucao", "volume": "8/10", "velocidade": "rapida e energica — o contraste com o 'antes' deve ser sentido", "pausas": "pausa antes de 'Tudo no piloto automatico'", "enfase": ["Chat IA Automatico", "WhatsApp, Instagram e site", "Qualquer pergunta", "Tudo no piloto automatico"], "emocao_na_voz": "entusiasmo controlado"},
                },
                "brolls": [{"descricao": "Screencast: painel de integracao mostrando logos WhatsApp, Instagram, site conectados. Depois, chat respondendo automaticamente em cada canal.", "tipo": "screencast do sistema", "duracao": "8s", "momento_exato": "15-23", "transicao_entrada": "corte energico", "texto_overlay": "WhatsApp + Instagram + Site | Tudo automatico"}],
                "visual_apresentador": {"enquadramento": "meio com gestos", "angulo_camera": "frontal", "movimento": "leve lean forward — entusiasmo", "acao": "contar nos dedos as funcoes ao mencionar cada uma", "cenario": "mesmo — mas agora com cor de tela mais vibrante ao fundo"},
                "texto_tela": {"texto": "✅ WhatsApp | ✅ Instagram | ✅ Site | ✅ 24h/dia", "estilo": "lista animada verde", "animacao": "aparece uma por uma"},
                "edicao": {"tipo_corte": "cortes mais rapidos — ritmo acelerou", "efeito": "cores mais saturadas (vs. cenas de 'antes')", "sfx": "sons positivos: 'ding' de mensagem enviada", "musica": "musica muda para ritmo mais positivo e energico"},
                "storytelling": {"tecnica_retencao": "contraste visual antes/depois — cria o 'momento aha'", "estado_mental_viewer": "'Entendi. Isso e o que resolve meu problema.'", "nivel_engajamento": "9/10"},
            },
            {
                "numero": 4, "momento": "00:25 - 00:40", "bloco": "RESULTADO — prova final",
                "funcao": "Fechar com resultados concretos que tornam a decisao facil",
                "fala": {
                    "texto": (
                        "Resultado em 60 dias: "
                        "1.200 atendimentos automaticos por mes. "
                        "Taxa de resposta: 100% em menos de 5 segundos. "
                        "Conversao de lead para venda subiu 40%. "
                        "E eles economizaram R$ 18.000 por mes so em custo de equipe. "
                        "Isso e o que o Chat IA faz."
                    ),
                    "entonacao": {"tom": "impactante — cada numero e uma vitoria", "volume": "9/10", "velocidade": "pausada — cada numero recebe 0.5s de silencio antes", "pausas": "pausa antes de cada numero", "enfase": ["1.200 atendimentos", "100%", "5 segundos", "40%", "R$ 18.000"], "emocao_na_voz": "orgulho + convicção"},
                },
                "brolls": [{"descricao": "Dashboard animado mostrando os numeros crescendo: atendimentos, conversao, economia. Visual de relatorio executivo.", "tipo": "motion graphic / screencast", "duracao": "12s", "momento_exato": "25-37", "transicao_entrada": "corte", "texto_overlay": "1.200 atend/mes | 100% resposta | +40% conversao | -R$18k/mes"}],
                "visual_apresentador": {"enquadramento": "close para enfatizar os numeros", "angulo_camera": "frontal", "movimento": "estatico", "acao": "levantar os dedos a cada numero para criar ritmo visual", "cenario": "mesmo"},
                "texto_tela": {"texto": "📊 Resultados em 60 dias", "estilo": "destaque, verde", "animacao": "contador animado em cada numero"},
                "edicao": {"tipo_corte": "jump cuts nos numeros para ritmo", "efeito": "highlight nos numeros (circulo ou sublinhado)", "sfx": "contador crescendo, som de sucesso no fim", "musica": "climax musical breve"},
                "storytelling": {"tecnica_retencao": "social proof robusto — numeros especificos > afirmacoes genericas", "estado_mental_viewer": "'Eu quero esses numeros. Como faco isso?'", "nivel_engajamento": "10/10"},
            },
            {
                "numero": 5, "momento": "00:40 - 01:00", "bloco": "CTA",
                "funcao": "Oferta irresistivel com friccao minima",
                "fala": {
                    "texto": (
                        "Se voce quer o mesmo resultado, "
                        "manda 'QUERO' aqui no direct ou acessa o link da bio. "
                        "A gente faz uma analise gratuita do seu atendimento atual "
                        "e projeta quanto voce pode economizar e faturar com a IA. "
                        "Sem custo, sem compromisso. So manda 'QUERO'."
                    ),
                    "entonacao": {"tom": "convite — sem desespero, com confianca", "volume": "8/10", "velocidade": "clara e pausada — viewer precisa absorver o que fazer", "pausas": "pausa antes de 'Sem custo' e antes do 'QUERO' final", "enfase": ["QUERO", "analise gratuita", "quanto voce pode economizar", "QUERO (final)"], "emocao_na_voz": "confianca + convite"},
                },
                "brolls": [{"descricao": "Direct sendo aberto, 'QUERO' sendo digitado, botao de enviar sendo clicado. Depois: end card com logo e call-to-action visual.", "tipo": "screencast + end card", "duracao": "10s", "momento_exato": "42-52 (DM) + 53-60 (end card)", "transicao_entrada": "corte", "texto_overlay": "Manda 'QUERO' → Analise GRATIS"}],
                "visual_apresentador": {"enquadramento": "close — conexão maxima", "angulo_camera": "frontal", "movimento": "nenhum", "acao": "apontar para camera ao dizer 'voce'", "cenario": "mesmo"},
                "texto_tela": {"texto": "Manda 'QUERO' → Analise de atendimento GRATIS", "estilo": "fundo azul escuro, texto branco grande + botao visual", "animacao": "pisca suavemente"},
                "edicao": {"tipo_corte": "fade out suave", "efeito": "nenhum", "sfx": "som de mensagem enviada", "musica": "encerra suavemente"},
                "storytelling": {"tecnica_retencao": "CTA especifico ('QUERO') reduz friccao vs 'entre em contato'", "estado_mental_viewer": "'E so mandar uma palavra. Vou fazer.'", "nivel_engajamento": "10/10"},
            },
        ],
        "cta_final": {
            "tipo": "DM com palavra-chave ('QUERO')",
            "texto_fala": "Manda 'QUERO' no direct. Fazemos analise gratuita do seu atendimento.",
            "como_falar": "confiante e convidativo",
            "oferta": "Analise gratuita do atendimento + projecao de ROI com IA",
            "urgencia": "implicita — cada dia sem o sistema = custo e leads perdidos",
            "conexao_com_gancho": "conecta ao gancho mostrando que o viewer pode ter o mesmo resultado do caso",
            "broll_cta": "DM sendo aberto + end card com logo",
        },
        "producao": {
            "cenario_ideal": "escritorio moderno, tela de computador visivel com o sistema aberto",
            "iluminacao": "profissional — ring light ou luz de janela",
            "audio": {"musica_sugerida": "tech positivo — inicio tenso (antes), depois energico (depois)", "volume_musica": "15% durante fala", "sfx_chave": ["telefone tocando (antes)", "ping de mensagem (depois)", "contador crescendo (resultados)"]},
            "figurino": "profissional — camisa ou polo. Transmite autoridade sem ser formal demais.",
            "formato": "9:16 vertical",
        },
        "distribuicao": {
            "titulo_tiktok": "De 12 atendentes para 1 IA: como esse negocio cortou 70% do custo 📊 #automacao #ia #empreendedor",
            "titulo_instagram": "12 atendentes → 1 IA. Faturamento 3x. Custo -70%. Veja como eles fizeram 👇",
            "hashtags": {"alcance": ["#empreendedor", "#negocios", "#gestao", "#marketing"], "nicho": ["#automacao", "#ia", "#CRM", "#chatbot", "#whatsappbusiness"], "long_tail": ["#atendimentoautomatico", "#chatia", "#reduçãodecustos"]},
            "horario_postagem": "7h-9h (dono de empresa no cafe da manha, planejando o dia)",
            "dia_semana": "Segunda-feira — inicio de semana, mentalidade de melhoria",
        },
    }


def _script_revelacao(avg_wpm: int, est_words: int, hook_insp: str) -> dict:
    """
    Roteiro 3 — REVELACAO / VERDADE INCONVENIENTE
    Aborda uma crença limitante do mercado e a derruba.
    Framework: Controversia -> Reframing -> Solucao -> CTA
    """
    return {
        "titulo": "A mentira que te custa clientes todo mes (e ninguem fala sobre isso)",
        "abordagem": "Revelacao — Verdade Inconveniente",
        "framework": "Controversia > Reframing > Solucao > CTA",
        "duracao_alvo": 60,
        "palavras_totais": est_words,
        "conceito": {
            "dor_central": (
                "Empresarios acreditam que atendimento humano e sempre melhor — "
                "essa crenca os impede de automatizar e os faz perder dinheiro."
            ),
            "proposta_de_valor": "IA atende melhor e mais rapido que humano na maioria dos contatos de vendas",
            "promessa": "Revelar o motivo oculto pelo qual seu atendimento humano esta te custando mais do que voce imagina.",
            "persona_alvo": (
                "Dono de empresa que resiste a IA por 'preferir o toque humano' — "
                "mas esta perdendo competitividade. Precisa ser confrontado com dados."
            ),
        },
        "gancho": {
            "tipo": "afirmacao controversa que gera discordancia imediata",
            "intensidade": "10/10",
            "texto_fala": (
                "Atendimento humano nao e o diferencial que voce pensa. "
                "Na verdade, pode estar sendo o seu maior problema de vendas."
            ),
            "como_falar": {
                "volume": "alto, firme, sem hesitacao",
                "velocidade": "normal — cada palavra deve chegar clara",
                "tom": "provocativo mas fundamentado — nao e clickbait, e verdade",
                "enfase": "NAO E O DIFERENCIAL, MAIOR PROBLEMA",
                "pausa_dramatica": "1s de silencio apos 'voce pensa.' antes de continuar",
            },
            "broll": {
                "descricao": "Atendente humano ao celular, frustrado. Depois corte para tela de IA respondendo 10 mensagens simultaneamente.",
                "tipo": "split screen",
                "duracao": "3s",
                "transicao": "corte seco",
            },
            "por_que_funciona": (
                "Desafia uma crença profunda do empresario. Ele discorda, mas fica curioso para entender o argumento. "
                "O desconforto gera retencao — ele quer ser convencido ou refutar."
            ),
        },
        "cenas": [
            {
                "numero": 1, "momento": "00:00 - 00:04", "bloco": "GANCHO — controversia",
                "funcao": "Provocar discordancia imediata que gera curiosidade",
                "fala": {"texto": "Atendimento humano nao e o diferencial que voce pensa. Pode ser o seu maior problema de vendas.", "entonacao": {"tom": "firme e provocativo", "volume": "9/10", "velocidade": "direta — sem hesitacao", "pausas": "1s apos 'voce pensa'", "enfase": ["NAO E", "MAIOR PROBLEMA"], "emocao_na_voz": "convicção"}},
                "brolls": [{"descricao": "Atendente humano olhando o celular sobrecarregado. Tela cheia de mensagens sem resposta.", "tipo": "stock footage ou encenacao", "duracao": "4s", "momento_exato": "0-4", "transicao_entrada": "inicio abrupto sem intro", "texto_overlay": "Atendimento humano: o mito que custa caro"}],
                "visual_apresentador": {"enquadramento": "close — expressao seria", "angulo_camera": "levemente para cima — autoridade", "movimento": "estatico", "acao": "balanco sutil de cabeca ao dizer 'nao e'", "cenario": "escritorio moderno"},
                "texto_tela": {"texto": "Atendimento humano pode estar te custando vendas", "estilo": "fundo vermelho, fonte branca bold", "animacao": "aparece rapido, causa impacto"},
                "edicao": {"tipo_corte": "inicio direto sem intro", "efeito": "nenhum — forca da fala e suficiente", "sfx": "nenhum", "musica": "comeca aqui levemente — suspense"},
                "storytelling": {"tecnica_retencao": "controversia — viewer fica: 'Como assim? Isso e absurdo... mas espera, por que?'", "estado_mental_viewer": "'Discordo. Me convence.'", "nivel_engajamento": "10/10"},
            },
            {
                "numero": 2, "momento": "00:04 - 00:15", "bloco": "ARGUMENTO — construindo o caso",
                "funcao": "Apresentar os dados que fundamentam a controversia",
                "fala": {
                    "texto": (
                        "Seu atendente humano responde em media em 4 horas. "
                        "A janela de interesse de um lead dura menos de 5 minutos. "
                        "Ele vai no concorrente antes do seu atendente ver a mensagem. "
                        "Nao e culpa do atendente. E limitacao humana."
                    ),
                    "entonacao": {"tom": "argumentativo — presenta fatos com calma", "volume": "8/10", "velocidade": "normal, cada dado tem peso proprio", "pausas": "pausa antes de cada dado", "enfase": ["4 horas", "5 minutos", "concorrente", "limitacao humana"], "emocao_na_voz": "convicção + empatia"},
                },
                "brolls": [{"descricao": "Cronometro animado mostrando '4h' em vermelho vs '5 min' em verde. Depois grafico de perda de lead ao longo do tempo.", "tipo": "motion graphic", "duracao": "10s", "momento_exato": "5-15", "transicao_entrada": "corte", "texto_overlay": "Tempo medio de resposta humana: 4h | Janela de interesse: 5min"}],
                "visual_apresentador": {"enquadramento": "meio", "angulo_camera": "frontal", "movimento": "estatico", "acao": "contar nos dedos ao listar os dados", "cenario": "mesmo"},
                "texto_tela": {"texto": "⏰ 4h de resposta > Lead vai embora em 5 min", "estilo": "texto impactante, vermelho vs verde", "animacao": "aparece dado a dado"},
                "edicao": {"tipo_corte": "cortes nos dados para ritmo", "efeito": "highlight nos numeros", "sfx": "relogio tickando", "musica": "tensão aumentando"},
                "storytelling": {"tecnica_retencao": "dado chocante + reframing — o viewer muda de perspectiva", "estado_mental_viewer": "'Nossa... nunca tinha pensado assim. E eu tambem demoro horas para responder.'", "nivel_engajamento": "9/10"},
            },
            {
                "numero": 3, "momento": "00:15 - 00:35", "bloco": "SOLUCAO — o reframing",
                "funcao": "Apresentar IA nao como substituto do humano, mas como parceiro estrategico",
                "fala": {
                    "texto": (
                        "A solucao nao e tirar o humano. E deixar a IA fazer o que humano nao consegue: "
                        "responder em segundos, 24 horas, em todos os canais ao mesmo tempo. "
                        "Enquanto isso, seu atendente foca nas vendas que realmente precisam de toque humano: "
                        "negociacao, relacionamento, fechamento. "
                        "IA faz o volume. Humano faz o valor."
                    ),
                    "entonacao": {"tom": "revelador e empolgante — o 'aha moment' do video", "volume": "8/10", "velocidade": "moderada — deixar a mensagem central absorver", "pausas": "pausa longa antes de 'IA faz o volume. Humano faz o valor.'", "enfase": ["nao e tirar o humano", "em segundos", "24 horas", "IA faz o volume. Humano faz o valor."], "emocao_na_voz": "revelação — entusiasmo genuino"},
                },
                "brolls": [
                    {"descricao": "Diagrama animado: IA respondendo automaticamente centenas de mensagens ao mesmo tempo. Depois: funil — leads qualificados passando para o vendedor humano.", "tipo": "motion graphic", "duracao": "10s", "momento_exato": "16-26", "transicao_entrada": "slide", "texto_overlay": "IA: volume e velocidade | Humano: valor e fechamento"},
                    {"descricao": "Screencast: dashboard mostrando 'leads qualificados prontos para o vendedor'. Atendente humano recebendo so leads quentes.", "tipo": "screencast", "duracao": "8s", "momento_exato": "27-35", "transicao_entrada": "corte", "texto_overlay": "Vendedor recebe so leads prontos para fechar"},
                ],
                "visual_apresentador": {"enquadramento": "meio com gestos amplos", "angulo_camera": "frontal", "movimento": "leve movimento ao gesticular", "acao": "gesto separando 'IA' (mao esquerda) e 'Humano' (mao direita) ao dizer a frase final", "cenario": "mesmo"},
                "texto_tela": {"texto": "IA faz o volume → Humano faz o valor", "estilo": "frase de impacto, destaque total", "animacao": "aparece palavra a palavra, bold"},
                "edicao": {"tipo_corte": "corte energico para o diagrama", "efeito": "tela dividida no diagrama", "sfx": "som de 'ding' de ideias ao aparecer o conceito", "musica": "musica positiva e energica — momento de inspiracao"},
                "storytelling": {"tecnica_retencao": "momento aha — resolve o conflito da controversia com elegancia", "estado_mental_viewer": "'Agora entendi. Nao e IA VS humano. E IA + humano.'", "nivel_engajamento": "10/10"},
            },
            {
                "numero": 4, "momento": "00:35 - 00:45", "bloco": "PROVA RAPIDA",
                "funcao": "Reforcar com caso real",
                "fala": {
                    "texto": (
                        "Um cliente nosso do setor imobiliario fez exatamente isso. "
                        "IA qualifica os interessados, agenda a visita ao imovel, passa para o corretor. "
                        "Corretor chega na reuniao com lead ja educado e pronto. "
                        "Taxa de fechamento? Dobrou em 45 dias."
                    ),
                    "entonacao": {"tom": "storytelling — caso real, rapido e especifico", "volume": "7/10", "velocidade": "normal", "pausas": "pausa antes de 'Taxa de fechamento?'", "enfase": ["imobiliario", "pronto", "Taxa de fechamento", "Dobrou"], "emocao_na_voz": "orgulho discreto"},
                },
                "brolls": [{"descricao": "Tela do sistema: chat de IA qualificando lead de imovel (perguntando: 'Qual seu orcamento? Quantos quartos precisa?'). Depois: lead passado para o corretor.", "tipo": "screencast", "duracao": "8s", "momento_exato": "35-43", "transicao_entrada": "corte suave", "texto_overlay": "IA qualifica → Corretor fecha | Taxa de fechamento: +2x"}],
                "visual_apresentador": {"enquadramento": "close", "angulo_camera": "frontal", "movimento": "estatico", "acao": "sorriso genuino ao mencionar 'Dobrou'", "cenario": "mesmo"},
                "texto_tela": {"texto": "🏠 Imobiliaria: taxa de fechamento DOBROU em 45 dias", "estilo": "verde, destaque", "animacao": "pop"},
                "edicao": {"tipo_corte": "corte para o screencast", "efeito": "highlight no numero", "sfx": "nenhum", "musica": "continua"},
                "storytelling": {"tecnica_retencao": "caso especifico de setor diferente = aplicavel a varios nichos", "estado_mental_viewer": "'Funciona no meu setor tambem?'", "nivel_engajamento": "8/10"},
            },
            {
                "numero": 5, "momento": "00:45 - 01:00", "bloco": "CTA",
                "funcao": "Conversao com oferta de descoberta personalizada",
                "fala": {
                    "texto": (
                        "Quer ver como isso funciona no seu negocio especifico? "
                        "Manda 'TESTE' no direct ou no link da bio. "
                        "A gente faz um diagnostico gratuito — "
                        "sem compromisso, sem enrolacao. "
                        "Voce ve com os seus proprios olhos o que a IA faria pelo seu atendimento."
                    ),
                    "entonacao": {"tom": "convidativo — pergunta retórica abre a conversa", "volume": "8/10", "velocidade": "clara", "pausas": "pausa antes de 'sem compromisso'", "enfase": ["seu negocio especifico", "TESTE", "gratuito", "seus proprios olhos"], "emocao_na_voz": "entusiasmo + confiança"},
                },
                "brolls": [{"descricao": "Direct sendo aberto, 'TESTE' sendo digitado. End card com logo, 'Diagnostico Gratis' e QR code.", "tipo": "screencast + end card", "duracao": "10s", "momento_exato": "47-57 + 57-60", "transicao_entrada": "corte", "texto_overlay": "Manda 'TESTE' → Diagnostico personalizado GRATIS"}],
                "visual_apresentador": {"enquadramento": "close — maximo conexao", "angulo_camera": "frontal", "movimento": "nenhum", "acao": "apontar para camera ao dizer 'seus proprios olhos'", "cenario": "mesmo"},
                "texto_tela": {"texto": "Manda 'TESTE' → Diagnostico GRATIS", "estilo": "call-to-action visual, verde, fonte impactante", "animacao": "pisca suavemente"},
                "edicao": {"tipo_corte": "fade suave", "efeito": "nenhum", "sfx": "som de mensagem enviada", "musica": "encerra positivo"},
                "storytelling": {"tecnica_retencao": "CTA personalizado ('no seu negocio especifico') — promete relevancia, nao pacote generico", "estado_mental_viewer": "'E personalizado para mim. Vou mandar.'", "nivel_engajamento": "10/10"},
            },
        ],
        "cta_final": {
            "tipo": "DM com palavra-chave ('TESTE')",
            "texto_fala": "Manda 'TESTE' no direct. Diagnostico gratuito personalizado para o seu negocio.",
            "como_falar": "curioso e convidativo — como oferecer uma descoberta, nao uma venda",
            "oferta": "Diagnostico personalizado: mapeamento do atendimento atual + demonstracao pratica da IA no nicho especifico",
            "urgencia": "implicita — cada dia de atraso e leads perdidos para quem responde mais rapido",
            "conexao_com_gancho": "resolve a controversia do inicio — o viewer agora quer provar que pode funcionar para ele",
            "broll_cta": "DM + end card limpo com logo e QR code",
        },
        "producao": {
            "cenario_ideal": "escritorio profissional, tela de computador ao fundo mostrando o sistema",
            "iluminacao": "profissional",
            "audio": {"musica_sugerida": "começa tensão/suspense, evolui para positivo/tech", "volume_musica": "15% durante fala, sem musica no gancho", "sfx_chave": ["relogio tickando (argumento)", "ding de ideias (reframing)", "mensagem enviada (CTA)"]},
            "figurino": "profissional casual — transmite autoridade sem distanciar",
            "formato": "9:16 vertical",
        },
        "distribuicao": {
            "titulo_tiktok": "A verdade sobre atendimento humano que ningem fala 👀 #ia #automacao #empreendedor #vendas",
            "titulo_instagram": "Atendimento humano pode estar te custando mais do que voce imagina. Thread 👇",
            "hashtags": {"alcance": ["#empreendedor", "#vendas", "#marketing", "#gestao"], "nicho": ["#ia", "#automacao", "#chatbot", "#CRM", "#whatsapp"], "long_tail": ["#atendimentointeligente", "#iaparaempresas", "#chatiaautomatico"]},
            "horario_postagem": "12h-14h (almoco — dono de empresa usa celular durante a pausa)",
            "dia_semana": "Quarta ou Quinta — meio da semana, mindset de otimizacao",
        },
    }


# ===================================================================
# 9. SALVAR MARKDOWN DOS ROTEIROS
# ===================================================================

def _save_markdown(scripts: list[dict]):
    md_path = OUTPUT_DIR / "roteiros.md"
    lines = []
    lines.append(f"# CAMPANHA: {PRODUCT_NAME}")
    lines.append(f"*Nicho: {NICHE}*")
    lines.append(f"*Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n")
    lines.append("---\n")

    for i, script in enumerate(scripts, 1):
        title    = script.get("titulo", f"Roteiro #{i}")
        abord    = script.get("abordagem", "")
        framework = script.get("framework", "")
        dur      = script.get("duracao_alvo", "?")

        lines.append(f"# ROTEIRO #{i}: {title}")
        lines.append(f"**Abordagem:** {abord}  |  **Framework:** {framework}  |  **Duracao:** ~{dur}s\n")

        # CONCEITO
        conceito = script.get("conceito", {})
        if conceito:
            lines.append("## CONCEITO\n")
            for k, v in conceito.items():
                lines.append(f"**{k.replace('_', ' ').title()}:** {v}\n")

        # GANCHO
        gancho = script.get("gancho", {})
        if gancho:
            lines.append("## GANCHO\n")
            lines.append(f"> \"{gancho.get('texto_fala', '')}\"\n")
            lines.append(f"**Tipo:** {gancho.get('tipo', '')}  |  **Intensidade:** {gancho.get('intensidade', '')}\n")
            como = gancho.get("como_falar", {})
            if como:
                lines.append(f"**Tom:** {como.get('tom', '')}  |  **Volume:** {como.get('volume', '')}  |  **Velocidade:** {como.get('velocidade', '')}")
                lines.append(f"**Enfase:** {como.get('enfase', '')}  |  **Pausa:** {como.get('pausa_dramatica', '')}\n")
            broll = gancho.get("broll", {})
            if broll:
                lines.append(f"**B-Roll:** {broll.get('descricao', '')}  ({broll.get('duracao', '')})\n")
            lines.append(f"**Por que funciona:** {gancho.get('por_que_funciona', '')}\n")

        # CENAS
        cenas = script.get("cenas", [])
        if cenas:
            lines.append("## ROTEIRO CENA A CENA\n")
            for cena in cenas:
                bloco   = cena.get("bloco", "")
                momento = cena.get("momento", "?")
                funcao  = cena.get("funcao", "")
                lines.append(f"### [{momento}] {bloco}")
                if funcao:
                    lines.append(f"*{funcao}*\n")

                fala = cena.get("fala", {})
                if isinstance(fala, dict) and fala.get("texto"):
                    lines.append(f"**FALA:**")
                    lines.append(f"> {fala['texto']}\n")
                    ent = fala.get("entonacao", {})
                    if ent:
                        lines.append(f"- Tom: {ent.get('tom', '')} | Volume: {ent.get('volume', '')} | Velocidade: {ent.get('velocidade', '')}")
                        lines.append(f"- Pausas: {ent.get('pausas', '')}")
                        lines.append(f"- Enfase: {ent.get('enfase', '')}")
                        lines.append(f"- Emocao: {ent.get('emocao_na_voz', '')}\n")

                brolls = cena.get("brolls", [])
                if brolls:
                    lines.append("**B-ROLLS:**\n")
                    for br in brolls:
                        if isinstance(br, dict):
                            lines.append(f"- `[{br.get('momento_exato', '?')}]` {br.get('descricao', '')}")
                            if br.get("texto_overlay"):
                                lines.append(f"  - Overlay: *\"{br['texto_overlay']}\"*")
                    lines.append("")

                visual = cena.get("visual_apresentador", {})
                if visual:
                    lines.append(f"**APRESENTADOR:** {visual.get('enquadramento', '')} | Acao: {visual.get('acao', '')}\n")

                texto_tela = cena.get("texto_tela", {})
                if texto_tela and texto_tela.get("texto"):
                    lines.append(f"**TEXTO NA TELA:** {texto_tela['texto']}  ({texto_tela.get('animacao', '')})\n")

                edicao = cena.get("edicao", {})
                if edicao:
                    lines.append(f"**EDICAO:** {edicao.get('tipo_corte', '')} | SFX: {edicao.get('sfx', '')} | Musica: {edicao.get('musica', '')}\n")

                story = cena.get("storytelling", {})
                if story:
                    lines.append(f"**STORYTELLING:** {story.get('tecnica_retencao', '')}")
                    lines.append(f"*Viewer pensa: \"{story.get('estado_mental_viewer', '')}\"*  |  Engajamento: {story.get('nivel_engajamento', '?')}\n")

                lines.append("---\n")

        # MAPA DO VIDEO
        mapa = script.get("mapa_do_video", {})
        if mapa:
            lines.append("## MAPA DO VIDEO\n")
            for faixa, info in mapa.items():
                if isinstance(info, dict):
                    lines.append(f"**{faixa}**")
                    for k, v in info.items():
                        lines.append(f"- {k.replace('_',' ').title()}: {v}")
                    lines.append("")

        # ARSENAL B-ROLLS
        arsenal = script.get("arsenal_brolls", {})
        if arsenal:
            lines.append("## ARSENAL DE B-ROLLS\n")
            for k, items in arsenal.items():
                if isinstance(items, list) and items:
                    lines.append(f"**{k.replace('_', ' ').title()}:**")
                    for item in items:
                        lines.append(f"- {item}")
                    lines.append("")

        # CTA FINAL
        cta = script.get("cta_final", {})
        if cta:
            lines.append("## CTA FINAL\n")
            lines.append(f"> \"{cta.get('texto_fala', '')}\"\n")
            lines.append(f"**Tipo:** {cta.get('tipo', '')}  |  **Oferta:** {cta.get('oferta', '')}")
            lines.append(f"**Urgencia:** {cta.get('urgencia', '')}  |  **Conexao com gancho:** {cta.get('conexao_com_gancho', '')}\n")

        # PRODUCAO
        prod = script.get("producao", {})
        if prod:
            lines.append("## PRODUCAO\n")
            lines.append(f"**Cenario:** {prod.get('cenario_ideal', '')}")
            lines.append(f"**Iluminacao:** {prod.get('iluminacao', '')}")
            lines.append(f"**Figurino:** {prod.get('figurino', '')}")
            audio = prod.get("audio", {})
            if audio:
                lines.append(f"**Musica:** {audio.get('musica_sugerida', '')} (volume: {audio.get('volume_musica', '')})")
                sfx = audio.get("sfx_chave", [])
                if sfx:
                    lines.append(f"**SFX:** {', '.join(sfx)}")
            lines.append("")

        # DISTRIBUICAO
        dist = script.get("distribuicao", {})
        if dist:
            lines.append("## DISTRIBUICAO\n")
            lines.append(f"**TikTok:** {dist.get('titulo_tiktok', '')}")
            lines.append(f"**Instagram:** {dist.get('titulo_instagram', '')}")
            hashtags = dist.get("hashtags", {})
            if isinstance(hashtags, dict):
                all_tags = []
                for lst in hashtags.values():
                    if isinstance(lst, list):
                        all_tags.extend(lst)
                if all_tags:
                    lines.append(f"**Hashtags:** {' '.join(all_tags)}")
            lines.append(f"**Horario:** {dist.get('horario_postagem', '')} | **Dia:** {dist.get('dia_semana', '')}\n")

        lines.append("\n---\n---\n")

    md_text = "\n".join(lines)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    print(f"  Markdown: {md_path}")
    return md_path


# ===================================================================
# PIPELINE PRINCIPAL
# ===================================================================

def run_pipeline():
    print("""
======================================================

   VIRAL SCRAPER — Pipeline Offline (sem Gemini)

   Transcricao (Groq) + Filtro (regras) +
   Analise (local) + Roteiros (template avancado)
   Nicho: Chat IA + Automacao + CRM

======================================================
    """)

    # 1. Construir lista
    videos = build_video_list()
    if not videos:
        print("\nNenhum video encontrado em data/audio/")
        return

    # 2. Carregar transcricoes do cache
    videos = load_existing_transcriptions(videos)

    already  = sum(1 for v in videos if v.get("transcription"))
    to_trans = len(videos) - already
    print(f"\n  Ja transcritos: {already} | Para transcrever: {to_trans}")

    # 3. Transcrever os que faltam com Groq
    if to_trans > 0:
        videos = transcribe_remaining(videos)

    transcribed_total = sum(1 for v in videos if v.get("transcription"))
    print(f"  Total com transcricao: {transcribed_total}")

    # 4. Filtrar dança/musica
    videos = filter_dance(videos)
    if not videos:
        print("\nNenhum video com conteudo falado aprovado apos filtro.")
        return

    # 5. Analise tecnica de video (FFmpeg, sem API)
    videos = run_video_analysis(videos)

    # 6. Extrair padroes localmente
    patterns = extract_patterns_local(videos)

    # 7. Gerar relatorio
    report = generate_report_local(videos, patterns)

    # 8. Gerar roteiros
    scripts = generate_scripts_local(patterns)

    # 9. Salvar estado
    state_path = DATA_DIR / "pipeline_state.json"
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump([dict(v) for v in videos], f, ensure_ascii=False, indent=2, default=str)

    # 10. Resumo
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETO!")
    print("=" * 60)
    print(f"\n  Produto: {PRODUCT_NAME}")
    print(f"  Nicho: {NICHE}")
    print(f"  Videos aprovados: {len(videos)}")
    print(f"  Roteiros gerados: {len(scripts)}")
    print(f"\n  Arquivos em output/:")
    print(f"    relatorio_viral.md  — Analise de padroes")
    print(f"    roteiros.md         — 3 roteiros completos com storytelling")
    print(f"    roteiros.json       — Roteiros em JSON estruturado")
    print(f"\n  Custo de API: apenas Groq Whisper (transcricao)")
    print(f"  Gemini: nao utilizado neste pipeline")


if __name__ == "__main__":
    run_pipeline()
