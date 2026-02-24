#!/usr/bin/env python3
"""
=============================================================
SCRIPT DE TESTE — Sem rodar o pipeline completo
=============================================================
Testa geracao de roteiros e Kling.ai com dados existentes
ou com dados mock (sem nenhuma API).

Uso:
    python testar.py          # menu interativo
    python testar.py --kling  # abre Kling direto com roteiros existentes
    python testar.py --roteiro # gera novo roteiro com dados existentes
    python testar.py --mock   # gera roteiro com dados mock (sem arquivos)
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Injeta variaveis de ambiente antes de importar config
import os
if not os.getenv("APIFY_API_TOKEN"):
    os.environ.setdefault("APIFY_API_TOKEN", "teste")
if not os.getenv("GROQ_API_KEY"):
    os.environ.setdefault("GROQ_API_KEY", "teste")
if not os.getenv("GEMINI_API_KEY"):
    # Tenta carregar do .env
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")

from config import OUTPUT_DIR, DATA_DIR
from modules import KlingLauncher


# -----------------------------------------------------------
# DADOS MOCK — videos virais simulados para testar sem API
# -----------------------------------------------------------

MOCK_VIDEOS = [
    {
        "platform": "tiktok",
        "id": "mock_001",
        "author": "@creator_viral",
        "views": 2_500_000,
        "likes": 180_000,
        "comments": 12_000,
        "shares": 8_500,
        "engagement_rate": 8.02,
        "duration": 58,
        "transcription": {
            "text": "Voce sabia que 90% das pessoas que tentam vender online cometem esse erro? Eu mesmo cometi por 2 anos. O erro e tentar vender para todo mundo. Quando voce fala com todo mundo, voce nao fala com ninguem. A virada foi quando defini meu cliente ideal com precisao cirurgica. Resultado: faturamento 3x em 4 meses. Quer saber como fazer isso? Comenta CLIENTE aqui embaixo.",
            "hook_text": "Voce sabia que 90% das pessoas que tentam vender online cometem esse erro?",
            "hook_classification": {"tipo": "estatistica", "score": 9},
            "words_per_minute": 165,
            "word_count": 87,
            "total_duration": 58,
        },
        "video_analysis": {
            "duration_seconds": 58,
            "resolution": "1080x1920",
            "fps": 30,
            "editing_pace": "moderado",
            "cuts_per_minute": 8,
            "total_cuts": 7,
        },
        "content_analysis": {
            "gancho": {
                "tipo_gancho": "estatistica",
                "gatilho_emocional": "medo de errar",
                "texto_verbal": "90% das pessoas cometem esse erro",
                "persona_alvo": "empreendedores iniciantes",
                "score": 9,
            },
            "credibilidade": {
                "tipo_prova": "resultado_pessoal",
                "resultados_citados": "faturamento 3x em 4 meses",
                "como_se_posiciona": "experiente que ja errou e corrigiu",
                "score": 8,
            },
            "conteudo_central": {
                "tipo_conteudo": "revelacao_de_erro",
                "como_apresenta": "historia pessoal com licao pratica",
                "beneficios_destacados": ["clareza de nicho", "mais conversao", "menos esforco"],
                "momento_aha": "falar com todo mundo = falar com ninguem",
                "score": 8,
                "elementos_mencionados": ["cliente ideal", "nicho", "faturamento", "vendas online"],
            },
            "cta": {
                "tipo_cta": "comentario_palavra_chave",
                "texto_exato": "comenta CLIENTE aqui embaixo",
                "oferta": "conteudo sobre cliente ideal",
                "urgencia_aplicada": "baixa",
                "score": 7,
            },
            "estrutura_narrativa": {
                "framework": "PAS",
                "tecnicas_retencao": ["revelacao progressiva", "identificacao de dor", "prova social"],
            },
            "entonacao_e_performance": {
                "tom_predominante": "confidente e direto",
                "palavras_por_minuto": 165,
                "palavras_poder": ["erro", "90%", "virada", "3x", "cirurgica"],
            },
            "pontos_fortes": ["gancho estatistico forte", "historia pessoal crivel", "CTA simples"],
        },
    },
    {
        "platform": "instagram",
        "id": "mock_002",
        "author": "@negocio_digital",
        "views": 1_800_000,
        "likes": 95_000,
        "comments": 7_200,
        "shares": 4_100,
        "engagement_rate": 5.9,
        "duration": 45,
        "transcription": {
            "text": "Para de usar esse script de vendas ultrapassado. Em 2024, o cliente quer sentir que a solucao foi feita pra ele. Script novo em 3 passos: primeiro espelha a dor exata dele. Segundo mostra que voce entende o contexto especifico. Terceiro apresenta a solucao como consequencia natural. Taxa de fechamento subiu de 23 para 61 por cento. Salva esse video.",
            "hook_text": "Para de usar esse script de vendas ultrapassado",
            "hook_classification": {"tipo": "comando", "score": 8},
            "words_per_minute": 178,
            "word_count": 73,
            "total_duration": 45,
        },
        "video_analysis": {
            "duration_seconds": 45,
            "resolution": "1080x1920",
            "fps": 30,
            "editing_pace": "rapido",
            "cuts_per_minute": 12,
            "total_cuts": 9,
        },
        "content_analysis": {
            "gancho": {
                "tipo_gancho": "comando_proibicao",
                "gatilho_emocional": "medo de estar desatualizado",
                "texto_verbal": "Para de usar esse script ultrapassado",
                "persona_alvo": "vendedores e closers",
                "score": 8,
            },
            "credibilidade": {
                "tipo_prova": "dado_numerico",
                "resultados_citados": "taxa de fechamento de 23 para 61%",
                "como_se_posiciona": "especialista em vendas com resultado comprovado",
                "score": 9,
            },
            "conteudo_central": {
                "tipo_conteudo": "tutorial_passos",
                "como_apresenta": "3 passos simples e acionaveis",
                "beneficios_destacados": ["mais fechamentos", "abordagem personalizada", "cliente se sente entendido"],
                "momento_aha": "solucao como consequencia natural da dor",
                "score": 9,
                "elementos_mencionados": ["script", "espelhamento", "taxa de fechamento", "vendas", "closer"],
            },
            "cta": {
                "tipo_cta": "salvar_conteudo",
                "texto_exato": "salva esse video",
                "oferta": "tecnica de vendas em 3 passos",
                "urgencia_aplicada": "baixa",
                "score": 6,
            },
            "estrutura_narrativa": {
                "framework": "AIDA",
                "tecnicas_retencao": ["numeros de impacto", "passo a passo", "antes e depois"],
            },
            "entonacao_e_performance": {
                "tom_predominante": "autoritario e direto",
                "palavras_por_minuto": 178,
                "palavras_poder": ["ultrapassado", "61%", "natural", "especifico", "exata"],
            },
            "pontos_fortes": ["dado numerico impactante", "estrutura clara", "aplicabilidade imediata"],
        },
    },
]


# -----------------------------------------------------------
# FUNCOES DE TESTE
# -----------------------------------------------------------

def testar_kling_existente():
    """Abre Kling.ai com roteiros que ja existem em output/roteiros.json."""
    roteiros_path = OUTPUT_DIR / "roteiros.json"
    if not roteiros_path.exists():
        print(f"\n  ERRO: {roteiros_path} nao encontrado.")
        print("  Execute primeiro: python testar.py --roteiro")
        return

    with open(roteiros_path, encoding="utf-8") as f:
        scripts = json.load(f)

    if not scripts:
        print("  roteiros.json esta vazio.")
        return

    print(f"\n  {len(scripts)} roteiro(s) carregado(s) de {roteiros_path}")
    for i, s in enumerate(scripts, 1):
        titulo = s.get("titulo", f"Roteiro {i}")
        cenas = len(s.get("cenas", []))
        tem_prompt = any(c.get("ai_video_prompt") for c in s.get("cenas", []))
        print(f"  [{i}] {titulo} — {cenas} cenas — prompts IA: {'SIM' if tem_prompt else 'NAO'}")

    if not any(c.get("ai_video_prompt") for s in scripts for c in s.get("cenas", [])):
        print("\n  AVISO: Esses roteiros foram gerados antes da atualizacao.")
        print("  Nao tem ai_video_prompt ainda.")
        print("  Execute: python testar.py --roteiro  para gerar novos com prompts.")
        return

    launcher = KlingLauncher()
    launcher.launch(scripts)


def testar_roteiro_com_dados_existentes():
    """Gera novo roteiro usando dados ja existentes (sem rodar o pipeline)."""
    state_path = DATA_DIR / "pipeline_state.json"
    analyses_path = OUTPUT_DIR / "content_analyses.json"
    transcriptions_path = DATA_DIR / "transcriptions.json"
    scraped_path = DATA_DIR / "scraped_videos.json"

    videos = None

    # Prioridade 1: pipeline_state.json (dados completos)
    if state_path.exists():
        print(f"  Carregando pipeline_state.json...")
        with open(state_path, encoding="utf-8") as f:
            videos = json.load(f)
        print(f"  {len(videos)} videos com analise completa")

    # Prioridade 2: content_analyses.json com dados
    elif analyses_path.exists():
        with open(analyses_path, encoding="utf-8") as f:
            analyses = json.load(f)
        if analyses:
            print(f"  Carregando content_analyses.json...")
            videos = [{"id": vid_id, **data} for vid_id, data in analyses.items()] if isinstance(analyses, dict) else analyses
            print(f"  {len(videos)} analises carregadas")

    # Prioridade 3: scraped + transcriptions (mais comum apos pipeline parcial)
    if not videos and scraped_path.exists() and transcriptions_path.exists():
        print(f"  Carregando scraped_videos.json + transcriptions.json...")
        with open(scraped_path, encoding="utf-8") as f:
            scraped = json.load(f)
        with open(transcriptions_path, encoding="utf-8") as f:
            transcriptions = json.load(f)

        # Mescla transcricoes nos videos
        trans_map = {}
        if isinstance(transcriptions, dict):
            trans_map = transcriptions
        elif isinstance(transcriptions, list):
            trans_map = {v.get("id", v.get("video_id", "")): v for v in transcriptions}

        videos = []
        for v in scraped:
            vid_id = str(v.get("id", ""))
            if vid_id in trans_map:
                trans_data = trans_map[vid_id]
                v["transcription"] = trans_data.get("transcription", trans_data)
            videos.append(v)

        tem_trans = sum(1 for v in videos if v.get("transcription"))
        print(f"  {len(videos)} videos | {tem_trans} com transcricao")

    # Fallback: mock
    if not videos:
        print("  Nenhum dado local encontrado. Usando dados mock...")
        videos = MOCK_VIDEOS

    return _gerar_roteiro(videos)


def testar_roteiro_mock():
    """Gera roteiro com dados mock — nao precisa de nenhum arquivo."""
    print("\n  Usando dados mock (2 videos simulados)...")
    return _gerar_roteiro(MOCK_VIDEOS)


def _gerar_roteiro(videos: list) -> list:
    """Gera roteiro e pergunta se quer abrir Kling."""
    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY or GEMINI_API_KEY == "teste":
        print("\n  GEMINI_API_KEY nao configurada.")
        print("  Adicione no .env: GEMINI_API_KEY=sua_chave")
        print("  Chave gratis em: https://aistudio.google.com/apikey")
        return []

    from modules import ScriptGenerator

    print("\n" + "=" * 60)
    print("  CONFIGURACAO DO ROTEIRO")
    print("=" * 60)

    nicho = input("\n  Seu nicho (ex: marketing digital, ecommerce, saude):\n  -> ").strip() or "marketing digital"
    tema = input("\n  Tema do video (ex: como dobrar vendas em 30 dias):\n  -> ").strip() or "como aumentar vendas"

    print("\n  Estilo:")
    print("  1. Educativo  2. Storytelling  3. Controverso  4. Tutorial  5. Transformacao")
    estilo_map = {"1": "educativo", "2": "storytelling", "3": "controverso", "4": "educativo", "5": "transformacao"}
    estilo = estilo_map.get(input("  Escolha [1-5] (Enter=1): ").strip() or "1", "educativo")

    duracao = input("\n  Duracao em segundos (Enter=60): ").strip() or "60"
    num = input("  Quantos roteiros gerar (Enter=1): ").strip() or "1"

    print(f"\n  Gerando {num} roteiro(s) para nicho '{nicho}'...")
    print("  (pode levar 30-60 segundos)\n")

    generator = ScriptGenerator(niche=nicho)
    scripts = generator.generate_scripts(
        videos=videos,
        topic=tema,
        niche=nicho,
        style=estilo,
        num_scripts=int(num),
        duration_seconds=int(duracao),
    )

    print(f"\n  {len(scripts)} roteiro(s) gerado(s)!")
    print(f"  Arquivos salvos em {OUTPUT_DIR}/")

    abrir = input("\n  Abrir Kling.ai agora para gerar os videos? [S/n]: ").strip().lower()
    if abrir != "n":
        launcher = KlingLauncher()
        launcher.launch(scripts)

    return scripts


def ver_prompts():
    """Mostra os prompts gerados no terminal."""
    md_path = OUTPUT_DIR / "ai_video_prompts.md"
    txt_path = OUTPUT_DIR / "prompts_kling.txt"

    if txt_path.exists():
        print(f"\n  Lendo: {txt_path}\n")
        print(txt_path.read_text(encoding="utf-8"))
    elif md_path.exists():
        print(f"\n  Lendo: {md_path}\n")
        print(md_path.read_text(encoding="utf-8"))
    else:
        print("\n  Nenhum arquivo de prompts encontrado.")
        print("  Execute: python testar.py --roteiro")


# -----------------------------------------------------------
# MENU INTERATIVO
# -----------------------------------------------------------

def menu():
    print("""
======================================================

  VIRAL SCRAPER — MODO DE TESTE

======================================================

  Testa sem rodar o pipeline completo.

  1. Abrir Kling.ai com roteiros existentes
     (usa output/roteiros.json)

  2. Gerar novo roteiro com dados existentes
     (usa content_analyses.json ou pipeline_state.json)

  3. Gerar roteiro com dados MOCK
     (sem nenhum arquivo — so precisa da GEMINI_API_KEY)

  4. Ver prompts gerados

  5. Gerar VIDEO COMPLETO — TTS + edicao (sem IA, gratis)
     (usa roteiros existentes, gera MP4 pronto para postar)

  6. Gerar VIDEO COMPLETO — TTS + clips fal.ai + edicao
     (requer FAL_AI_KEY no .env)

  0. Sair
""")

    while True:
        choice = input("  Escolha: ").strip()

        if choice == "1":
            testar_kling_existente()
        elif choice == "2":
            testar_roteiro_com_dados_existentes()
        elif choice == "3":
            testar_roteiro_mock()
        elif choice == "4":
            ver_prompts()
        elif choice == "5":
            testar_video(modo="sem_ia")
        elif choice == "6":
            testar_video(modo="com_ia")
        elif choice == "0":
            print("\n  Ate mais!")
            break
        else:
            print("  Opcao invalida.")


# -----------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------

def testar_video(modo="sem_ia", music_path=None, voice=None, clips_dir=None):
    """Gera video completo a partir de output/roteiros.json."""
    roteiros_path = OUTPUT_DIR / "roteiros.json"
    if not roteiros_path.exists():
        print(f"\n  ERRO: {roteiros_path} nao encontrado.")
        print("  Execute primeiro: python testar.py --roteiro")
        return

    with open(roteiros_path, encoding="utf-8") as f:
        scripts = json.load(f)

    # Filtrar apenas roteiros com cenas
    scripts_validos = [s for s in scripts if s.get("cenas")]
    if not scripts_validos:
        print("\n  AVISO: Roteiros sem cenas encontrados.")
        print("  Regenere os roteiros: python testar.py --roteiro")
        return

    print(f"\n  {len(scripts_validos)} roteiro(s) valido(s)")
    for i, s in enumerate(scripts_validos, 1):
        cenas = len(s.get("cenas", []))
        print(f"  [{i}] {s.get('titulo','?')[:60]} — {cenas} cenas")

    if len(scripts_validos) > 1:
        idx = input("\n  Qual processar? (Enter=todos | 1,2,...): ").strip()
        if idx.isdigit() and 1 <= int(idx) <= len(scripts_validos):
            scripts_validos = [scripts_validos[int(idx) - 1]]

    if not voice:
        print("\n  Voz TTS:")
        print("  1. Feminina — pt-BR-FranciscaNeural (recomendada para conteudo)")
        print("  2. Masculina — pt-BR-AntonioNeural (autoridade/vendas)")
        v = input("  Escolha [1/2] (Enter=1): ").strip() or "1"
        voice = "masculino" if v == "2" else "feminino"

    if not music_path:
        music_path = input("\n  Path da musica de fundo (Enter=sem musica): ").strip() or None

    from modules.pipeline_video import PipelineVideo
    pipeline = PipelineVideo(voice=voice, music_path=music_path)
    pipeline.executar(scripts_validos, modo=modo, clips_dir=clips_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Viral Scraper — Teste")
    parser.add_argument("--kling",    action="store_true", help="Abre Kling com roteiros existentes")
    parser.add_argument("--roteiro",  action="store_true", help="Gera roteiro com dados existentes")
    parser.add_argument("--mock",     action="store_true", help="Gera roteiro com dados mock")
    parser.add_argument("--prompts",  action="store_true", help="Mostra prompts gerados")
    parser.add_argument("--video",    action="store_true", help="Gera video completo (TTS + ffmpeg)")
    parser.add_argument("--modo",     default="sem_ia",
                        choices=["sem_ia", "com_ia", "clips_ok"],
                        help="Modo video: sem_ia (default) | com_ia (fal.ai) | clips_ok")
    parser.add_argument("--musica",   default="", help="Path MP3 para musica de fundo")
    parser.add_argument("--voz",      default="",
                        choices=["feminino", "masculino", "feminino2", "masculino2", ""],
                        help="Voz TTS")
    parser.add_argument("--clips-dir", default="", help="Pasta de clips para modo clips_ok")
    args = parser.parse_args()

    if args.kling:
        testar_kling_existente()
    elif args.roteiro:
        testar_roteiro_com_dados_existentes()
    elif args.mock:
        testar_roteiro_mock()
    elif args.prompts:
        ver_prompts()
    elif args.video:
        testar_video(
            modo=args.modo,
            music_path=args.musica or None,
            voice=args.voz or None,
            clips_dir=args.clips_dir or None,
        )
    else:
        menu()
