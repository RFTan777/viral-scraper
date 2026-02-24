#!/usr/bin/env python3
"""
=============================================================
PIPELINE DIRETO: Videos existentes -> Roteiros
=============================================================
Pega TODOS os videos/audios ja baixados, transcreve, analisa
e gera roteiros focados no nicho especifico.

Uso:
    python run_from_existing.py
"""

import json
import sys
import glob
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR, OUTPUT_DIR, VIDEOS_DIR, AUDIO_DIR
from modules import (
    Transcriber,
    VideoAnalyzer,
    ContentAnalyzer,
    ScriptGenerator,
    ContentFilter,
    RateTracker,
)


# =============================================
# NICHO FIXO
# =============================================
NICHE = "venda de sistema de chat com IA, automacao de atendimento e CRM para empresas"


def build_video_list() -> list[dict]:
    """
    Constroi lista de videos a partir dos arquivos existentes em disco.
    Tenta carregar metadata do scraped_videos.json quando disponivel.
    """
    print("\n" + "=" * 60)
    print("CONSTRUINDO LISTA DE VIDEOS EXISTENTES")
    print("=" * 60)

    # Carregar metadata existente
    scraped_path = DATA_DIR / "scraped_videos.json"
    metadata_by_id = {}
    if scraped_path.exists():
        with open(scraped_path, "r", encoding="utf-8") as f:
            scraped = json.load(f)
        for v in scraped:
            metadata_by_id[str(v.get("id", ""))] = v

    # Listar todos os audios (ponto de partida — precisamos do audio para transcrever)
    audio_files = sorted(glob.glob(str(AUDIO_DIR / "*.mp3")))
    print(f"  Audios encontrados: {len(audio_files)}")

    videos = []
    for audio_path in audio_files:
        audio_name = os.path.basename(audio_path).replace(".mp3", "")
        video_id = audio_name

        # Tentar encontrar o arquivo de video correspondente
        video_path = None
        for pattern in [f"tiktok_{video_id}.mp4", f"instagram_{video_id}.mp4", f"{video_id}.mp4"]:
            candidate = VIDEOS_DIR / pattern
            if candidate.exists():
                video_path = str(candidate)
                break

        # Pegar metadata se existir, senao criar basica
        if video_id in metadata_by_id:
            video = dict(metadata_by_id[video_id])
        else:
            video = {
                "platform": "tiktok",
                "id": video_id,
                "url": "",
                "video_url": "",
                "description": "",
                "author": f"autor_{video_id[-6:]}",
                "author_followers": 0,
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "saves": 0,
                "engagement_rate": 0,
                "duration": 0,
                "hashtags": [],
                "music": "",
                "created_at": "",
                "cover_url": "",
            }

        video["local_video_path"] = video_path
        video["local_audio_path"] = audio_path
        videos.append(video)

    print(f"  Videos com metadata: {sum(1 for v in videos if v.get('views', 0) > 0)}")
    print(f"  Videos sem metadata: {sum(1 for v in videos if v.get('views', 0) == 0)}")
    print(f"  Total: {len(videos)}")

    return videos


def load_existing_transcriptions(videos: list[dict]) -> list[dict]:
    """Carrega transcricoes ja existentes para evitar retranscrever."""
    trans_path = DATA_DIR / "transcriptions.json"
    if not trans_path.exists():
        return videos

    with open(trans_path, "r", encoding="utf-8") as f:
        existing = json.load(f)

    loaded = 0
    for video in videos:
        vid_id = video["id"]
        if vid_id in existing and existing[vid_id].get("transcription"):
            video["transcription"] = existing[vid_id]["transcription"]
            loaded += 1

    print(f"  Transcricoes carregadas do cache: {loaded}")
    return videos


def run_pipeline():
    """Pipeline completo: videos existentes -> roteiros."""

    print("""
======================================================

   VIRAL SCRAPER — Pipeline Direto

   Videos existentes -> Transcricao -> Analise -> Roteiros
   Nicho: Chat IA + Automacao + CRM

======================================================
    """)

    rate_tracker = RateTracker()
    rate_tracker.print_status()

    # 1. Construir lista de videos
    videos = build_video_list()
    if not videos:
        print("\nNenhum video encontrado em data/videos/ e data/audio/")
        return

    # 2. Carregar transcricoes existentes
    videos = load_existing_transcriptions(videos)
    already_transcribed = sum(1 for v in videos if v.get("transcription"))
    to_transcribe = sum(1 for v in videos if not v.get("transcription"))
    print(f"\n  Ja transcritos: {already_transcribed}")
    print(f"  Para transcrever: {to_transcribe}")

    # 3. Transcrever os que faltam
    if to_transcribe > 0:
        print(f"\n  Transcrevendo {to_transcribe} audios...")
        # Filtrar apenas os que precisam transcrever
        need_transcription = [v for v in videos if not v.get("transcription")]
        transcriber = Transcriber()
        need_transcription = transcriber.transcribe_all(need_transcription)

        # Merge de volta
        transcribed_map = {v["id"]: v.get("transcription") for v in need_transcription}
        for video in videos:
            if not video.get("transcription") and video["id"] in transcribed_map:
                video["transcription"] = transcribed_map[video["id"]]

        # Salvar TODAS as transcricoes
        transcriber.save_transcriptions(videos)
        rate_tracker.track("groq", to_transcribe)

    # 4. Filtro Stage B — remover videos sem fala
    print("\n" + "=" * 60)
    print("FILTRANDO CONTEUDO SEM FALA")
    print("=" * 60)

    content_filter = ContentFilter(niche=NICHE)
    before = len(videos)
    videos = [v for v in videos if v.get("transcription")]  # remover sem transcricao
    approved, rejected = content_filter.filter_stage_b(videos)
    videos = approved
    print(f"  {before} -> {len(videos)} videos com conteudo relevante")

    if not videos:
        print("\nNenhum video com conteudo falado relevante encontrado.")
        return

    # 5. Analise de video (tecnica) — so para os que tem arquivo de video
    videos_with_file = [v for v in videos if v.get("local_video_path") and Path(v["local_video_path"]).exists()]
    if videos_with_file:
        analyzer = VideoAnalyzer()
        videos_with_file = analyzer.analyze_all(videos_with_file)
        analyzer.save_analysis(videos_with_file)

        # Merge analises de volta
        va_map = {v["id"]: v.get("video_analysis") for v in videos_with_file}
        for video in videos:
            if video["id"] in va_map:
                video["video_analysis"] = va_map[video["id"]]

    # 6. Analise de conteudo com Gemini
    print("\n" + "=" * 60)
    print(f"ANALISE DE CONTEUDO — Nicho: {NICHE}")
    print("=" * 60)

    # Verificar rate limit
    needed_requests = len(videos) + 1  # +1 para relatorio
    if not rate_tracker.can_proceed("gemini", needed_requests):
        print(f"\n  AVISO: Precisa de {needed_requests} requests Gemini")
        rate_tracker.print_status()
        # Limitar quantidade
        max_videos = rate_tracker.get_remaining("gemini") - 2  # reservar para relatorio + scripts
        if max_videos < 5:
            print("  Rate limit muito proximo. Tente amanha.")
            return
        print(f"  Limitando a {max_videos} videos para caber no rate limit")
        videos = videos[:max_videos]

    content_analyzer = ContentAnalyzer(niche=NICHE)
    videos = content_analyzer.analyze_all(videos)
    content_analyzer.save_analyses(videos)
    report = content_analyzer.generate_report(videos)
    rate_tracker.track("gemini", len([v for v in videos if v.get("content_analysis")]) + 1)

    analyzed_count = sum(1 for v in videos if v.get("content_analysis"))
    print(f"\n  Videos analisados com sucesso: {analyzed_count}")

    if analyzed_count == 0:
        print("\nNenhum video analisado com sucesso. Verifique os logs acima.")
        return

    # 7. Gerar roteiros
    print("\n" + "=" * 60)
    print("GERANDO ROTEIROS")
    print("=" * 60)

    generator = ScriptGenerator(niche=NICHE)
    scripts = generator.generate_scripts(
        videos=videos,
        topic="Sistema de chat com IA integrado + automacao de atendimento + CRM",
        niche=NICHE,
        style="educativo",
        num_scripts=3,
        duration_seconds=60,
    )
    rate_tracker.track("gemini", 3 + 1)  # 3 scripts + 1 brief

    # 8. Salvar estado completo
    state_path = DATA_DIR / "pipeline_state.json"
    with open(state_path, "w", encoding="utf-8") as f:
        serializable = [dict(v) for v in videos]
        json.dump(serializable, f, ensure_ascii=False, indent=2, default=str)

    # 9. Resumo
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETO!")
    print("=" * 60)
    print(f"\n  Nicho: {NICHE}")
    print(f"  Videos processados: {len(videos)}")
    print(f"  Videos analisados: {analyzed_count}")
    print(f"  Roteiros gerados: {len(scripts)}")
    print(f"\n  Arquivos em {OUTPUT_DIR}/:")
    print(f"    relatorio_viral.md    — Relatorio de analise")
    print(f"    content_analyses.json — Analises detalhadas")
    print(f"    roteiros.md           — Roteiros em Markdown")
    print(f"    roteiros.json         — Roteiros em JSON")

    rate_tracker.print_status()


if __name__ == "__main__":
    run_pipeline()
