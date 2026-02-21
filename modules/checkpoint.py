"""
=============================================================
MODULO: CHECKPOINT / RESUME DO PIPELINE
=============================================================
Salva estado apos CADA etapa do pipeline, permitindo retomar
de onde parou em caso de interrupcao.
"""

import json
from pathlib import Path
from datetime import datetime
from config import DATA_DIR


class PipelineCheckpoint:
    """Salva e restaura estado do pipeline para resume."""

    STAGES = [
        "scraping",
        "filter_a",
        "download",
        "transcription",
        "filter_b",
        "video_analysis",
        "content_analysis",
        "script_generation",
    ]

    def __init__(self, filepath: str | Path | None = None):
        self.filepath = Path(filepath) if filepath else DATA_DIR / "checkpoint.json"
        self.state: dict = {}
        self._load()

    def _load(self):
        """Carrega checkpoint existente do disco."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except (json.JSONDecodeError, KeyError):
                self.state = {}

    def _save(self):
        """Salva checkpoint no disco."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2, default=str)

    def has_checkpoint(self) -> bool:
        """Verifica se existe um checkpoint salvo."""
        return bool(self.state.get("last_completed_stage"))

    def get_last_stage(self) -> str | None:
        """Retorna a ultima etapa completada."""
        return self.state.get("last_completed_stage")

    def get_next_stage(self) -> str | None:
        """Retorna a proxima etapa a ser executada."""
        last = self.get_last_stage()
        if not last:
            return self.STAGES[0]

        try:
            idx = self.STAGES.index(last)
            if idx + 1 < len(self.STAGES):
                return self.STAGES[idx + 1]
            return None  # Pipeline completo
        except ValueError:
            return self.STAGES[0]

    def should_skip(self, stage: str) -> bool:
        """Verifica se uma etapa deve ser pulada (ja completada)."""
        last = self.get_last_stage()
        if not last:
            return False

        try:
            last_idx = self.STAGES.index(last)
            stage_idx = self.STAGES.index(stage)
            return stage_idx <= last_idx
        except ValueError:
            return False

    def save_stage(self, stage: str, videos: list[dict], extra_data: dict | None = None):
        """
        Salva checkpoint apos completar uma etapa.

        Args:
            stage: Nome da etapa completada
            videos: Estado atual dos videos
            extra_data: Dados extras a salvar (ex: search_params, niche)
        """
        self.state["last_completed_stage"] = stage
        self.state["last_updated"] = datetime.now().isoformat()
        self.state["video_count"] = len(videos)

        # Salvar videos de forma serializavel
        serializable = []
        for v in videos:
            serializable.append(dict(v))
        self.state["videos"] = serializable

        if extra_data:
            self.state["extra_data"] = extra_data

        self._save()
        print(f"  [Checkpoint] Etapa '{stage}' salva ({len(videos)} videos)")

    def load_videos(self) -> list[dict]:
        """Carrega videos do checkpoint."""
        return self.state.get("videos", [])

    def load_extra_data(self) -> dict:
        """Carrega dados extras do checkpoint."""
        return self.state.get("extra_data", {})

    def clear(self):
        """Limpa o checkpoint (pipeline completo ou novo inicio)."""
        self.state = {}
        if self.filepath.exists():
            self.filepath.unlink()

    def print_status(self):
        """Mostra status do checkpoint."""
        if not self.has_checkpoint():
            print("  [Checkpoint] Nenhum checkpoint encontrado")
            return

        last = self.get_last_stage()
        next_stage = self.get_next_stage()
        count = self.state.get("video_count", 0)
        updated = self.state.get("last_updated", "?")

        print(f"\n  [Checkpoint] Checkpoint encontrado!")
        print(f"    Ultima etapa: {last}")
        print(f"    Proxima etapa: {next_stage or 'pipeline completo'}")
        print(f"    Videos salvos: {count}")
        print(f"    Atualizado em: {updated}")
