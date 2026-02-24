"""
=============================================================
MODULO: VIDEO EDITOR — Edicao completa com FFmpeg
=============================================================
Monta video final TikTok/Reels 1080x1920 9:16 H.264 MP4.

Fluxo por cena:
  1. Fundo: clip de IA (loop) OU cor solida por bloco
  2. Redimensiona/cropa para 1080x1920
  3. Adiciona audio TTS sincronizado
  4. Adiciona legenda/caption com drawtext

Montagem final:
  5. Concatena todas as cenas (concat demuxer)
  6. Mistura musica de fundo (amix) com fade out
  7. Output: MP4 H.264 AAC 1080x1920

Sem moviepy. Apenas subprocess + ffmpeg.exe.
=============================================================
"""

import re
import subprocess
from pathlib import Path
from typing import Optional

from config import BASE_DIR, OUTPUT_DIR

# -----------------------------------------------------------
# CONFIGURACOES VISUAIS
# -----------------------------------------------------------

FFMPEG = str(BASE_DIR / "ffmpeg.exe") if (BASE_DIR / "ffmpeg.exe").exists() else "ffmpeg"
W, H, FPS = 1080, 1920, 30
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
CRF = 23
PRESET = "medium"
AUDIO_BITRATE = "192k"
FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"   # Arial Bold
FONT_SIZE = 56
MUSIC_VOLUME = 0.12

BG_COLORS = {
    "GANCHO":        "0x1a1a2e",
    "CREDIBILIDADE": "0x0f3460",
    "CONTEUDO":      "0x16213e",
    "CTA":           "0xe94560",
    "GLOBAL":        "0x1a1a2e",
    "DEFAULT":       "0x1a1a2e",
}


class VideoEditor:
    """Edita videos completos a partir de cenas TTS + clips de IA."""

    def __init__(self, output_dir: Path = None):
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR / "videos_finais"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------
    # ENTRY POINT
    # ----------------------------------------------------------

    def montar_video(
        self,
        script: dict,
        tts_results: list[dict],
        clips_ia: list[dict] = None,
        music_path: str = None,
    ) -> Optional[Path]:
        """
        Monta o video completo para um roteiro.

        Args:
            script: roteiro dict (roteiros.json)
            tts_results: resultado de TTSGenerator.generate_for_script()
            clips_ia: [{cena_numero, local_path, status}] do VideoAISender
            music_path: path MP3 para musica de fundo (opcional)

        Returns:
            Path do MP4 final ou None em caso de falha total
        """
        titulo = script.get("titulo", "video")
        safe = _safe_name(titulo)
        work_dir = self.output_dir / safe
        work_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'=' * 60}")
        print(f"  VIDEO EDITOR: {titulo}")
        print(f"{'=' * 60}")

        # Indexar TTS e clips por numero da cena
        tts_map = {r["cena_numero"]: r for r in tts_results}
        clips_map = _index_clips(clips_ia or [])

        # Montar cada cena
        cena_paths = []
        for cena in script.get("cenas", []):
            numero = cena.get("numero", 0)
            tts = tts_map.get(numero, {})
            clip_ia = clips_map.get(numero)

            print(f"\n  Cena {numero} [{cena.get('momento','')}] {cena.get('bloco','')}")

            cena_path = self._montar_cena(
                cena=cena,
                audio_path=tts.get("audio_path"),
                duration=tts.get("duration_sec", 5.0),
                clip_ia_path=clip_ia,
                work_dir=work_dir,
            )

            if cena_path:
                cena_paths.append(cena_path)
                print(f"    OK: {cena_path.name} ({cena_path.stat().st_size/1024:.0f} KB)")
            else:
                print(f"    FALHA: cena {numero} nao montada")

        if not cena_paths:
            print("\n  ERRO: Nenhuma cena montada.")
            return None

        # Concatenar
        print(f"\n  Concatenando {len(cena_paths)} cenas...")
        concat_path = work_dir / f"{safe}_concat.mp4"
        if not self._concatenar(cena_paths, concat_path):
            return None

        # Adicionar musica (opcional)
        final_path = self.output_dir / f"{safe}_FINAL.mp4"
        if music_path and Path(music_path).exists():
            print(f"  Adicionando musica: {Path(music_path).name}")
            ok = self._add_music(concat_path, music_path, final_path)
            if not ok:
                concat_path.rename(final_path)
        else:
            concat_path.rename(final_path)

        size_mb = final_path.stat().st_size / 1024 / 1024
        dur = self._get_duration(final_path)
        print(f"\n  VIDEO FINAL: {final_path.name}")
        print(f"  Duracao: {dur:.1f}s | Tamanho: {size_mb:.1f} MB")
        return final_path

    # ----------------------------------------------------------
    # MONTAGEM DE CENA
    # ----------------------------------------------------------

    def _montar_cena(
        self,
        cena: dict,
        audio_path: Optional[str],
        duration: float,
        clip_ia_path: Optional[str],
        work_dir: Path,
    ) -> Optional[Path]:
        """Gera MP4 de uma cena: fundo + audio + legenda."""
        numero = cena.get("numero", 0)
        output = work_dir / f"cena_{numero:02d}.mp4"
        if output.exists():
            output.unlink()

        duration = max(duration, 1.5)

        # Texto da legenda (texto_tela.texto do roteiro)
        texto_tela = cena.get("texto_tela", {})
        legenda = ""
        posicao = "inferior"
        if isinstance(texto_tela, dict):
            legenda = texto_tela.get("texto", "")
            posicao = texto_tela.get("posicao", "inferior")
        elif isinstance(texto_tela, str):
            legenda = texto_tela

        drawtext = _build_drawtext(legenda, posicao) if legenda else ""

        if clip_ia_path and Path(clip_ia_path).exists():
            return self._cena_com_clip(clip_ia_path, audio_path, duration, drawtext, output)
        else:
            bloco = cena.get("bloco", "DEFAULT")
            fala = cena.get("fala", {})
            texto_fala = fala.get("texto", "") if isinstance(fala, dict) else ""
            return self._cena_sem_ia(bloco, audio_path, duration, drawtext, texto_fala, output)

    def _cena_com_clip(
        self, clip_path, audio_path, duration, drawtext, output
    ) -> Optional[Path]:
        """Usa clip de IA com loop para durar o mesmo que o TTS."""
        scale_crop = (
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},setsar=1"
        )
        vf = f"{scale_crop},{drawtext}" if drawtext else scale_crop

        if audio_path and Path(audio_path).exists():
            cmd = [
                FFMPEG, "-y", "-loglevel", "error",
                "-stream_loop", "-1", "-i", str(clip_path),
                "-i", str(audio_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-t", f"{duration:.3f}",
                "-vf", vf,
                "-r", str(FPS),
                "-c:v", VIDEO_CODEC, "-crf", str(CRF), "-preset", PRESET,
                "-c:a", AUDIO_CODEC, "-b:a", AUDIO_BITRATE,
                "-shortest", "-movflags", "+faststart",
                str(output),
            ]
        else:
            cmd = [
                FFMPEG, "-y", "-loglevel", "error",
                "-stream_loop", "-1", "-i", str(clip_path),
                "-t", f"{duration:.3f}",
                "-vf", vf,
                "-r", str(FPS),
                "-c:v", VIDEO_CODEC, "-crf", str(CRF), "-preset", PRESET,
                "-an", "-movflags", "+faststart",
                str(output),
            ]
        return _run(cmd, output)

    def _cena_sem_ia(
        self, bloco, audio_path, duration, drawtext, texto_fala, output
    ) -> Optional[Path]:
        """Gera cena com fundo colorido por bloco (sem clip de IA)."""
        cor = BG_COLORS.get(bloco, BG_COLORS["DEFAULT"])
        video_src = f"color=c={cor}:size={W}x{H}:rate={FPS}"

        # Filtros: legenda principal (texto_tela) + texto da fala menor
        filters = []
        if drawtext:
            filters.append(drawtext)

        # Texto da fala no centro inferior (preview sem IA)
        if texto_fala:
            linhas = _wrap_text(texto_fala, max_chars=28)[:4]
            texto_display = "\n".join(linhas)
            fe = _escape(texto_display)
            font_esc = FONT_PATH.replace(":", "\\:")
            filters.append(
                f"drawtext=fontfile='{font_esc}'"
                f":text='{fe}'"
                f":fontsize=34"
                f":fontcolor=white@0.75"
                f":x=(w-text_w)/2"
                f":y=h*0.75-text_h/2"
                f":line_spacing=10"
                f":borderw=2:bordercolor=black@0.8"
                f":fix_bounds=true"
            )

        vf = ",".join(filters) if filters else "null"

        if audio_path and Path(audio_path).exists():
            cmd = [
                FFMPEG, "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", video_src,
                "-i", str(audio_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-t", f"{duration:.3f}",
                "-vf", vf,
                "-r", str(FPS),
                "-c:v", VIDEO_CODEC, "-crf", str(CRF), "-preset", PRESET,
                "-c:a", AUDIO_CODEC, "-b:a", AUDIO_BITRATE,
                "-shortest", "-movflags", "+faststart",
                str(output),
            ]
        else:
            cmd = [
                FFMPEG, "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", video_src,
                "-t", f"{duration:.3f}",
                "-vf", vf,
                "-r", str(FPS),
                "-c:v", VIDEO_CODEC, "-crf", str(CRF), "-preset", PRESET,
                "-an", "-movflags", "+faststart",
                str(output),
            ]
        return _run(cmd, output)

    # ----------------------------------------------------------
    # CONCATENACAO
    # ----------------------------------------------------------

    def _concatenar(self, paths: list[Path], output: Path) -> bool:
        """Concatena clips via concat demuxer (arquivo de lista)."""
        list_file = output.parent / "_concat_list.txt"
        lines = [f"file '{str(p).replace(chr(92), '/')}'\n" for p in paths]
        list_file.write_text("".join(lines), encoding="utf-8")

        cmd = [
            FFMPEG, "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c:v", VIDEO_CODEC, "-crf", str(CRF), "-preset", PRESET,
            "-c:a", AUDIO_CODEC, "-b:a", AUDIO_BITRATE,
            "-movflags", "+faststart",
            str(output),
        ]
        result = _run(cmd, output)
        list_file.unlink(missing_ok=True)
        return result is not None

    # ----------------------------------------------------------
    # MUSICA DE FUNDO
    # ----------------------------------------------------------

    def _add_music(self, video: Path, music: str, output: Path) -> bool:
        """Mistura musica de fundo com volume baixo e fade out."""
        dur = self._get_duration(video)
        if dur <= 0:
            return False

        fade_start = max(0, dur - 3.0)
        af = (
            f"[1:a]aloop=-1:size=2000000000,"
            f"volume={MUSIC_VOLUME},"
            f"afade=t=out:st={fade_start:.3f}:d=3.0[music];"
            f"[0:a][music]amix=inputs=2:normalize=0[aout]"
        )

        cmd = [
            FFMPEG, "-y", "-loglevel", "error",
            "-i", str(video),
            "-i", str(music),
            "-filter_complex", af,
            "-map", "0:v:0", "-map", "[aout]",
            "-t", f"{dur:.3f}",
            "-c:v", "copy",
            "-c:a", AUDIO_CODEC, "-b:a", AUDIO_BITRATE,
            "-movflags", "+faststart",
            str(output),
        ]
        return _run(cmd, output) is not None

    # ----------------------------------------------------------
    # DURACAO
    # ----------------------------------------------------------

    def _get_duration(self, path: Path) -> float:
        """Mede duracao via 'ffmpeg -i' (sem ffprobe)."""
        try:
            r = subprocess.run(
                [FFMPEG, "-i", str(path)],
                capture_output=True, text=True, timeout=15,
                encoding="utf-8", errors="replace",
            )
            for line in r.stderr.splitlines():
                if "Duration:" in line:
                    d = line.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = d.split(":")
                    return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception:
            pass
        return 0.0


# -----------------------------------------------------------
# FUNCOES AUXILIARES
# -----------------------------------------------------------

def _build_drawtext(texto: str, posicao: str) -> str:
    """Monta filtro drawtext para legenda/caption."""
    if not texto:
        return ""

    # Escape para ffmpeg drawtext
    fe = _escape(texto[:60])  # limita tamanho da legenda
    font_esc = FONT_PATH.replace(":", "\\:")

    # Posicao Y
    if "superior" in posicao:
        x, y = "(w-text_w)/2", "80"
    elif "esquerdo" in posicao:
        x, y = "60", "h-text_h-80"
    elif "centro" in posicao:
        x, y = "(w-text_w)/2", "(h-text_h)/2"
    else:  # inferior (padrao)
        x, y = "(w-text_w)/2", "h-text_h-100"

    return (
        f"drawtext=fontfile='{font_esc}'"
        f":text='{fe}'"
        f":fontsize={FONT_SIZE}"
        f":fontcolor=white"
        f":x={x}:y={y}"
        f":borderw=3:bordercolor=black"
        f":box=1:boxcolor=black@0.5:boxborderw=6"
        f":fix_bounds=true"
    )


def _escape(texto: str) -> str:
    """Escapa caracteres especiais para o filtro drawtext."""
    texto = texto.replace("\\", "\\\\")
    texto = texto.replace("'", "\u2019")   # substitui aspas simples por Unicode
    texto = texto.replace(":", "\\:")
    texto = texto.replace(";", "\\;")
    texto = texto.replace("%", "\\%")
    texto = texto.replace("[", "\\[")
    texto = texto.replace("]", "\\]")
    return texto


def _wrap_text(texto: str, max_chars: int = 28) -> list[str]:
    """Quebra texto em linhas de no maximo max_chars caracteres."""
    words = texto.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > max_chars:
            if current:
                lines.append(current.strip())
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        lines.append(current)
    return lines


def _index_clips(clips_ia: list) -> dict:
    """Indexa clips de IA por numero de cena."""
    index = {}
    for c in clips_ia:
        if c.get("status") != "ok" or not c.get("local_path"):
            continue
        # Tenta campo direto
        num = c.get("cena_numero")
        if not num:
            # Tenta extrair do label: "Cena 3 [00:08]"
            label = c.get("label", "")
            m = re.search(r"cena\s*(\d+)", label, re.IGNORECASE)
            if m:
                num = int(m.group(1))
        if num:
            index[num] = c["local_path"]
    return index


def _safe_name(titulo: str) -> str:
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in titulo)[:40]


def _run(cmd: list, expected: Path, timeout: int = 300) -> Optional[Path]:
    """Executa ffmpeg e verifica se o output foi criado."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            print(f"    ERRO ffmpeg (rc={result.returncode}): {result.stderr[-400:]}")
            return None
        if not expected.exists() or expected.stat().st_size < 100:
            print(f"    ERRO: arquivo nao gerado ou vazio: {expected.name}")
            return None
        return expected
    except subprocess.TimeoutExpired:
        print(f"    ERRO: timeout ({timeout}s) para {expected.name}")
        return None
    except Exception as e:
        print(f"    ERRO ffmpeg: {e}")
        return None
