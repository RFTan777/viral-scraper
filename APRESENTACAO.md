# VIRAL SCRAPER — Documento de Apresentação

**Sistema completo de scraping, análise e geração de roteiros para conteúdo viral**

---

## Visão Geral

O Viral Scraper é um pipeline automatizado de 6 fases que coleta vídeos virais do TikTok e Instagram, analisa profundamente seus padrões de sucesso e gera roteiros de venda otimizados para B2B/PMEs. O sistema transforma dados brutos de redes sociais em inteligência acionável para criação de conteúdo.

**Stack tecnológica:** Python | Apify API | Groq Whisper | FFmpeg | Google Gemini 2.5 Flash

**Custo operacional:** Gratuito (todas as APIs possuem tier gratuito suficiente)

---

## Arquitetura do Pipeline

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  FASE 1      │    │  FASE 2      │    │  FASE 3      │
│  Scraping    │───▶│  Download    │───▶│  Transcrição │
│  (Apify)     │    │  (yt-dlp)    │    │  (Whisper)   │
└──────────────┘    └──────────────┘    └──────────────┘
                                               │
                                               ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  FASE 6      │    │  FASE 5      │    │  FASE 4      │
│  Roteiros    │◀───│  Análise de  │◀───│  Análise de  │
│  (Gemini)    │    │  Conteúdo    │    │  Vídeo       │
└──────────────┘    │  (Gemini)    │    │  (FFmpeg)    │
                    └──────────────┘    └──────────────┘
```

---

## Estrutura de Diretórios

```
viral-scraper/
├── main.py                    # Orquestrador principal (CLI + menu interativo)
├── config.py                  # Configuração central (APIs, diretórios, parâmetros)
├── requirements.txt           # Dependências Python
├── modules/
│   ├── scraper.py             # Fase 1 — Coleta de vídeos
│   ├── downloader.py          # Fase 2 — Download de vídeos
│   ├── transcriber.py         # Fase 3 — Transcrição de áudio
│   ├── video_analyzer.py      # Fase 4 — Análise técnica de vídeo
│   ├── content_analyzer.py    # Fase 5 — Desconstrução de conteúdo
│   └── script_generator.py    # Fase 6 — Geração de roteiros
├── data/
│   ├── videos/                # Vídeos baixados (.mp4)
│   ├── audio/                 # Áudios extraídos (.mp3)
│   ├── frames/                # Frames-chave extraídos (.jpg)
│   ├── scraped_videos.json    # Dados brutos do scraping
│   ├── transcriptions.json    # Transcrições com timestamps
│   ├── video_analysis.json    # Análises técnicas de vídeo
│   └── pipeline_state.json    # Estado completo do pipeline
└── output/
    ├── content_analyses.json  # Desconstruções detalhadas
    ├── relatorio_viral.md     # Relatório estratégico consolidado
    ├── roteiros.json          # Roteiros em formato estruturado
    └── roteiros.md            # Roteiros formatados para leitura
```

---

## Modos de Execução

| Comando                   | Descrição                                       |
|---------------------------|-------------------------------------------------|
| `python main.py`          | Menu interativo com todas as opções              |
| `python main.py --full`   | Pipeline completo automatizado (Fases 1 a 6)    |
| `python main.py --scrape-only`  | Apenas scraping (Fase 1)                   |
| `python main.py --analyze-only` | Apenas análise (requer dados existentes)   |
| `python main.py --scripts-only` | Apenas roteiros (requer análise existente) |

O **menu interativo** oferece 5 opções: pipeline completo, scraping isolado, análise isolada, geração de roteiros isolada e visualização do último relatório.

---

## FASE 1 — Scraping (Módulo: `scraper.py`)

**Classe:** `ApifyScraper`
**API utilizada:** Apify (actors de terceiros para TikTok e Instagram)
**Objetivo:** Coletar vídeos virais com métricas de engajamento

### Como Funciona

1. **Configuração da busca** — O usuário define:
   - Plataformas: TikTok, Instagram ou ambas
   - Tipo de busca: por hashtags, perfis específicos ou palavras-chave

2. **Execução dos Actors Apify** — O sistema inicia actors remotos no Apify:
   - **TikTok:** Actor de scraping gratuito (até 20 vídeos por execução)
   - **Instagram:** Actor oficial do Apify (filtra apenas Reels/vídeos)
   - Polling a cada 5 segundos até conclusão (timeout de 300s)

3. **Normalização de dados** — Cada vídeo é padronizado para um formato comum:

| Campo             | Descrição                                |
|-------------------|------------------------------------------|
| `platform`        | "tiktok" ou "instagram"                  |
| `url`             | URL pública do vídeo                     |
| `video_url`       | URL direta do arquivo de vídeo           |
| `description`     | Legenda/texto do post                    |
| `author`          | Nome do criador                          |
| `author_followers`| Número de seguidores                     |
| `views`           | Visualizações                            |
| `likes`           | Curtidas                                 |
| `comments`        | Comentários                              |
| `shares`          | Compartilhamentos                        |
| `saves`           | Salvamentos                              |
| `engagement_rate` | Taxa de engajamento calculada (%)        |
| `duration`        | Duração em segundos                      |
| `hashtags`        | Lista de hashtags                        |
| `music`           | Música/som utilizado                     |
| `created_at`      | Data de criação                          |
| `cover_url`       | URL da thumbnail                         |

4. **Filtragem por performance:**
   - TikTok: mínimo 100.000 views
   - Instagram: mínimo 50.000 views

5. **Ordenação configurável:** por engajamento (padrão), views ou data

6. **Persistência:** Salva em `data/scraped_videos.json`

### Cálculo de Engajamento

- **TikTok:** `(likes + comments + shares) / views * 100`
- **Instagram:** `(likes + comments) / views * 100`

---

## FASE 2 — Download (Módulo: `downloader.py`)

**Classe:** `VideoDownloader`
**Ferramentas:** Requests (download direto) + yt-dlp (fallback) + FFmpeg (extração de áudio)
**Objetivo:** Baixar vídeos e extrair áudio para análise local

### Como Funciona

1. **Download com estratégia dupla:**
   - **Tentativa 1:** Download direto via URL do vídeo (`video_url`) usando Requests com streaming
   - **Tentativa 2 (fallback):** Download via `yt-dlp` usando a URL pública do post
   - Skip automático de vídeos já baixados (cache local)

2. **Extração de áudio via FFmpeg:**
   - Formato de saída: MP3
   - Codec: libmp3lame a 128kbps
   - Sample rate: 16kHz (otimizado para transcrição por voz)
   - Timeout de 60 segundos por extração

3. **Outputs adicionados a cada vídeo:**
   - `local_video_path` — Caminho do arquivo .mp4 baixado
   - `local_audio_path` — Caminho do arquivo .mp3 extraído

### Formato de Nomes

- Vídeos: `{plataforma}_{id}.mp4` (ex: `tiktok_7284932.mp4`)
- Áudios: `{id}.mp3`

---

## FASE 3 — Transcrição (Módulo: `transcriber.py`)

**Classe:** `Transcriber`
**API utilizada:** Groq (Whisper Large V3 — gratuito, ultrarrápido)
**Objetivo:** Transcrever o áudio de cada vídeo com timestamps detalhados

### Como Funciona

1. **Validação de arquivo:**
   - Verifica existência do arquivo de áudio
   - Limite de 25MB por arquivo (restrição da API Groq)

2. **Transcrição via Groq Whisper:**
   - Modelo: `whisper-large-v3` (melhor qualidade disponível)
   - Idioma: Português (configurável)
   - Formato de resposta: `verbose_json` com segmentos timestampados

3. **Processamento dos resultados:**

| Dado Extraído         | Descrição                                     |
|-----------------------|-----------------------------------------------|
| `text`                | Transcrição completa do vídeo                 |
| `hook_text`           | Texto dos primeiros 3 segundos (gancho verbal)|
| `segments`            | Lista de segmentos com start, end, text       |
| `total_duration`      | Duração total do áudio em segundos            |
| `word_count`          | Contagem total de palavras                    |
| `words_per_minute`    | Velocidade de fala (WPM)                      |

4. **Identificação do Hook Verbal:**
   - Extrai automaticamente todo texto falado nos primeiros 3 segundos
   - Crucial para a análise posterior do gancho de atenção

5. **Persistência:** Salva em `data/transcriptions.json`

---

## FASE 4 — Análise de Vídeo (Módulo: `video_analyzer.py`)

**Classe:** `VideoAnalyzer`
**Ferramentas:** FFmpeg + FFprobe (executáveis locais)
**Objetivo:** Analisar tecnicamente a edição, ritmo e elementos visuais de cada vídeo

### Como Funciona

1. **Extração de metadados via FFprobe:**
   - Duração precisa do vídeo
   - Resolução (largura x altura)
   - FPS (frames por segundo)
   - Codec de vídeo utilizado
   - Presença de faixa de áudio

2. **Detecção de cortes via FFmpeg Scene Filter:**
   - Usa o filtro `select='gt(scene, threshold)'` para detectar mudanças de cena
   - Threshold padrão: 0.27 (27% de mudança entre frames consecutivos)
   - Parse do stderr do FFmpeg para extrair timestamps via regex
   - Timeout de 120 segundos por análise

3. **Cálculo de métricas de edição:**

| Métrica                  | Descrição                                           |
|--------------------------|-----------------------------------------------------|
| `total_cuts`             | Número total de cortes detectados                   |
| `cuts_per_minute`        | Frequência de cortes por minuto                     |
| `avg_segment_duration`   | Duração média entre cortes (segundos)               |
| `cut_timestamps`         | Lista de timestamps de cada corte                   |
| `editing_pace`           | Classificação do ritmo de edição                    |

4. **Classificação de ritmo:**
   - `sem_cortes` — 0 cortes/min
   - `lento` — < 5 cortes/min
   - `moderado` — 5 a 15 cortes/min
   - `rápido` — 15 a 30 cortes/min
   - `muito_rápido` — > 30 cortes/min

5. **Extração de frames-chave** (8 frames por vídeo):
   - Frame 0 (thumbnail/hook visual — sempre extraído)
   - Frames nos momentos de corte (até metade dos frames)
   - Frames distribuídos uniformemente para cobrir o restante
   - Formato: JPEG com qualidade alta (q:v 2)
   - Salvos em `data/frames/{video_id}/`

6. **Persistência:** Salva em `data/video_analysis.json`

---

## FASE 5 — Análise de Conteúdo (Módulo: `content_analyzer.py`)

**Classe:** `ContentAnalyzer`
**API utilizada:** Google Gemini 2.5 Flash (1500 req/dia gratuitas)
**Objetivo:** Desconstrução profunda de cada vídeo como peça de venda B2B

### Como Funciona

1. **Montagem do contexto multimodal:**
   - Envia até 4 frames-chave do vídeo como imagens (base64) ao Gemini
   - Inclui transcrição completa, hook verbal e segmentos com timestamps
   - Inclui métricas de engajamento e dados de edição

2. **Desconstrução nos 4 pilares de venda B2B:**

#### Pilar 1 — Gancho de Dor
- Dor do empresário identificada
- Tipo de gancho (cenário negativo, pergunta retórica, dado alarmante, provocação, etc.)
- Texto verbal e visual exato do gancho
- Gatilho emocional explorado (medo, frustração, inveja, urgência, vergonha)
- Persona-alvo específica
- Análise psicológica de eficácia

#### Pilar 2 — Ponte de Autoridade
- Tipo de prova social (case, demonstração, números, bastidores, depoimento)
- Posicionamento do criador
- Credenciais e resultados mencionados
- Transição da dor para a autoridade

#### Pilar 3 — Apresentação da Solução
- Tipo de solução (CRM, automação, funil, chatbot, dashboard)
- Método de apresentação (screencast, antes/depois, demonstração ao vivo)
- Ferramentas/plataformas mencionadas
- Nível técnico da linguagem
- Benefícios destacados e objeções antecipadas
- "Momento aha" — ponto exato onde o viewer entende o valor

#### Pilar 4 — CTA de Agendamento
- Tipo de CTA (link na bio, DM, WhatsApp, Calendly, formulário)
- Texto exato do chamado à ação
- Urgência aplicada (escassez, prazo, vagas limitadas)
- Oferta-isca (consultoria gratuita, diagnóstico, demonstração)
- Nível de fricção para o viewer

3. **Análises complementares extraídas:**

| Análise                     | Conteúdo                                                    |
|-----------------------------|-------------------------------------------------------------|
| Estrutura narrativa         | Framework usado, distribuição de tempo por bloco, transições|
| Entonação e performance     | Tom, variações por bloco, WPM, palavras de poder, jargões  |
| Produção e visual           | Cenário, enquadramento, screencast, elementos gráficos     |
| Pontos fortes               | 3-5 pontos fortes como peça de venda                        |
| Pontos fracos               | 2-3 pontos de melhoria                                      |
| Por que converte            | Explicação da eficácia do vídeo                              |
| Lições para replicar        | 3-5 táticas específicas e replicáveis                        |

4. **Geração de Relatório Consolidado:**
   - Compara todos os vídeos analisados
   - Identifica padrões de sucesso em ganchos, autoridade, demonstrações e CTAs
   - Gera um relatório estratégico em Markdown com 8 seções:
     1. Resumo Executivo
     2. Ganchos de Dor que Convertem
     3. Estratégias de Ponte de Autoridade
     4. Como Top Performers Apresentam a Solução
     5. CTAs que Geram Agendamentos
     6. Frameworks Narrativos Vencedores
     7. Padrões de Produção e Visual
     8. Plano de Ação (blueprint acionável)

5. **Persistência:**
   - Análises individuais: `output/content_analyses.json`
   - Relatório consolidado: `output/relatorio_viral.md`

---

## FASE 6 — Geração de Roteiros (Módulo: `script_generator.py`)

**Classe:** `ScriptGenerator`
**API utilizada:** Google Gemini 2.5 Flash (com system prompt especializado)
**Objetivo:** Gerar roteiros de venda ultra-detalhados para PMEs, baseados nos padrões reais dos vídeos analisados

### Como Funciona

1. **Extração de padrões dos vídeos desconstruídos:**
   - Ganchos de dor que funcionaram (tipo, texto, score, views)
   - Pontes de autoridade mais eficazes
   - Métodos de demonstração de solução
   - CTAs que geraram agendamentos
   - Frameworks narrativos e técnicas de retenção
   - Ferramentas/plataformas mencionadas
   - Palavras de poder B2B
   - Métricas médias (views, engajamento, duração, WPM)
   - Top 3 vídeos por engajamento como referência

2. **Geração de Brief Estratégico de Campanha:**
   - Diagnóstico de dores que ressoam com donos de PME
   - Arsenal de 5 ganchos agressivos prontos
   - Playbook de autoridade
   - Roteiro de demonstração (quais B-rolls usar)
   - Direção vocal (tom, ritmo, linguagem)
   - Direção visual (B-rolls obrigatórios por bloco)
   - CTA de implementação

3. **Geração de roteiros com abordagens variadas:**

| # | Abordagem               | Descrição                                                  |
|---|-------------------------|------------------------------------------------------------|
| 1 | Hemorragia de Caixa     | Abre com o empresário PERDENDO dinheiro agora               |
| 2 | Espião do Concorrente   | Mostra que o concorrente já usa IA e está à frente          |
| 3 | Flagrante no Atendimento| Pega o caos do atendimento manual no ato                    |
| 4 | ROI na Cara             | Abre com resultado concreto de um cliente                   |
| 5 | Diagnóstico Brutal      | Tom de consultor fazendo auditoria ao vivo                  |

4. **Estrutura de cada roteiro gerado:**

```
Roteiro
├── Título e conceito de venda
│   ├── Dor central atacada
│   ├── Solução oferecida
│   ├── Promessa mensurável ao empresário
│   └── Persona-alvo exata
│
├── Gancho de Dor (primeiros 2-3s)
│   ├── Texto exato da fala
│   ├── Nível de agressividade (1-10)
│   ├── Direção vocal (tom, volume, velocidade, pausas, ênfase)
│   ├── Texto na tela (posição, animação, timing)
│   ├── B-Roll do gancho (descrição exata, tipo, duração, transição)
│   └── Direção visual do apresentador (enquadramento, expressão, gesto)
│
├── Cenas detalhadas (6-10 cenas)
│   ├── Timestamp e bloco (FERIDA / AUTORIDADE / DEMONSTRAÇÃO / CTA)
│   ├── Função comercial da cena
│   ├── Fala com entonação detalhada
│   ├── B-Rolls específicos (descrição, tipo, duração, overlay)
│   ├── Visual do apresentador (enquadramento, ângulo, ação)
│   ├── Texto na tela (overlay, estilo, animação)
│   ├── Edição (tipo de corte, efeito, SFX, música)
│   └── Storytelling (técnica de retenção, estado mental do viewer)
│
├── Mapa de Venda (distribuição por %)
│   ├── 0-20% — Ferida Aberta
│   ├── 20-35% — Prova de Autoridade
│   ├── 35-75% — Demonstração da Solução
│   └── 75-100% — CTA de Agendamento
│
├── Arsenal de B-Rolls
│   ├── Caos do atendimento manual
│   ├── Telas do sistema/CRM
│   ├── Painéis de métricas
│   ├── Antes vs. Depois
│   └── Fluxos de IA/automação
│
├── CTA de Agendamento
│   ├── Tipo e texto exato
│   ├── Oferta-isca e urgência
│   └── Conexão com a dor inicial
│
├── Produção
│   ├── Cenário, iluminação, figurino
│   ├── Música sugerida e SFX
│   └── Monitor de apoio
│
└── Distribuição
    ├── Descrições para TikTok e Instagram
    ├── Hashtags (alcance + nicho + long tail)
    └── Melhor horário e dia de postagem
```

5. **System Prompt Especializado:**
   - Persona: estrategista de campanhas com +800 roteiros produzidos
   - Público definido: donos de PMEs (5 a 200 funcionários)
   - Framework rígido: FERIDA → AUTORIDADE → DEMONSTRAÇÃO → AGENDA
   - Regras inegociáveis: ganchos agressivos, B-rolls obrigatórios em toda cena, zero jargão técnico, CTA sempre de agendamento

6. **Persistência:**
   - Formato estruturado: `output/roteiros.json`
   - Formato legível: `output/roteiros.md` (formatado com seções, emojis e tabelas)

---

## Configurações Centrais (`config.py`)

### APIs Utilizadas

| Serviço            | Função                        | Custo         | Limite Gratuito          |
|--------------------|-------------------------------|---------------|--------------------------|
| Apify              | Scraping TikTok + Instagram   | $5/mês grátis | ~100-200 execuções/mês   |
| Groq (Whisper)     | Transcrição de áudio          | Gratuito      | Sem limite aparente      |
| Google Gemini      | Análise de conteúdo + roteiros| Gratuito      | 1500 req/dia             |

### Parâmetros de Scraping

| Parâmetro               | Valor Padrão | Descrição                         |
|-------------------------|--------------|-----------------------------------|
| `max_videos_tiktok`     | 20           | Máximo de vídeos por busca        |
| `max_videos_instagram`  | 20           | Máximo de reels por busca         |
| `min_views_tiktok`      | 100.000      | Filtro mínimo de views            |
| `min_views_instagram`   | 50.000       | Filtro mínimo de views            |
| `sort_by`               | engagement   | Critério de ordenação             |

### Parâmetros de Transcrição

| Parâmetro           | Valor Padrão        | Descrição                      |
|---------------------|---------------------|--------------------------------|
| `model`             | whisper-large-v3    | Modelo de transcrição          |
| `language`          | pt                  | Idioma alvo                    |
| `response_format`   | verbose_json        | Formato com timestamps         |

### Parâmetros de Análise de Vídeo

| Parâmetro           | Valor Padrão | Descrição                              |
|---------------------|--------------|----------------------------------------|
| `scene_threshold`   | 27.0         | Sensibilidade de detecção de cortes (%) |
| `frames_to_extract` | 8            | Frames-chave por vídeo                 |
| `hook_seconds`      | 3            | Duração do hook em segundos            |

### Parâmetros do Gemini

| Parâmetro                | Valor Padrão                        | Descrição              |
|--------------------------|-------------------------------------|------------------------|
| `model`                  | gemini-2.5-flash-preview-05-20      | Modelo de IA           |
| `max_tokens`             | 8192                                | Tokens máximos/resposta|
| `temperature`            | 0.7                                 | Criatividade (roteiros)|
| `temperature_analysis`   | 0.2                                 | Precisão (análise)     |

---

## Dependências

| Pacote                | Versão    | Função                                   |
|-----------------------|-----------|------------------------------------------|
| `groq`                | >= 0.11.0 | Cliente para API Groq (Whisper gratuito)  |
| `google-generativeai` | >= 0.8.0  | Cliente para API Gemini (análise + geração)|
| `requests`            | >= 2.31.0 | HTTP requests (Apify + downloads)         |
| `yt-dlp`              | >= 2024.1 | Download de vídeos (fallback)             |

**Requisito externo:** FFmpeg + FFprobe (executáveis na raiz do projeto)

---

## Fluxo de Dados

```
Entrada do Usuário
    │  (hashtags, perfis ou palavras-chave)
    ▼
┌─────────────────────────────────────────────────────┐
│ FASE 1: Scraping                                     │
│ → Apify coleta vídeos virais                         │
│ → Normalização + filtragem por views                 │
│ → Saída: scraped_videos.json                         │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│ FASE 2: Download                                     │
│ → Download direto ou via yt-dlp                      │
│ → Extração de áudio (MP3 16kHz)                      │
│ → Saída: data/videos/*.mp4 + data/audio/*.mp3        │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│ FASE 3: Transcrição                                  │
│ → Groq Whisper transcreve áudio                      │
│ → Extrai hook verbal (3s), WPM, segmentos            │
│ → Saída: transcriptions.json                         │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│ FASE 4: Análise de Vídeo                             │
│ → FFprobe extrai metadados técnicos                  │
│ → FFmpeg detecta cortes e extrai frames              │
│ → Classifica ritmo de edição                         │
│ → Saída: video_analysis.json + frames/               │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│ FASE 5: Análise de Conteúdo                          │
│ → Gemini desconstrui cada vídeo (texto + imagens)    │
│ → 4 pilares: Dor → Autoridade → Solução → CTA       │
│ → Gera relatório estratégico consolidado             │
│ → Saída: content_analyses.json + relatorio_viral.md  │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│ FASE 6: Geração de Roteiros                          │
│ → Extrai padrões vencedores dos vídeos               │
│ → Gera brief estratégico de campanha                 │
│ → Cria roteiros ultra-detalhados por abordagem       │
│ → Saída: roteiros.json + roteiros.md                 │
└─────────────────────────────────────────────────────┘
```

---

## Resumo do Pipeline Completo

| Fase | Módulo             | API/Ferramenta  | Input                      | Output                        | Tempo Estimado |
|------|--------------------|-----------------|----------------------------|-------------------------------|----------------|
| 1    | Scraping           | Apify           | Hashtags/perfis/keywords   | Lista de vídeos normalizados  | 1-5 min        |
| 2    | Download           | Requests/yt-dlp | URLs dos vídeos            | Arquivos .mp4 + .mp3 locais   | 2-10 min       |
| 3    | Transcrição        | Groq Whisper    | Arquivos .mp3              | Texto + timestamps + hook     | 1-3 min        |
| 4    | Análise de Vídeo   | FFmpeg/FFprobe  | Arquivos .mp4              | Cortes, frames, ritmo         | 1-5 min        |
| 5    | Análise de Conteúdo| Google Gemini   | Tudo anterior + frames     | Desconstrução B2B + relatório | 3-10 min       |
| 6    | Roteiros           | Google Gemini   | Padrões extraídos          | Roteiros de venda detalhados  | 3-8 min        |

**Tempo total estimado:** 10-40 minutos (depende da quantidade de vídeos)

---

*Documento gerado para o projeto Viral Scraper — Pipeline de inteligência para criação de conteúdo viral B2B*
