"""
=============================================================
MODULO: PIPELINE DE VIDEO — Orquestrador completo
=============================================================
Transforma roteiros JSON em videos MP4 prontos para postar.

Modos:
  "sem_ia"   — TTS + fundo colorido (gratis, rapido, sem API)
  "com_ia"   — TTS + clips gerados por fal.ai (requer FAL_AI_KEY)
  "clips_ok" — TTS + clips ja baixados pelo Kling/fal.ai

Uso:
    pipeline = PipelineVideo()
    pipeline.executar(scripts, modo="sem_ia")

    # Com musica de fundo:
    pipeline = PipelineVideo(music_path="musica.mp3", voice="masculino")
    pipeline.executar(scripts, modo="com_ia")
=============================================================
"""

import json
import re
from pathlib import Path
from typing import Optional

from config import OUTPUT_DIR, FAL_AI_KEY, VIDEO_AI
from modules.tts_generator import TTSGenerator
from modules.video_editor import VideoEditor


class PipelineVideo:
    """Orquestra TTS + clips de IA + edicao em um video final."""

    def __init__(
        self,
        voice: str = "feminino",
        music_path: str = None,
        output_dir: Path = None,
    ):
        self.voice = voice
        self.music_path = music_path
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR / "videos_finais"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------
    # ENTRY POINT
    # ----------------------------------------------------------

    def executar(
        self,
        scripts: list[dict],
        modo: str = "sem_ia",
        clips_dir: str = None,
        modelo_ia: str = None,
        max_cenas_ia: int = None,
    ) -> list[dict]:
        """
        Processa lista de roteiros e gera um video por roteiro.

        Args:
            scripts:     lista de roteiros (de roteiros.json)
            modo:        "sem_ia" | "com_ia" | "clips_ok"
            clips_dir:   path dos clips ja baixados (modo clips_ok)
            modelo_ia:   modelo fal.ai: "kling"|"wan"|"cogvideo" (modo com_ia)
            max_cenas_ia: limita cenas enviadas para IA (economiza creditos)

        Returns:
            Lista de resultados: [{ titulo, video_path, status, ... }]
        """
        resultados = []

        for i, script in enumerate(scripts, 1):
            titulo = script.get("titulo", f"Roteiro {i}")
            print(f"\n{'#' * 60}")
            print(f"  PIPELINE VIDEO [{i}/{len(scripts)}]")
            print(f"  {titulo}")
            print(f"  Modo: {modo}")
            print(f"{'#' * 60}")

            resultado = self._processar(
                script=script,
                modo=modo,
                clips_dir=clips_dir,
                modelo_ia=modelo_ia,
                max_cenas_ia=max_cenas_ia,
            )
            resultados.append(resultado)

            if resultado["status"] == "ok":
                print(f"\n  PRONTO: {resultado['video_path']}")
            else:
                print(f"\n  FALHA: {resultado.get('erros', [])}")

        self._salvar_relatorio(resultados)
        self._imprimir_resumo(resultados)
        return resultados

    # ----------------------------------------------------------
    # PROCESSAR UM ROTEIRO
    # ----------------------------------------------------------

    def _processar(self, script, modo, clips_dir, modelo_ia, max_cenas_ia) -> dict:
        titulo = script.get("titulo", "video")
        safe = _safe_name(titulo)
        tts_dir = self.output_dir / safe / "audio_tts"
        tts_dir.mkdir(parents=True, exist_ok=True)

        # Etapa 1: TTS
        print(f"\n  [1/3] Gerando voiceover TTS...")
        tts_gen = TTSGenerator(voice=self.voice, output_dir=tts_dir)
        tts_results = tts_gen.generate_for_script(script)
        dur_total = sum(r.get("duration_sec", 0) for r in tts_results)
        cenas_ok = sum(1 for r in tts_results if r.get("audio_path"))
        print(f"\n       {cenas_ok}/{len(tts_results)} cenas com audio | Total: {dur_total:.1f}s")

        # Etapa 2: Clips de IA (opcional)
        clips_ia = None
        if modo == "com_ia":
            print(f"\n  [2/3] Gerando clips de IA (fal.ai)...")
            clips_ia = self._gerar_clips_ia(script, modelo_ia, max_cenas_ia)
        elif modo == "clips_ok":
            print(f"\n  [2/3] Carregando clips existentes...")
            clips_ia = self._carregar_clips(script, clips_dir)
        else:
            print(f"\n  [2/3] Modo sem IA — fundos coloridos por bloco")

        # Etapa 3: Editar
        print(f"\n  [3/3] Montando video com ffmpeg...")
        editor = VideoEditor(output_dir=self.output_dir)
        video_path = editor.montar_video(
            script=script,
            tts_results=tts_results,
            clips_ia=clips_ia,
            music_path=self.music_path,
        )

        if video_path:
            return {
                "titulo": titulo,
                "video_path": str(video_path),
                "status": "ok",
                "modo": modo,
                "duracao_tts": dur_total,
                "cenas_processadas": cenas_ok,
            }
        return {
            "titulo": titulo,
            "video_path": None,
            "status": "falha",
            "erros": ["editor nao gerou video"],
        }

    # ----------------------------------------------------------
    # CLIPS DE IA
    # ----------------------------------------------------------

    def _gerar_clips_ia(self, script, modelo, max_cenas) -> list[dict]:
        """Envia roteiro para fal.ai e retorna clips baixados."""
        if not FAL_AI_KEY:
            print("    AVISO: FAL_AI_KEY nao configurada. Usando modo sem IA.")
            return []

        from modules.video_ai_sender import VideoAISender
        modelo = modelo or VIDEO_AI.get("modelo_padrao", "kling")
        max_c = max_cenas or VIDEO_AI.get("max_cenas_por_roteiro", 9)

        script_lim = dict(script)
        cenas = script.get("cenas", [])
        if len(cenas) > max_c:
            print(f"    Limitando: {max_c}/{len(cenas)} cenas")
            script_lim["cenas"] = cenas[:max_c]

        try:
            sender = VideoAISender(fal_api_key=FAL_AI_KEY, model=modelo)
            resultado = sender.send_script(script_lim)
            clips = resultado.get("clips", [])
            ok = sum(1 for c in clips if c.get("status") == "ok")
            print(f"    {ok}/{len(clips)} clips gerados pela IA")
            return clips
        except Exception as e:
            print(f"    ERRO ao gerar clips IA: {e}")
            return []

    def _carregar_clips(self, script, clips_dir) -> list[dict]:
        """Carrega clips ja baixados de um diretorio."""
        if not clips_dir:
            clips_dir = str(OUTPUT_DIR / "video_gerado")

        clips_path = Path(clips_dir)
        if not clips_path.exists():
            print(f"    AVISO: diretorio nao encontrado: {clips_dir}")
            return []

        # Tenta carregar JSON de resultado do VideoAISender
        for json_file in sorted(clips_path.glob("resultado_*.json")):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                clips = data.get("clips", [])
                ok = sum(1 for c in clips if c.get("status") == "ok")
                print(f"    {ok} clips carregados de {json_file.name}")
                return clips
            except Exception:
                continue

        # Fallback: listar MP4 no diretorio
        clips = []
        for mp4 in sorted(clips_path.glob("clip_*.mp4")):
            m = re.search(r"cena(\d+)", mp4.name)
            if m:
                clips.append({
                    "status": "ok",
                    "local_path": str(mp4),
                    "cena_numero": int(m.group(1)),
                    "label": f"Cena {m.group(1)}",
                    "bloco": "",
                })
        print(f"    {len(clips)} clips encontrados em {clips_path.name}/")
        return clips

    # ----------------------------------------------------------
    # RELATORIO
    # ----------------------------------------------------------

    def _salvar_relatorio(self, resultados: list[dict]):
        path = self.output_dir / "relatorio_videos.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)
        print(f"\n  Relatorio: {path}")

    def _imprimir_resumo(self, resultados: list[dict]):
        ok = [r for r in resultados if r["status"] == "ok"]
        print(f"\n{'=' * 60}")
        print(f"  PIPELINE CONCLUIDO: {len(ok)}/{len(resultados)} videos gerados")
        for r in ok:
            p = Path(r["video_path"])
            mb = p.stat().st_size / 1024 / 1024 if p.exists() else 0
            print(f"    {p.name} ({mb:.1f} MB)")
        print(f"{'=' * 60}")


# -----------------------------------------------------------
# UTIL
# -----------------------------------------------------------

def _safe_name(titulo: str) -> str:
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in titulo)[:40]
