"""
=============================================================
MODULO 3: TRANSCRITOR (Groq Whisper -- GRATUITO)
=============================================================
Transcreve o audio dos videos usando Groq (Whisper gratis).
Groq roda Whisper em hardware ultra-rapido -- gratis e ~10x mais
rapido que a API paga da OpenAI.

Inclui:
- Processamento paralelo (ThreadPoolExecutor, 3 workers)
- Classificacao de ganchos (tipo + score de efetividade)
- Retry com backoff exponencial
"""

import json
import os
import re
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from groq import Groq
from config import GROQ_API_KEY, TRANSCRIPTION, DATA_DIR
from modules.retry import groq_retry


class Transcriber:
    """Transcricao de audio usando Groq Whisper (gratuito)."""

    # Rate limiting: max 3 requests concorrentes para Groq
    _rate_lock = threading.Lock()
    _last_request_time = 0.0
    _min_interval = 0.5  # 500ms entre requests

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def transcribe_all(self, videos: list[dict], max_workers: int = 3) -> list[dict]:
        """
        Transcreve todos os videos da lista em paralelo.

        Args:
            videos: Lista de dicts (precisa ter 'local_audio_path')
            max_workers: Numero maximo de workers paralelos

        Returns:
            Lista atualizada com transcricoes
        """
        print("\n" + "=" * 60)
        print("TRANSCREVENDO AUDIOS (Groq Whisper -- Gratuito)")
        print("=" * 60)

        # Separar videos com e sem audio
        to_transcribe = []
        for video in videos:
            audio_path = video.get("local_audio_path")
            if not audio_path or not Path(audio_path).exists():
                print(f"  Aviso: Audio nao encontrado para {video['id']}")
                video["transcription"] = None
            else:
                to_transcribe.append(video)

        if not to_transcribe:
            print("  Nenhum audio para transcrever")
            return videos

        # Processar em paralelo
        print(f"  Transcrevendo {len(to_transcribe)} audios com {max_workers} workers...")

        def _process_video(video):
            audio_path = video["local_audio_path"]
            try:
                result = self._transcribe_file(audio_path)
                # Classificar gancho
                if result and result.get("hook_text"):
                    hook_info = self._classify_hook(result["hook_text"], result["text"])
                    result["hook_classification"] = hook_info
                return video["id"], result, None
            except Exception as e:
                return video["id"], None, str(e)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_process_video, v): v for v in to_transcribe}

            completed = 0
            for future in as_completed(futures):
                video = futures[future]
                video_id, result, error = future.result()
                completed += 1

                if error:
                    print(f"  [{completed}/{len(to_transcribe)}] ERRO {video_id}: {error}")
                    video["transcription"] = None
                else:
                    video["transcription"] = result
                    word_count = result.get("word_count", 0) if result else 0
                    print(f"  [{completed}/{len(to_transcribe)}] OK: {video_id} — {word_count} palavras")
                    if result and result.get("hook_text"):
                        print(f"    Hook: \"{result['hook_text'][:80]}\"")
                    if result and result.get("hook_classification"):
                        hc = result["hook_classification"]
                        print(f"    Tipo: {hc.get('tipo', '?')} | Score: {hc.get('score', '?')}/10")

        transcribed = sum(1 for v in videos if v.get("transcription"))
        print(f"\n  {transcribed}/{len(videos)} videos transcritos")
        return videos

    @groq_retry
    def _transcribe_file(self, audio_path: str) -> dict:
        """
        Transcreve um arquivo de audio individual via Groq.
        Com rate limiting para evitar exceder limites.

        Returns:
            Dict com text, segments, hook_text, words_per_minute, etc.
        """
        # Rate limiting
        with self._rate_lock:
            now = time.time()
            elapsed = now - Transcriber._last_request_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            Transcriber._last_request_time = time.time()

        # Groq tem limite de 25MB por arquivo
        file_size = os.path.getsize(audio_path)
        if file_size > 25 * 1024 * 1024:
            print(f"    Aviso: Arquivo muito grande ({file_size // 1024 // 1024}MB), pulando...")
            return {"text": "", "hook_text": "", "segments": [], "total_duration": 0, "word_count": 0, "words_per_minute": 0}

        with open(audio_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model=TRANSCRIPTION["model"],
                file=audio_file,
                language=TRANSCRIPTION["language"],
                response_format=TRANSCRIPTION["response_format"],
                timestamp_granularities=["segment"],
            )

        # Normalizar resposta para dict (Groq pode retornar objeto ou dict)
        if hasattr(response, "model_dump"):
            resp = response.model_dump()
        elif isinstance(response, dict):
            resp = response
        else:
            resp = {"text": str(getattr(response, "text", "")), "segments": list(getattr(response, "segments", []))}

        full_text = resp.get("text", "")
        raw_segments = resp.get("segments") or []

        segments = []
        hook_text = ""

        for seg in raw_segments:
            # Normalizar cada segmento para dict
            if not isinstance(seg, dict):
                seg = seg.model_dump() if hasattr(seg, "model_dump") else vars(seg)

            start = round(float(seg.get("start", 0)), 2)
            end = round(float(seg.get("end", 0)), 2)
            text = str(seg.get("text", "")).strip()

            segment_data = {
                "start": start,
                "end": end,
                "text": text,
                "duration": round(end - start, 2),
            }
            segments.append(segment_data)

            if start < 3.0:
                hook_text += text + " "

        total_duration = segments[-1]["end"] if segments else 0
        word_count = len(full_text.split())
        wpm = round((word_count / total_duration) * 60) if total_duration > 0 else 0

        return {
            "text": full_text.strip(),
            "hook_text": hook_text.strip(),
            "segments": segments,
            "total_duration": round(total_duration, 2),
            "word_count": word_count,
            "words_per_minute": wpm,
        }

    def _classify_hook(self, hook_text: str, full_text: str = "") -> dict:
        """
        Classifica o tipo do gancho e calcula score de efetividade.

        Tipos:
        - pergunta: comeca com pergunta
        - estatistica: contem numeros/dados
        - dor: expoe problema/dor
        - historia: comeca com narrativa pessoal
        - controversia: opiniao forte/contraintuitiva
        - comando: imperativo direto
        - outro: nao classificado

        Returns:
            Dict com tipo, score (1-10), motivo
        """
        hook_lower = hook_text.lower().strip()

        # Detectar tipo
        hook_type = "outro"
        score = 5
        motivo = ""

        # Pergunta
        if "?" in hook_text or hook_lower.startswith(("voce", "você", "por que", "como", "qual", "quando", "o que", "ja ", "já ")):
            hook_type = "pergunta"
            score = 7
            motivo = "perguntas geram curiosidade e engajamento mental"

        # Estatistica/numero
        elif re.search(r'\d+[%kKmM]|\d{2,}|R\$|US\$|\d+\s*(mil|milhao|milhões|vezes|x)', hook_text):
            hook_type = "estatistica"
            score = 8
            motivo = "dados concretos geram credibilidade e choque"

        # Comando/imperativo
        elif hook_lower.startswith(("para", "pare", "olha", "veja", "escuta", "presta", "nunca", "sempre", "faz", "faca", "faça")):
            hook_type = "comando"
            score = 7
            motivo = "comandos diretos capturam atencao por autoridade"

        # Historia pessoal
        elif hook_lower.startswith(("eu ", "quando eu", "ha ", "há ", "era ")):
            hook_type = "historia"
            score = 6
            motivo = "historias pessoais geram conexao emocional"

        # Controversia
        elif any(w in hook_lower for w in ["ninguem", "ninguém", "mentira", "errado", "mito", "verdade que", "nao funciona", "pare de"]):
            hook_type = "controversia"
            score = 8
            motivo = "controversia gera forte reacao emocional e debate"

        # Dor/problema
        elif any(w in hook_lower for w in ["problema", "erro", "perdendo", "cuidado", "perigo", "dor", "sofr", "dificil", "difícil"]):
            hook_type = "dor"
            score = 7
            motivo = "expor dores gera identificacao e urgencia"

        # Ajustes de score
        hook_word_count = len(hook_text.split())

        # Ganchos muito curtos (1-3 palavras) — alto impacto
        if hook_word_count <= 3 and hook_word_count > 0:
            score = min(score + 1, 10)
            motivo += " | gancho curto e impactante"

        # Ganchos com palavras de poder
        power_words = {"gratis", "grátis", "segredo", "revelado", "proibido", "urgente",
                       "exclusivo", "garantido", "comprovado", "simples", "rapido", "rápido",
                       "facil", "fácil", "dinheiro", "lucro", "resultado"}
        if any(pw in hook_lower for pw in power_words):
            score = min(score + 1, 10)
            motivo += " | contem palavras de poder"

        return {
            "tipo": hook_type,
            "score": score,
            "motivo": motivo.strip(" |"),
            "word_count": hook_word_count,
        }

    def save_transcriptions(self, videos: list[dict], filename: str = "transcriptions.json"):
        """Salva transcricoes em arquivo separado."""
        transcriptions = {}
        for v in videos:
            if v.get("transcription"):
                transcriptions[v["id"]] = {
                    "platform": v["platform"],
                    "author": v["author"],
                    "transcription": v["transcription"],
                }

        filepath = DATA_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(transcriptions, f, ensure_ascii=False, indent=2)
        print(f"  Transcricoes salvas em: {filepath}")
        return filepath
