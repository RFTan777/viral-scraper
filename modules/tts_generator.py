"""
=============================================================
MODULO: TTS GENERATOR — Voiceover por cena (edge-tts)
=============================================================
Gera narracoes em audio MP3 por cena usando Microsoft edge-tts.
Vozes pt-BR naturais, gratuitas, sem API key.

Instalar: pip install edge-tts

Vozes recomendadas:
  pt-BR-FranciscaNeural  — feminina, fluente (educativo/conteudo)
  pt-BR-AntonioNeural    — masculino, assertivo (vendas/autoridade)
  pt-BR-ThalitaMultilingualNeural — feminina moderna
=============================================================
"""

import asyncio
import subprocess
import sys
from pathlib import Path

from config import BASE_DIR, OUTPUT_DIR


# -----------------------------------------------------------
# VOZES DISPONIVEIS
# -----------------------------------------------------------

VOZES = {
    "feminino":  "pt-BR-FranciscaNeural",
    "masculino": "pt-BR-AntonioNeural",
    "feminino2": "pt-BR-ThalitaMultilingualNeural",
    "masculino2": "pt-BR-HumbertoNeural",
}

FFMPEG = str(BASE_DIR / "ffmpeg.exe") if (BASE_DIR / "ffmpeg.exe").exists() else "ffmpeg"
TTS_DIR_DEFAULT = OUTPUT_DIR / "tts_audio"


class TTSGenerator:
    """Gera audio TTS para cada cena de um roteiro."""

    def __init__(self, voice: str = "feminino", output_dir: Path = None):
        self.voice_key = voice
        # Aceita tanto o nome amigavel quanto o ID completo da voz
        self.voice = VOZES.get(voice, voice)
        self.output_dir = Path(output_dir) if output_dir else TTS_DIR_DEFAULT
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------
    # GERACAO PARA ROTEIRO COMPLETO
    # ----------------------------------------------------------

    def generate_for_script(self, script: dict) -> list[dict]:
        """
        Gera audio TTS para todas as cenas do roteiro.

        Retorna lista de dicts:
          { cena_numero, audio_path, duration_sec, texto, bloco, momento }
        """
        cenas = script.get("cenas", [])
        titulo = script.get("titulo", "roteiro")
        safe = _safe_name(titulo)

        print(f"\n{'=' * 60}")
        print(f"  TTS — {len(cenas)} cenas | Voz: {self.voice}")
        print(f"{'=' * 60}")

        results = []
        for cena in cenas:
            numero = cena.get("numero", len(results) + 1)
            fala = cena.get("fala", {})
            texto = fala.get("texto", "") if isinstance(fala, dict) else str(fala or "")

            if not texto.strip():
                print(f"  [{numero}] SKIP — cena sem texto")
                results.append({
                    "cena_numero": numero,
                    "audio_path": None,
                    "duration_sec": 0.0,
                    "texto": "",
                    "bloco": cena.get("bloco", ""),
                    "momento": cena.get("momento", ""),
                })
                continue

            rate = _calc_rate(fala)
            audio_path = self.output_dir / f"{safe}_cena{numero:02d}.mp3"

            print(f"\n  [{numero}/{len(cenas)}] {cena.get('bloco','')} | rate={rate}")
            print(f"    Texto: {texto[:80]}{'...' if len(texto)>80 else ''}")

            success = self._synthesize(texto, audio_path, rate)
            if not success:
                print(f"    FALHA no TTS da cena {numero}")
                results.append({
                    "cena_numero": numero,
                    "audio_path": None,
                    "duration_sec": 0.0,
                    "texto": texto,
                    "bloco": cena.get("bloco", ""),
                    "momento": cena.get("momento", ""),
                })
                continue

            duration = self._get_audio_duration(audio_path)
            print(f"    OK: {audio_path.name} ({duration:.2f}s)")

            results.append({
                "cena_numero": numero,
                "audio_path": str(audio_path),
                "duration_sec": duration,
                "texto": texto,
                "bloco": cena.get("bloco", ""),
                "momento": cena.get("momento", ""),
            })

        total = sum(r["duration_sec"] for r in results)
        print(f"\n  Total TTS: {total:.1f}s ({total/60:.1f} min)")
        return results

    # ----------------------------------------------------------
    # SINTESE
    # ----------------------------------------------------------

    def _synthesize(self, texto: str, output_path: Path, rate: str) -> bool:
        """Gera audio MP3 via edge-tts. Retorna True se sucesso."""
        try:
            import edge_tts
        except ImportError:
            print("  ERRO: edge-tts nao instalado. Execute: python -m pip install edge-tts")
            return False

        try:
            # Windows Python 3.14 — usar asyncio.run() diretamente
            asyncio.run(self._async_synthesize(texto, output_path, rate))
            return output_path.exists() and output_path.stat().st_size > 100
        except RuntimeError:
            # Fallback se event loop já estiver rodando
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._async_synthesize(texto, output_path, rate))
                return output_path.exists() and output_path.stat().st_size > 100
            finally:
                loop.close()
        except Exception as e:
            print(f"    ERRO TTS: {e}")
            return False

    async def _async_synthesize(self, texto: str, output_path: Path, rate: str):
        import edge_tts
        tts = edge_tts.Communicate(texto, self.voice, rate=rate)
        await tts.save(str(output_path))

    # ----------------------------------------------------------
    # DURACAO VIA FFMPEG
    # ----------------------------------------------------------

    def _get_audio_duration(self, path: Path) -> float:
        """
        Mede duracao do audio usando 'ffmpeg -i' (sem ffprobe).
        Parse da linha: 'Duration: HH:MM:SS.mm'
        """
        if not path.exists():
            return 0.0
        try:
            result = subprocess.run(
                [FFMPEG, "-i", str(path)],
                capture_output=True, text=True, timeout=15,
                encoding="utf-8", errors="replace",
            )
            # ffmpeg escreve info no stderr mesmo em caso de 'erro' (sem output)
            for line in result.stderr.splitlines():
                if "Duration:" in line:
                    dur_str = line.strip().split("Duration:")[1].split(",")[0].strip()
                    h, m, s = dur_str.split(":")
                    return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception as e:
            print(f"    AVISO: nao foi possivel medir duracao: {e}")
        return 5.0  # fallback: 5 segundos

    # ----------------------------------------------------------
    # UTILITARIOS
    # ----------------------------------------------------------

    @classmethod
    def listar_vozes(cls):
        """Mostra vozes disponiveis."""
        print("\n  VOZES TTS DISPONIVEIS (pt-BR):")
        print("  " + "-" * 40)
        for key, voice_id in VOZES.items():
            print(f"  {key:12s} -> {voice_id}")


# -----------------------------------------------------------
# FUNCOES AUXILIARES
# -----------------------------------------------------------

def _safe_name(titulo: str) -> str:
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in titulo)[:40]


def _calc_rate(fala: dict) -> str:
    """
    Converte velocidade sugerida (ex: '190wpm acelerado') em rate do edge-tts.
    edge-tts rate: '+20%' = 20% mais rapido | '-10%' = 10% mais lento.
    Base natural: ~150wpm.
    """
    if not isinstance(fala, dict):
        return "+0%"
    entonacao = fala.get("entonacao", {})
    if not isinstance(entonacao, dict):
        return "+0%"

    velocidade = str(entonacao.get("velocidade", "")).lower()

    if any(x in velocidade for x in ["190", "185"]):
        return "+20%"
    if any(x in velocidade for x in ["180", "175"]):
        return "+12%"
    if "170" in velocidade:
        return "+5%"
    if any(x in velocidade for x in ["160", "155"]):
        return "-5%"
    if any(x in velocidade for x in ["pausad", "lento", "calmo"]):
        return "-10%"
    return "+0%"
