"""
=============================================================
MODULO 2: DOWNLOADER
=============================================================
Baixa os videos coletados para analise local.
Usa yt_dlp (biblioteca Python) + FFmpeg para extracao de audio.
Downloads em paralelo com ThreadPoolExecutor (5 workers).
"""

import subprocess
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import yt_dlp
from config import VIDEOS_DIR, AUDIO_DIR, FFMPEG_DIR


class VideoDownloader:
    """Baixa videos do TikTok e Instagram para analise."""

    def __init__(self):
        self.ffmpeg_path = str(FFMPEG_DIR / "ffmpeg.exe")

    def download_all(self, videos: list[dict], max_workers: int = 5) -> list[dict]:
        """
        Baixa todos os videos da lista em paralelo.

        Args:
            videos: Lista de dicts com dados dos videos
            max_workers: Numero maximo de downloads simultaneos

        Returns:
            Lista atualizada com caminhos locais dos arquivos
        """
        print("\n" + "=" * 60)
        print("BAIXANDO VIDEOS")
        print("=" * 60)
        print(f"  {len(videos)} videos para baixar com {max_workers} workers...")

        def _process_download(video):
            video_path = self._download_video(video)
            if video_path:
                audio_path = self._extract_audio(video_path, video["id"])
                return video, str(video_path), str(audio_path) if audio_path else None
            return video, None, None

        downloaded = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_process_download, v): v for v in videos}

            completed = 0
            for future in as_completed(futures):
                video, video_path, audio_path = future.result()
                completed += 1

                if video_path:
                    video["local_video_path"] = video_path
                    video["local_audio_path"] = audio_path
                    downloaded.append(video)
                    print(f"  [{completed}/{len(videos)}] OK: {video['platform']}_{video['id']}")
                else:
                    print(f"  [{completed}/{len(videos)}] FALHA: {video['platform']}_{video['id']}")

        print(f"\n  {len(downloaded)}/{len(videos)} videos baixados com sucesso")
        return downloaded

    def _download_video(self, video: dict) -> Path | None:
        """Baixa um video individual. Tenta URL direta primeiro, fallback via yt-dlp."""
        video_url = video.get("video_url", "")
        if not video_url:
            return self._download_via_ytdlp(video)

        try:
            filename = f"{video['platform']}_{video['id']}.mp4"
            filepath = VIDEOS_DIR / filename

            if filepath.exists():
                return filepath

            response = requests.get(video_url, stream=True, timeout=60, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            response.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return filepath

        except Exception as e:
            print(f"    Aviso: Download direto falhou: {e}")
            return self._download_via_ytdlp(video)

    def _download_via_ytdlp(self, video: dict) -> Path | None:
        """Fallback: baixa via yt_dlp (biblioteca Python nativa)."""
        url = video.get("url", "")
        if not url:
            return None

        filename = f"{video['platform']}_{video['id']}"
        filepath = VIDEOS_DIR / f"{filename}.mp4"

        if filepath.exists():
            return filepath

        try:
            ydl_opts = {
                "outtmpl": str(VIDEOS_DIR / f"{filename}.%(ext)s"),
                "format": "mp4/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "merge_output_format": "mp4",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "ffmpeg_location": str(FFMPEG_DIR),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            for ext in [".mp4", ".webm", ".mkv"]:
                candidate = VIDEOS_DIR / f"{filename}{ext}"
                if candidate.exists():
                    return candidate

            return None

        except Exception as e:
            print(f"    Aviso: yt-dlp falhou: {e}")
            return None

    def _extract_audio(self, video_path: Path, video_id: str) -> Path | None:
        """Extrai audio do video usando FFmpeg (path explicito da raiz do projeto)."""
        try:
            audio_path = AUDIO_DIR / f"{video_id}.mp3"

            if audio_path.exists():
                return audio_path

            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-vn",
                "-acodec", "libmp3lame",
                "-ab", "128k",
                "-ar", "16000",
                "-y",
                "-loglevel", "error",
                str(audio_path)
            ]

            subprocess.run(cmd, check=True, timeout=60)
            return audio_path

        except Exception as e:
            print(f"    Aviso: Extracao de audio falhou: {e}")
            return None


if __name__ == "__main__":
    downloader = VideoDownloader()
    test_video = {
        "platform": "tiktok",
        "id": "test123",
        "url": "https://www.tiktok.com/@example/video/123",
        "video_url": "",
    }
    result = downloader.download_all([test_video])
    print(result)
