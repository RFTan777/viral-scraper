"""
=============================================================
MODULO: RATE LIMITING AWARENESS
=============================================================
Rastreia uso diario de APIs para evitar exceder limites:
- Gemini: 1500 req/dia (free tier)
- Groq: 14400 req/dia (free tier)
"""

import json
from pathlib import Path
from datetime import datetime, date
from config import DATA_DIR


class RateTracker:
    """Rastreia uso diario de APIs."""

    DEFAULT_LIMITS = {
        "gemini": 1500,
        "groq": 14400,
    }

    WARNING_THRESHOLD = 0.80  # Avisar quando atingir 80% do limite

    def __init__(self, filepath: str | Path | None = None):
        self.filepath = Path(filepath) if filepath else DATA_DIR / "rate_usage.json"
        self.usage: dict = {}
        self._load()

    def _load(self):
        """Carrega dados de uso do disco."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.usage = json.load(f)
            except (json.JSONDecodeError, KeyError):
                self.usage = {}

        # Resetar se e um novo dia
        today = date.today().isoformat()
        if self.usage.get("date") != today:
            self.usage = {"date": today}

    def _save(self):
        """Salva dados de uso no disco."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.usage, f, ensure_ascii=False, indent=2)

    def track(self, api: str, count: int = 1):
        """
        Registra uso de uma API.

        Args:
            api: Nome da API ("gemini" ou "groq")
            count: Numero de requests
        """
        today = date.today().isoformat()
        if self.usage.get("date") != today:
            self.usage = {"date": today}

        current = self.usage.get(api, 0)
        self.usage[api] = current + count
        self._save()

        # Verificar limites
        limit = self.DEFAULT_LIMITS.get(api, float("inf"))
        used = self.usage[api]
        pct = used / limit if limit > 0 else 0

        if pct >= 1.0:
            print(f"  [RateTracker] LIMITE ATINGIDO: {api} ({used}/{limit})")
        elif pct >= self.WARNING_THRESHOLD:
            remaining = limit - used
            print(f"  [RateTracker] AVISO: {api} em {pct:.0%} do limite ({used}/{limit}, restam {remaining})")

    def get_usage(self, api: str) -> int:
        """Retorna uso atual de uma API."""
        today = date.today().isoformat()
        if self.usage.get("date") != today:
            return 0
        return self.usage.get(api, 0)

    def get_remaining(self, api: str) -> int:
        """Retorna requests restantes para uma API."""
        limit = self.DEFAULT_LIMITS.get(api, float("inf"))
        used = self.get_usage(api)
        return max(0, int(limit - used))

    def can_proceed(self, api: str, needed: int = 1) -> bool:
        """Verifica se ha requests suficientes para prosseguir."""
        return self.get_remaining(api) >= needed

    def print_status(self):
        """Mostra status de uso de todas as APIs."""
        today = date.today().isoformat()
        print(f"\n  [RateTracker] Uso em {today}:")
        for api, limit in self.DEFAULT_LIMITS.items():
            used = self.get_usage(api)
            remaining = max(0, limit - used)
            pct = used / limit if limit > 0 else 0
            status = "OK" if pct < self.WARNING_THRESHOLD else ("AVISO" if pct < 1.0 else "LIMITE")
            print(f"    {api}: {used}/{limit} ({pct:.0%}) — restam {remaining} [{status}]")
