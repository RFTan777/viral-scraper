"""
=============================================================
CONFIGURACAO CENTRAL DO VIRAL SCRAPER
=============================================================
VERSAO GRATUITA -- Usa Groq (Whisper gratis) + Gemini (gratis)
Preencha suas chaves de API no arquivo .env antes de rodar.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Carregar variaveis de ambiente do .env
load_dotenv(Path(__file__).parent / ".env")

# ---------------------------------------------
# CHAVES DE API (TODAS GRATUITAS)
# ---------------------------------------------

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# FAL_AI_KEY e opcional — necessaria apenas para gerar videos com IA
# Crie sua chave gratuita em: https://fal.ai/dashboard/keys
FAL_AI_KEY = os.getenv("FAL_AI_KEY", "")

# Validar chaves obrigatorias
_missing = []
if not APIFY_API_TOKEN:
    _missing.append("APIFY_API_TOKEN")
if not GROQ_API_KEY:
    _missing.append("GROQ_API_KEY")
if not GEMINI_API_KEY:
    _missing.append("GEMINI_API_KEY")

if _missing:
    print(f"ERRO: Chaves de API ausentes: {', '.join(_missing)}")
    print("Crie um arquivo .env na raiz do projeto com suas chaves.")
    print("Use .env.example como modelo.")
    sys.exit(1)

# ---------------------------------------------
# DIRETORIOS
# ---------------------------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
VIDEOS_DIR = DATA_DIR / "videos"
AUDIO_DIR = DATA_DIR / "audio"
FRAMES_DIR = DATA_DIR / "frames"

# FFmpeg (executavel solto na raiz do projeto)
FFMPEG_DIR = BASE_DIR

# Criar diretorios automaticamente
for d in [DATA_DIR, OUTPUT_DIR, VIDEOS_DIR, AUDIO_DIR, FRAMES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------
# CONFIGURACAO DE NICHO (DINAMICO)
# ---------------------------------------------

NICHE = {
    "default_niche": "",
    "default_style": "educativo",
    "num_scripts": 3,
    "duration_seconds": 60,
}

# ---------------------------------------------
# CONFIGURACOES DE SCRAPING
# ---------------------------------------------

SCRAPING = {
    "max_videos_tiktok": 20,
    "max_videos_instagram": 20,
    "min_views_tiktok": 100_000,
    "min_views_instagram": 50_000,
    "sort_by": "engagement",
    "tiktok_actor": "clockworks~free-tiktok-scraper",
    "instagram_actor": "apify~instagram-scraper",
}

# ---------------------------------------------
# CONFIGURACOES DE TRANSCRICAO (Groq Whisper)
# ---------------------------------------------

TRANSCRIPTION = {
    "model": "whisper-large-v3",   # melhor modelo, gratis no Groq
    "language": "pt",
    "response_format": "verbose_json",
}

# ---------------------------------------------
# CONFIGURACOES DE ANALISE DE VIDEO
# ---------------------------------------------

VIDEO_ANALYSIS = {
    "scene_threshold": 27.0,
    "frames_to_extract": 8,
    "hook_seconds": 3,
}

# ---------------------------------------------
# CONFIGURACOES DO GEMINI
# ---------------------------------------------

GEMINI = {
    "model": "gemini-2.5-flash",
    "max_tokens": 65536,
    "temperature": 0.7,             # para roteiros (criativo)
    "temperature_analysis": 0.2,    # para analise (preciso)
}

# ---------------------------------------------
# CONFIGURACOES DE IA DE VIDEO (fal.ai) — OPCIONAL
# ---------------------------------------------

VIDEO_AI = {
    "modelo_padrao": "kling",       # kling | kling_pro | wan | wan_14b | cogvideo
    "max_cenas_por_roteiro": 5,     # limita quantas cenas gerar para economizar creditos
    "gerar_automatico": False,      # True = gera sem perguntar apos roteiro pronto
    "baixar_clips": True,           # True = baixa os clips gerados localmente
}
