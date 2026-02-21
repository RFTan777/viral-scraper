"""
=============================================================
MODULO 4: ANALISADOR DE VIDEO
=============================================================
Analisa cortes, ritmo de edicao, e extrai frames-chave.
Usa FFmpeg + FFprobe para analise tecnica.
Fallback para ffmpeg quando ffprobe nao esta disponivel.
"""

import json
import shutil
import subprocess
import re
from pathlib import Path
from config import VIDEO_ANALYSIS, FRAMES_DIR, DATA_DIR, FFMPEG_DIR


class VideoAnalyzer:
    """Analise tecnica de video: cortes, ritmo, frames."""

    def __init__(self):
        self.ffmpeg = str(FFMPEG_DIR / "ffmpeg.exe")
        self.ffprobe = self._find_ffprobe()

    def _find_ffprobe(self) -> str | None:
        """Tenta localizar ffprobe: projeto -> PATH -> None (fallback para ffmpeg)."""
        # 1. Tentar no diretorio do projeto
        project_ffprobe = FFMPEG_DIR / "ffprobe.exe"
        if project_ffprobe.exists():
            return str(project_ffprobe)

        # 2. Tentar no PATH do sistema
        ffprobe_in_path = shutil.which("ffprobe")
        if ffprobe_in_path:
            return ffprobe_in_path

        # 3. Nao encontrado — usar fallback via ffmpeg
        print("  [VideoAnalyzer] ffprobe nao encontrado, usando fallback via ffmpeg")
        return None

    def analyze_all(self, videos: list[dict]) -> list[dict]:
        """
        Analisa todos os videos da lista.

        Args:
            videos: Lista de dicts (precisa ter 'local_video_path')

        Returns:
            Lista atualizada com dados de analise visual
        """
        print("\n" + "=" * 60)
        print("ANALISANDO VIDEOS")
        print("=" * 60)

        for i, video in enumerate(videos, 1):
            video_path = video.get("local_video_path")
            if not video_path or not Path(video_path).exists():
                print(f"  [{i}] Aviso: Video nao encontrado para {video['id']}")
                video["video_analysis"] = None
                continue

            print(f"  [{i}/{len(videos)}] Analisando: {video['platform']}_{video['id']}...")

            try:
                analysis = self._analyze_video(video_path, video["id"])
                video["video_analysis"] = analysis
                print(f"    OK: {analysis['total_cuts']} cortes detectados")
                print(f"    Ritmo: {analysis['cuts_per_minute']:.1f} cortes/min")
                print(f"    {len(analysis['extracted_frames'])} frames extraidos")
            except Exception as e:
                print(f"    ERRO: {e}")
                video["video_analysis"] = None

        analyzed = sum(1 for v in videos if v.get("video_analysis"))
        print(f"\n  {analyzed}/{len(videos)} videos analisados")
        return videos

    def _analyze_video(self, video_path: str, video_id: str) -> dict:
        """
        Analise completa de um video individual.

        Returns:
            Dict com todos os dados de analise visual
        """
        video_path = Path(video_path)

        # 1. Metadados tecnicos via FFprobe ou fallback
        if self.ffprobe:
            metadata = self._get_metadata(video_path)
        else:
            metadata = self._get_metadata_ffmpeg(video_path)

        # 2. Detectar cortes/cenas
        cuts = self._detect_cuts(video_path)

        # 3. Calcular metricas de edicao
        duration = metadata.get("duration", 0)
        total_cuts = len(cuts)
        cuts_per_minute = (total_cuts / duration * 60) if duration > 0 else 0

        # Duracao media entre cortes
        if len(cuts) > 1:
            intervals = [cuts[i+1] - cuts[i] for i in range(len(cuts)-1)]
            avg_segment = sum(intervals) / len(intervals)
        else:
            avg_segment = duration

        # 4. Extrair frames-chave
        frames = self._extract_key_frames(video_path, video_id, duration, cuts)

        # 5. Classificar ritmo de edicao
        editing_pace = self._classify_pace(cuts_per_minute)

        return {
            "duration_seconds": round(duration, 2),
            "resolution": f"{metadata.get('width', '?')}x{metadata.get('height', '?')}",
            "fps": metadata.get("fps", 0),
            "has_audio": metadata.get("has_audio", False),
            "total_cuts": total_cuts,
            "cuts_per_minute": round(cuts_per_minute, 1),
            "avg_segment_duration": round(avg_segment, 2),
            "cut_timestamps": [round(c, 2) for c in cuts],
            "editing_pace": editing_pace,
            "extracted_frames": frames,
            "hook_frame": frames[0] if frames else None,
        }

    def _get_metadata(self, video_path: Path) -> dict:
        """Extrai metadados tecnicos via FFprobe."""
        try:
            cmd = [
                self.ffprobe,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout)

            video_stream = None
            has_audio = False

            for stream in data.get("streams", []):
                if stream["codec_type"] == "video" and not video_stream:
                    video_stream = stream
                if stream["codec_type"] == "audio":
                    has_audio = True

            if not video_stream:
                return {"duration": 0}

            # Parse FPS
            fps_str = video_stream.get("r_frame_rate", "30/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = round(int(num) / int(den), 2)
            else:
                fps = float(fps_str)

            return {
                "duration": float(data.get("format", {}).get("duration", 0)),
                "width": int(video_stream.get("width", 0)),
                "height": int(video_stream.get("height", 0)),
                "fps": fps,
                "has_audio": has_audio,
                "codec": video_stream.get("codec_name", ""),
            }
        except Exception as e:
            print(f"    Aviso FFprobe: {e}, tentando fallback via ffmpeg...")
            return self._get_metadata_ffmpeg(video_path)

    def _get_metadata_ffmpeg(self, video_path: Path) -> dict:
        """Fallback: extrai metadados via stderr do ffmpeg."""
        try:
            cmd = [
                self.ffmpeg,
                "-i", str(video_path),
                "-f", "null",
                "-"
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            stderr = result.stderr

            metadata = {"duration": 0, "width": 0, "height": 0, "fps": 0, "has_audio": False}

            # Extrair duracao: "Duration: 00:01:30.50"
            dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", stderr)
            if dur_match:
                h, m, s, cs = dur_match.groups()
                metadata["duration"] = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100

            # Extrair resolucao e fps: "Stream #0:0: Video: h264 ... 1080x1920 ... 30 fps"
            video_match = re.search(
                r"Stream\s+#\d+:\d+.*Video:.*?(\d{2,5})x(\d{2,5}).*?(\d+(?:\.\d+)?)\s*(?:fps|tbr)",
                stderr
            )
            if video_match:
                metadata["width"] = int(video_match.group(1))
                metadata["height"] = int(video_match.group(2))
                metadata["fps"] = float(video_match.group(3))

            # Detectar audio
            if re.search(r"Stream\s+#\d+:\d+.*Audio:", stderr):
                metadata["has_audio"] = True

            return metadata
        except Exception as e:
            print(f"    Aviso ffmpeg metadata fallback: {e}")
            return {"duration": 0}

    def _detect_cuts(self, video_path: Path) -> list[float]:
        """
        Detecta cortes/transicoes no video usando FFmpeg scene filter.

        Returns:
            Lista de timestamps (em segundos) onde ocorrem cortes
        """
        try:
            threshold = VIDEO_ANALYSIS["scene_threshold"] / 100.0

            cmd = [
                self.ffmpeg,
                "-i", str(video_path),
                "-vf", f"select='gt(scene,{threshold})',showinfo",
                "-vsync", "vfr",
                "-f", "null",
                "-loglevel", "info",
                "-"
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )

            # Parse timestamps dos cortes do stderr
            cuts = []
            for line in result.stderr.split("\n"):
                if "pts_time:" in line:
                    match = re.search(r"pts_time:(\d+\.?\d*)", line)
                    if match:
                        timestamp = float(match.group(1))
                        cuts.append(timestamp)

            return sorted(set(cuts))

        except Exception as e:
            print(f"    Aviso: Deteccao de cortes falhou: {e}")
            return []

    def _extract_key_frames(
        self, video_path: Path, video_id: str, duration: float, cuts: list[float]
    ) -> list[str]:
        """
        Extrai frames-chave do video:
        - Frame 0 (thumbnail/hook visual)
        - Frames nos momentos de corte
        - Frames distribuidos uniformemente
        """
        frames_dir = FRAMES_DIR / video_id
        frames_dir.mkdir(parents=True, exist_ok=True)

        extracted = []
        n_frames = VIDEO_ANALYSIS["frames_to_extract"]

        # Timestamps para extrair
        timestamps = [0.0]  # Sempre pegar o primeiro frame (hook)

        # Adicionar pontos de corte (maximo metade dos frames)
        if cuts:
            max_cut_frames = n_frames // 2
            step = max(1, len(cuts) // max_cut_frames)
            timestamps.extend(cuts[::step][:max_cut_frames])

        # Preencher com frames distribuidos uniformemente
        remaining = n_frames - len(timestamps)
        if remaining > 0 and duration > 0:
            interval = duration / (remaining + 1)
            for j in range(1, remaining + 1):
                timestamps.append(interval * j)

        # Remover duplicatas e ordenar
        timestamps = sorted(set(timestamps))[:n_frames]

        # Extrair cada frame
        for idx, ts in enumerate(timestamps):
            frame_path = frames_dir / f"frame_{idx:02d}_{ts:.1f}s.jpg"

            if frame_path.exists():
                extracted.append(str(frame_path))
                continue

            try:
                cmd = [
                    self.ffmpeg,
                    "-ss", str(ts),
                    "-i", str(video_path),
                    "-vframes", "1",
                    "-q:v", "2",
                    "-y",
                    "-loglevel", "error",
                    str(frame_path)
                ]
                subprocess.run(cmd, check=True, timeout=15)
                extracted.append(str(frame_path))
            except Exception:
                pass

        return extracted

    def _classify_pace(self, cuts_per_minute: float) -> str:
        """Classifica o ritmo de edicao."""
        if cuts_per_minute == 0:
            return "sem_cortes"
        elif cuts_per_minute < 5:
            return "lento"
        elif cuts_per_minute < 15:
            return "moderado"
        elif cuts_per_minute < 30:
            return "rapido"
        else:
            return "muito_rapido"

    def save_analysis(self, videos: list[dict], filename: str = "video_analysis.json"):
        """Salva analises em arquivo."""
        analyses = {}
        for v in videos:
            if v.get("video_analysis"):
                analyses[v["id"]] = {
                    "platform": v["platform"],
                    "author": v["author"],
                    "video_analysis": v["video_analysis"],
                }

        filepath = DATA_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(analyses, f, ensure_ascii=False, indent=2)
        print(f"  Analises salvas em: {filepath}")
        return filepath
