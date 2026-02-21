# Viral Scraper

Pipeline automatizado que coleta videos virais do TikTok e Instagram, analisa seus padroes de sucesso e gera roteiros otimizados para qualquer nicho.

**Scraping → Download → Transcricao → Analise de Video → Analise de Conteudo → Geracao de Roteiros**

## Pre-requisitos

- **Python 3.11+**
- **FFmpeg** (necessario para download, extracao de audio e analise de video)
- Chaves de API gratuitas (ver abaixo)

### Instalar FFmpeg

**Windows:**
1. Baixe em https://www.gyan.dev/ffmpeg/builds/ (versao "essentials")
2. Extraia `ffmpeg.exe` e `ffprobe.exe` na raiz do projeto

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Mac
brew install ffmpeg
```

## Instalacao

```bash
# 1. Clonar o repositorio
git clone https://github.com/RFTan777/viral-scraper.git
cd viral-scraper

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar chaves de API
cp .env.example .env
# Edite o arquivo .env com suas chaves reais
```

## Chaves de API (todas gratuitas)

| Servico | Para que serve | Onde obter |
|---------|---------------|------------|
| Apify | Scraping TikTok + Instagram | https://console.apify.com/account/integrations |
| Groq | Transcricao de audio (Whisper) | https://console.groq.com/keys |
| Google Gemini | Analise de conteudo + roteiros | https://aistudio.google.com/apikey |

Preencha as 3 chaves no arquivo `.env`:

```
APIFY_API_TOKEN=sua_chave_aqui
GROQ_API_KEY=sua_chave_aqui
GEMINI_API_KEY=sua_chave_aqui
```

## Como usar

```bash
# Menu interativo (recomendado)
python main.py

# Pipeline completo automatizado
python main.py --full

# Etapas individuais
python main.py --scrape-only
python main.py --analyze-only
python main.py --scripts-only
```

## Estrutura do projeto

```
viral-scraper/
├── main.py              # Orquestrador principal
├── config.py            # Configuracoes centrais
├── requirements.txt     # Dependencias Python
├── .env.example         # Modelo para chaves de API
├── modules/
│   ├── scraper.py       # Fase 1 — Coleta via Apify
│   ├── downloader.py    # Fase 2 — Download de videos
│   ├── transcriber.py   # Fase 3 — Transcricao (Groq Whisper)
│   ├── video_analyzer.py# Fase 4 — Analise tecnica (FFmpeg)
│   ├── content_analyzer.py # Fase 5 — Desconstrucao (Gemini)
│   ├── script_generator.py # Fase 6 — Roteiros (Gemini)
│   ├── content_filter.py   # Filtro de conteudo irrelevante
│   ├── checkpoint.py       # Resume do pipeline
│   ├── dedup.py            # Deduplicacao de videos
│   ├── rate_tracker.py     # Controle de rate limits
│   └── retry.py            # Retry com backoff exponencial
├── data/                # Gerado automaticamente (nao commitado)
└── output/              # Resultados gerados (nao commitado)
```

## Funcionalidades

- Scraping de videos virais do TikTok e Instagram por hashtags, perfis ou palavras-chave
- Download automatico com fallback (URL direta + yt-dlp)
- Transcricao ultrarapida via Groq Whisper (gratuito)
- Deteccao de cortes, ritmo de edicao e extracao de frames-chave
- Desconstrucao de conteudo com IA (Gemini) — adaptavel a qualquer nicho
- Geracao de roteiros ultra-detalhados com direcao de fala, B-rolls e producao
- Checkpoint/resume — retoma de onde parou se interrompido
- Deduplicacao — nao reprocessa videos ja analisados
- Filtro inteligente — remove dancas, trends e conteudo irrelevante
- Controle de rate limits das APIs
