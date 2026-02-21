"""
=============================================================
MODULO: DEDUPLICACAO
=============================================================
Rastreia videos ja processados para evitar reprocessamento.
Salva IDs processados em processed_ids.json.
"""

import json
from pathlib import Path
from config import DATA_DIR


class DeduplicationTracker:
    """Rastreia videos ja processados para evitar duplicatas."""

    def __init__(self, filepath: str | Path | None = None):
        self.filepath = Path(filepath) if filepath else DATA_DIR / "processed_ids.json"
        self.processed: set[str] = set()
        self._load()

    def _load(self):
        """Carrega IDs ja processados do disco."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.processed = set(data.get("processed_ids", []))
            except (json.JSONDecodeError, KeyError):
                self.processed = set()

    def _save(self):
        """Salva IDs processados no disco."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(
                {"processed_ids": sorted(self.processed)},
                f, ensure_ascii=False, indent=2
            )

    def filter_new(self, videos: list[dict]) -> tuple[list[dict], int]:
        """
        Filtra apenas videos que ainda nao foram processados.

        Args:
            videos: Lista de dicts com campo 'id'

        Returns:
            (videos_novos, quantidade_duplicados)
        """
        new_videos = []
        duplicates = 0

        for video in videos:
            video_id = self._make_id(video)
            if video_id in self.processed:
                duplicates += 1
            else:
                new_videos.append(video)

        if duplicates > 0:
            print(f"  Dedup: {duplicates} videos ja processados removidos, {len(new_videos)} novos")

        return new_videos, duplicates

    def mark_batch(self, videos: list[dict]):
        """
        Marca um lote de videos como processados.

        Args:
            videos: Lista de dicts com campo 'id'
        """
        for video in videos:
            video_id = self._make_id(video)
            self.processed.add(video_id)

        self._save()
        print(f"  Dedup: {len(videos)} videos marcados como processados (total: {len(self.processed)})")

    def is_processed(self, video: dict) -> bool:
        """Verifica se um video ja foi processado."""
        return self._make_id(video) in self.processed

    @staticmethod
    def _make_id(video: dict) -> str:
        """Cria ID unico para o video (platform_id)."""
        platform = video.get("platform", "unknown")
        video_id = video.get("id", "")
        return f"{platform}_{video_id}"

    @property
    def total_processed(self) -> int:
        """Numero total de videos ja processados."""
        return len(self.processed)
