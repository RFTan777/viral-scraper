#!/usr/bin/env python3
"""
=============================================================
VIRAL SCRAPER - ORQUESTRADOR PRINCIPAL
=============================================================
Sistema completo de scraping, analise e geracao de roteiros
para conteudo viral no TikTok e Instagram.

Uso:
    python main.py                    # Menu interativo
    python main.py --full             # Pipeline completo
    python main.py --scrape-only      # Apenas scraping
    python main.py --analyze-only     # Apenas analise (precisa de dados)
    python main.py --scripts-only     # Apenas gerar roteiros
"""

import argparse
import json
import sys
from pathlib import Path

# Adicionar diretorio raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR, OUTPUT_DIR
from modules import (
    ApifyScraper,
    VideoDownloader,
    Transcriber,
    VideoAnalyzer,
    ContentAnalyzer,
    ScriptGenerator,
    ContentFilter,
    DeduplicationTracker,
    PipelineCheckpoint,
    RateTracker,
)


def print_banner():
    print("""
======================================================

   V I R A L   S C R A P E R

   Scraping -> Analise -> Roteiros Virais
   TikTok + Instagram

======================================================
    """)


def get_niche() -> str:
    """Coleta o nicho do usuario."""
    print("\n CONFIGURACAO DO NICHO")
    print("-" * 40)
    print("\nExemplos: marketing digital, fitness, culinaria, financas,")
    print("  ecommerce, saude, educacao, tecnologia, moda, beleza")
    niche = input("\nQual e o seu nicho?\n-> ").strip()
    if not niche:
        niche = "conteudo viral"
        print(f"  Usando nicho padrao: {niche}")
    return niche


def get_search_params() -> dict:
    """Coleta parametros de busca do usuario."""
    print("\n CONFIGURACAO DA BUSCA")
    print("-" * 40)

    # Plataformas
    print("\nPlataformas:")
    print("  1. TikTok + Instagram")
    print("  2. Apenas TikTok")
    print("  3. Apenas Instagram")
    platform_choice = input("\nEscolha [1/2/3] (padrao: 1): ").strip() or "1"

    platforms = {
        "1": ["tiktok", "instagram"],
        "2": ["tiktok"],
        "3": ["instagram"],
    }.get(platform_choice, ["tiktok", "instagram"])

    # Tipo de busca
    print("\nTipo de busca:")
    print("  1. Por hashtags")
    print("  2. Por perfis especificos")
    print("  3. Por palavras-chave")
    search_type = input("\nEscolha [1/2/3] (padrao: 1): ").strip() or "1"

    search_params = {"platforms": platforms}

    if search_type == "1":
        tags = input("\nDigite as hashtags (separadas por virgula):\n-> ").strip()
        search_params["hashtags"] = [t.strip().replace("#", "") for t in tags.split(",")]
    elif search_type == "2":
        profiles = input("\nDigite os perfis (separados por virgula):\n-> ").strip()
        search_params["profiles"] = [p.strip().replace("@", "") for p in profiles.split(",")]
    else:
        keywords = input("\nDigite as palavras-chave (separadas por virgula):\n-> ").strip()
        search_params["keywords"] = [k.strip() for k in keywords.split(",")]

    return search_params


def get_script_params() -> dict:
    """Coleta parametros para geracao de roteiros."""
    print("\n CONFIGURACAO DOS ROTEIROS")
    print("-" * 40)

    topic = input("\nSobre qual tema/assunto? \n-> ").strip()

    print("\nEstilo do conteudo:")
    print("  1. Educativo / Tutorial")
    print("  2. Storytelling / Historia pessoal")
    print("  3. Humor / Entretenimento")
    print("  4. Controverso / Opiniao forte")
    print("  5. Antes e depois / Transformacao")
    style_choice = input("\nEscolha [1-5] (padrao: 1): ").strip() or "1"

    style_map = {
        "1": "educativo",
        "2": "storytelling",
        "3": "humor",
        "4": "controverso",
        "5": "transformacao",
    }
    style = style_map.get(style_choice, "educativo")

    num = input("\nQuantos roteiros gerar? (padrao: 3)\n-> ").strip() or "3"
    duration = input("Duracao em segundos? (padrao: 60)\n-> ").strip() or "60"

    return {
        "topic": topic,
        "style": style,
        "num_scripts": int(num),
        "duration_seconds": int(duration),
    }


# ---------------------------------------------
# PIPELINE PRINCIPAL
# ---------------------------------------------

def run_scraping(search_params: dict) -> list[dict]:
    """Etapa 1: Scraping via Apify."""
    scraper = ApifyScraper()
    all_videos = []

    if "tiktok" in search_params["platforms"]:
        tiktok_videos = scraper.scrape_tiktok(
            hashtags=search_params.get("hashtags"),
            profiles=search_params.get("profiles"),
            keywords=search_params.get("keywords"),
        )
        all_videos.extend(tiktok_videos)

    if "instagram" in search_params["platforms"]:
        instagram_videos = scraper.scrape_instagram(
            hashtags=search_params.get("hashtags"),
            profiles=search_params.get("profiles"),
        )
        all_videos.extend(instagram_videos)

    scraper.save_results(all_videos)
    return all_videos


def run_filter_stage_a(videos: list[dict], niche: str) -> list[dict]:
    """Etapa 1.5: Filtro pre-download."""
    content_filter = ContentFilter(niche=niche)
    approved, rejected = content_filter.filter_stage_a(videos)
    return approved


def run_download(videos: list[dict]) -> list[dict]:
    """Etapa 2: Download dos videos."""
    downloader = VideoDownloader()
    return downloader.download_all(videos)


def run_transcription(videos: list[dict]) -> list[dict]:
    """Etapa 3: Transcricao com Whisper."""
    transcriber = Transcriber()
    videos = transcriber.transcribe_all(videos)
    transcriber.save_transcriptions(videos)
    return videos


def run_filter_stage_b(videos: list[dict], niche: str) -> list[dict]:
    """Etapa 3.5: Filtro pos-transcricao."""
    content_filter = ContentFilter(niche=niche)
    approved, rejected = content_filter.filter_stage_b(videos)
    return approved


def run_video_analysis(videos: list[dict]) -> list[dict]:
    """Etapa 4: Analise tecnica de video."""
    analyzer = VideoAnalyzer()
    videos = analyzer.analyze_all(videos)
    analyzer.save_analysis(videos)
    return videos


def run_content_analysis(videos: list[dict], niche: str) -> tuple[list[dict], str]:
    """Etapa 5: Analise profunda com Gemini."""
    analyzer = ContentAnalyzer(niche=niche)
    videos = analyzer.analyze_all(videos)
    analyzer.save_analyses(videos)
    report = analyzer.generate_report(videos)
    return videos, report


def run_script_generation(videos: list[dict], script_params: dict, niche: str) -> list[dict]:
    """Etapa 6: Geracao de roteiros."""
    generator = ScriptGenerator(niche=niche)
    scripts = generator.generate_scripts(
        videos=videos,
        niche=niche,
        **script_params,
    )
    return scripts


# ---------------------------------------------
# PIPELINE COMPLETO COM CHECKPOINT
# ---------------------------------------------

def run_full_pipeline():
    """Executa o pipeline completo do inicio ao fim, com checkpoint/resume."""
    print_banner()

    checkpoint = PipelineCheckpoint()
    dedup = DeduplicationTracker()
    rate_tracker = RateTracker()

    # Verificar checkpoint existente
    if checkpoint.has_checkpoint():
        checkpoint.print_status()
        resume = input("\nDeseja retomar de onde parou? [S/n]: ").strip().lower()
        if resume != "n":
            videos = checkpoint.load_videos()
            extra = checkpoint.load_extra_data()
            niche = extra.get("niche", "conteudo viral")
            search_params = extra.get("search_params", {})
            print(f"\n  Retomando pipeline — Nicho: {niche}, {len(videos)} videos")
        else:
            checkpoint.clear()
            videos = None
            niche = None
            search_params = None
    else:
        videos = None
        niche = None
        search_params = None

    # 0. Coletar nicho
    if not niche:
        niche = get_niche()

    extra_data = {"niche": niche}

    # Mostrar status de rate limits
    rate_tracker.print_status()

    # 1. Scraping
    if not checkpoint.should_skip("scraping"):
        search_params = get_search_params()
        extra_data["search_params"] = search_params
        videos = run_scraping(search_params)
        if not videos:
            print("\n Nenhum video encontrado. Tente outros termos de busca.")
            return
        checkpoint.save_stage("scraping", videos, extra_data)
    elif videos is None:
        videos = checkpoint.load_videos()

    # 1.5. Deduplicacao
    videos, n_dupes = dedup.filter_new(videos)
    if not videos:
        print("\n Todos os videos ja foram processados anteriormente.")
        return

    # 2. Filtro Stage A (pre-download)
    if not checkpoint.should_skip("filter_a"):
        videos = run_filter_stage_a(videos, niche)
        if not videos:
            print("\n Todos os videos foram filtrados no Stage A.")
            return
        checkpoint.save_stage("filter_a", videos, extra_data)

    # 3. Download
    if not checkpoint.should_skip("download"):
        videos = run_download(videos)
        if not videos:
            print("\n Nenhum video baixado com sucesso.")
            return
        checkpoint.save_stage("download", videos, extra_data)

    # 4. Transcricao
    if not checkpoint.should_skip("transcription"):
        videos = run_transcription(videos)
        checkpoint.save_stage("transcription", videos, extra_data)

    # 4.5. Filtro Stage B (pos-transcricao)
    if not checkpoint.should_skip("filter_b"):
        videos = run_filter_stage_b(videos, niche)
        if not videos:
            print("\n Todos os videos foram filtrados no Stage B.")
            return
        checkpoint.save_stage("filter_b", videos, extra_data)

    # 5. Analise de video
    if not checkpoint.should_skip("video_analysis"):
        videos = run_video_analysis(videos)
        checkpoint.save_stage("video_analysis", videos, extra_data)

    # 6. Analise de conteudo + Relatorio
    if not checkpoint.should_skip("content_analysis"):
        # Verificar rate limits
        if not rate_tracker.can_proceed("gemini", len(videos) + 1):
            print(f"\n AVISO: Rate limit do Gemini proximo do limite!")
            rate_tracker.print_status()
            proceed = input("Continuar mesmo assim? [s/N]: ").strip().lower()
            if proceed != "s":
                print("Pipeline pausado. Execute novamente amanha.")
                return

        videos, report = run_content_analysis(videos, niche)
        rate_tracker.track("gemini", len([v for v in videos if v.get("content_analysis")]) + 1)
        checkpoint.save_stage("content_analysis", videos, extra_data)

    # 7. Perguntar se quer gerar roteiros
    print("\n" + "=" * 60)
    generate = input("\nDeseja gerar roteiros baseados na analise? [S/n]: ").strip().lower()
    if generate != "n":
        if not checkpoint.should_skip("script_generation"):
            script_params = get_script_params()
            num_scripts = script_params.get("num_scripts", 3)

            if not rate_tracker.can_proceed("gemini", num_scripts + 1):
                print(f"\n AVISO: Rate limit do Gemini proximo do limite!")
                rate_tracker.print_status()

            scripts = run_script_generation(videos, script_params, niche)
            rate_tracker.track("gemini", num_scripts + 1)
            checkpoint.save_stage("script_generation", videos, extra_data)

    # 8. Marcar videos como processados
    dedup.mark_batch(videos)

    # 9. Resumo final
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETO!")
    print("=" * 60)
    print(f"\n  Nicho: {niche}")
    print(f"  Videos processados: {len(videos)}")
    print(f"\n  Arquivos gerados em: {OUTPUT_DIR}/")
    print(f"    relatorio_viral.md    -- Relatorio de analise")
    print(f"    content_analyses.json -- Analises detalhadas")
    print(f"    roteiros.md           -- Roteiros em Markdown")
    print(f"    roteiros.json         -- Roteiros em JSON")

    # Salvar estado completo
    state_path = DATA_DIR / "pipeline_state.json"
    with open(state_path, "w", encoding="utf-8") as f:
        serializable = [dict(v) for v in videos]
        json.dump(serializable, f, ensure_ascii=False, indent=2, default=str)
    print(f"    pipeline_state.json   -- Estado completo salvo")

    # Limpar checkpoint (pipeline completo)
    checkpoint.clear()

    # Status final de rate limits
    rate_tracker.print_status()


# ---------------------------------------------
# MENU INTERATIVO
# ---------------------------------------------

def interactive_menu():
    """Menu interativo para executar etapas individuais."""
    print_banner()

    while True:
        print("\n MENU PRINCIPAL")
        print("-" * 40)
        print("  1. Pipeline Completo (recomendado)")
        print("  2. Apenas Scraping")
        print("  3. Apenas Analise (precisa ter dados)")
        print("  4. Apenas Gerar Roteiros (precisa ter analise)")
        print("  5. Ver ultimo relatorio")
        print("  6. Status de rate limits")
        print("  0. Sair")

        choice = input("\nEscolha: ").strip()

        if choice == "1":
            run_full_pipeline()

        elif choice == "2":
            search_params = get_search_params()
            videos = run_scraping(search_params)
            print(f"\n  {len(videos)} videos coletados!")

        elif choice == "3":
            # Carregar dados existentes
            state_path = DATA_DIR / "pipeline_state.json"
            scraped_path = DATA_DIR / "scraped_videos.json"

            if state_path.exists():
                with open(state_path) as f:
                    videos = json.load(f)
            elif scraped_path.exists():
                with open(scraped_path) as f:
                    videos = json.load(f)
                # Precisar rodar download + transcricao + video analysis
                videos = run_download(videos)
                videos = run_transcription(videos)
                videos = run_video_analysis(videos)
            else:
                print("Nenhum dado encontrado. Execute o scraping primeiro.")
                continue

            niche = get_niche()
            videos, report = run_content_analysis(videos, niche)

        elif choice == "4":
            state_path = DATA_DIR / "pipeline_state.json"
            if not state_path.exists():
                print("Nenhuma analise encontrada. Execute a analise primeiro.")
                continue

            with open(state_path) as f:
                videos = json.load(f)

            niche = get_niche()
            script_params = get_script_params()
            scripts = run_script_generation(videos, script_params, niche)

        elif choice == "5":
            report_path = OUTPUT_DIR / "relatorio_viral.md"
            if report_path.exists():
                print(report_path.read_text(encoding="utf-8"))
            else:
                print("Nenhum relatorio encontrado.")

        elif choice == "6":
            rate_tracker = RateTracker()
            rate_tracker.print_status()

        elif choice == "0":
            print("\nAte mais!")
            break

        else:
            print("Opcao invalida.")


# ---------------------------------------------
# ENTRY POINT
# ---------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Viral Scraper")
    parser.add_argument("--full", action="store_true", help="Pipeline completo")
    parser.add_argument("--scrape-only", action="store_true", help="Apenas scraping")
    parser.add_argument("--analyze-only", action="store_true", help="Apenas analise")
    parser.add_argument("--scripts-only", action="store_true", help="Apenas roteiros")

    args = parser.parse_args()

    if args.full:
        run_full_pipeline()
    elif args.scrape_only:
        search_params = get_search_params()
        run_scraping(search_params)
    elif args.analyze_only:
        state_path = DATA_DIR / "pipeline_state.json"
        scraped_path = DATA_DIR / "scraped_videos.json"
        if state_path.exists():
            with open(state_path) as f:
                videos = json.load(f)
        elif scraped_path.exists():
            with open(scraped_path) as f:
                videos = json.load(f)
            videos = run_download(videos)
            videos = run_transcription(videos)
            videos = run_video_analysis(videos)
        else:
            print("Nenhum dado encontrado. Execute o scraping primeiro.")
            sys.exit(1)
        niche = get_niche()
        run_content_analysis(videos, niche)
    elif args.scripts_only:
        state_path = DATA_DIR / "pipeline_state.json"
        if not state_path.exists():
            print("Nenhuma analise encontrada. Execute a analise primeiro.")
            sys.exit(1)
        with open(state_path) as f:
            videos = json.load(f)
        niche = get_niche()
        script_params = get_script_params()
        run_script_generation(videos, script_params, niche)
    else:
        interactive_menu()
