"""
=============================================================
MODULO: FILTRO DE CONTEUDO
=============================================================
Filtra videos irrelevantes (dancas, trends, lipsync, etc.)
em dois estagios:

Stage A (pre-download): Blacklists de hashtags, keywords,
  descricao muito curta.
Stage B (pos-transcricao): word_count, WPM, e classificacao
  via Gemini (prompt leve).
"""

import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI


class ContentFilter:
    """Filtra videos irrelevantes em 2 estagios."""

    # ~40 termos de blacklist para hashtags e descricao
    HASHTAG_BLACKLIST = {
        # Danca/coreografia
        "dance", "danca", "dancinha", "coreografia", "choreography",
        "dancechallenge", "dancevideo", "dancetrend", "dancadobem",
        # Trends/challenges
        "challenge", "trend", "trending", "viral", "viralchallenge",
        "trendchallenge", "desafio",
        # Lipsync/musica
        "lipsync", "lipsynch", "lipsyncbattle", "dubsmash",
        "singing", "cantando", "karaoke",
        # Cosplay/POV/humor nao-fala
        "cosplay", "pov", "povs", "cosplayer",
        # Genericos irrelevantes
        "fyp", "foryou", "foryoupage", "parati", "fy", "fyppage",
        "xyzbca", "viral", "xuxa", "meme", "memes",
        # Conteudo visual sem fala
        "asmr", "satisfying", "oddlysatisfying", "slime",
    }

    DESCRIPTION_BLACKLIST_KEYWORDS = {
        "dancinha", "coreografia", "challenge", "lipsync", "cosplay",
        "pov:", "dueto comigo", "use esse som", "usa esse audio",
        "trend", "faz esse", "aprendendo a dancar",
    }

    MUSIC_BLACKLIST_KEYWORDS = {
        "original sound -", "som original -",
    }

    def __init__(self, niche: str = ""):
        self.niche = niche or "conteudo viral"
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=GEMINI["model"],
            generation_config={
                "max_output_tokens": 256,
                "temperature": 0.1,
            },
        )

    # -----------------------------------------
    # STAGE A: Pre-download (metadados)
    # -----------------------------------------

    def filter_stage_a(self, videos: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Filtra videos ANTES do download usando metadados.

        Returns:
            (aprovados, rejeitados)
        """
        print("\n" + "=" * 60)
        print(f"FILTRO STAGE A (pre-download) — Nicho: {self.niche}")
        print("=" * 60)

        approved = []
        rejected = []

        for video in videos:
            reason = self._check_stage_a(video)
            if reason:
                rejected.append({**video, "_rejection_reason": reason, "_rejection_stage": "A"})
                print(f"  REJEITADO: {video.get('author', '?')} — {reason}")
            else:
                approved.append(video)

        print(f"\n  Resultado: {len(approved)} aprovados, {len(rejected)} rejeitados")
        return approved, rejected

    def _check_stage_a(self, video: dict) -> str | None:
        """Verifica se o video deve ser rejeitado no Stage A. Retorna motivo ou None."""

        # 1. Blacklist de hashtags
        hashtags = {h.lower().strip() for h in video.get("hashtags", [])}
        blocked_tags = hashtags & self.HASHTAG_BLACKLIST
        if blocked_tags:
            return f"hashtag bloqueada: {', '.join(list(blocked_tags)[:3])}"

        # 2. Keywords na descricao
        description = (video.get("description") or "").lower()
        for kw in self.DESCRIPTION_BLACKLIST_KEYWORDS:
            if kw in description:
                return f"keyword na descricao: '{kw}'"

        # 3. Descricao muito curta (< 10 caracteres sem hashtags)
        desc_clean = description
        for tag in video.get("hashtags", []):
            desc_clean = desc_clean.replace(f"#{tag.lower()}", "").strip()
        if len(desc_clean.strip()) < 10 and not video.get("description", "").strip():
            return "descricao vazia ou muito curta"

        # 4. Keywords na musica (indicativo de trend)
        music = (video.get("music") or "").lower()
        # Musica com "original sound" geralmente e conteudo proprio (ok)
        # Mas se a descricao tambem e curta, pode ser danca
        for kw in self.MUSIC_BLACKLIST_KEYWORDS:
            if kw in music and len(desc_clean.strip()) < 20:
                return f"musica suspeita + descricao curta: '{kw}'"

        return None

    # -----------------------------------------
    # STAGE B: Pos-transcricao
    # -----------------------------------------

    def filter_stage_b(self, videos: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Filtra videos APOS transcricao usando analise de conteudo.

        Returns:
            (aprovados, rejeitados)
        """
        print("\n" + "=" * 60)
        print(f"FILTRO STAGE B (pos-transcricao) — Nicho: {self.niche}")
        print("=" * 60)

        approved = []
        rejected = []

        for video in videos:
            transcription = video.get("transcription")
            if not transcription:
                # Sem transcricao = provavelmente musica/danca
                rejected.append({**video, "_rejection_reason": "sem transcricao", "_rejection_stage": "B"})
                print(f"  REJEITADO: {video.get('author', '?')} — sem transcricao")
                continue

            reason = self._check_stage_b(video, transcription)
            if reason:
                rejected.append({**video, "_rejection_reason": reason, "_rejection_stage": "B"})
                print(f"  REJEITADO: {video.get('author', '?')} — {reason}")
            else:
                approved.append(video)

        print(f"\n  Resultado: {len(approved)} aprovados, {len(rejected)} rejeitados")
        return approved, rejected

    def _check_stage_b(self, video: dict, transcription: dict) -> str | None:
        """Verifica se o video deve ser rejeitado no Stage B. Retorna motivo ou None."""

        word_count = transcription.get("word_count", 0)
        wpm = transcription.get("words_per_minute", 0)

        # 1. Poucas palavras = musica/danca (nao e fala)
        if word_count < 10:
            return f"poucas palavras ({word_count}) — provavelmente musica/danca"

        # 2. WPM muito baixo = nao e fala continua
        if wpm > 0 and wpm < 40:
            return f"WPM muito baixo ({wpm}) — nao e conteudo falado"

        # 3. Classificacao via Gemini (prompt leve de 256 tokens)
        try:
            is_relevant = self._classify_with_gemini(video, transcription)
            if not is_relevant:
                return f"Gemini classificou como irrelevante para nicho '{self.niche}'"
        except Exception as e:
            # Se Gemini falhar, aprovar (melhor falso positivo que perder conteudo)
            print(f"    Aviso: Gemini classificacao falhou ({e}), aprovando por padrao")

        return None

    def _classify_with_gemini(self, video: dict, transcription: dict) -> bool:
        """Usa Gemini para classificar se o conteudo e relevante ao nicho. Retorna True se relevante."""

        text_preview = transcription.get("text", "")[:300]
        description = (video.get("description") or "")[:200]

        prompt = f"""Classifique se este video e conteudo RELEVANTE para o nicho "{self.niche}".

Descricao: {description}
Transcricao (inicio): {text_preview}

Responda APENAS "SIM" ou "NAO".
- SIM = conteudo falado/educativo/informativo relevante ao nicho "{self.niche}"
- NAO = danca, trend, lipsync, musica, conteudo sem fala, ou completamente fora do nicho

Resposta:"""

        response = self.model.generate_content(prompt)
        try:
            answer = response.text.strip().upper()
        except (ValueError, AttributeError):
            return True  # Em caso de erro, aprovar

        return "SIM" in answer
