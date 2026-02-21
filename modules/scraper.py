"""
=============================================================
MODULO 1: SCRAPER (Apify)
=============================================================
Coleta videos virais do TikTok e Instagram via Apify API.
"""

import json
import requests
import time
from datetime import datetime
from config import APIFY_API_TOKEN, SCRAPING, DATA_DIR
from modules.retry import apify_retry


class ApifyScraper:
    """Cliente para scraping via Apify."""

    BASE_URL = "https://api.apify.com/v2"

    def __init__(self):
        self.token = APIFY_API_TOKEN
        self.headers = {"Content-Type": "application/json"}

    @apify_retry
    def _run_actor(self, actor_id: str, input_data: dict, timeout: int = 300) -> list:
        """
        Executa um Actor no Apify e aguarda o resultado.

        Args:
            actor_id: ID do actor (ex: 'clockworks/free-tiktok-scraper')
            input_data: Parametros de entrada do actor
            timeout: Tempo maximo de espera em segundos

        Returns:
            Lista de items retornados pelo actor
        """
        # 1. Iniciar o Actor
        url = f"{self.BASE_URL}/acts/{actor_id}/runs?token={self.token}"
        print(f"  Iniciando actor: {actor_id}...")

        response = requests.post(url, headers=self.headers, json=input_data)
        response.raise_for_status()
        run_data = response.json()["data"]
        run_id = run_data["id"]

        print(f"  Run iniciada: {run_id}")

        # 2. Aguardar conclusao (polling)
        status_url = f"{self.BASE_URL}/actor-runs/{run_id}?token={self.token}"
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Actor {actor_id} excedeu {timeout}s")

            status_resp = requests.get(status_url)
            status = status_resp.json()["data"]["status"]

            if status == "SUCCEEDED":
                print(f"  Actor concluido com sucesso!")
                break
            elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                raise RuntimeError(f"Actor falhou com status: {status}")

            print(f"  Status: {status}... aguardando 5s")
            time.sleep(5)

        # 3. Buscar resultados do dataset
        dataset_id = run_data["defaultDatasetId"]
        dataset_url = f"{self.BASE_URL}/datasets/{dataset_id}/items?token={self.token}"
        dataset_resp = requests.get(dataset_url)
        items = dataset_resp.json()

        print(f"  {len(items)} items coletados")
        return items

    # -----------------------------------------
    # TIKTOK
    # -----------------------------------------

    def scrape_tiktok(
        self,
        hashtags: list[str] = None,
        profiles: list[str] = None,
        keywords: list[str] = None,
    ) -> list[dict]:
        """
        Scrape videos virais do TikTok.

        Args:
            hashtags: Lista de hashtags (ex: ['fitness', 'receitas'])
            profiles: Lista de perfis (ex: ['@username'])
            keywords: Lista de palavras-chave para busca

        Returns:
            Lista de videos com metricas normalizadas
        """
        print("\n" + "=" * 60)
        print("SCRAPING TIKTOK")
        print("=" * 60)

        input_data = {
            "maxItems": SCRAPING["max_videos_tiktok"],
            "resultsPerPage": SCRAPING["max_videos_tiktok"],
        }

        # Configurar fonte de busca
        if hashtags:
            input_data["hashtags"] = hashtags
            print(f"  Hashtags: {hashtags}")
        if profiles:
            input_data["profiles"] = profiles
            print(f"  Perfis: {profiles}")
        if keywords:
            input_data["searchQueries"] = keywords
            print(f"  Keywords: {keywords}")

        raw_items = self._run_actor(SCRAPING["tiktok_actor"], input_data)

        # Normalizar dados
        videos = []
        for item in raw_items:
            video = self._normalize_tiktok(item)
            if video and video["views"] >= SCRAPING["min_views_tiktok"]:
                videos.append(video)

        # Ordenar por engajamento
        videos = self._sort_videos(videos)

        print(f"  {len(videos)} videos virais encontrados (>{SCRAPING['min_views_tiktok']:,} views)")
        return videos

    def _normalize_tiktok(self, raw: dict) -> dict | None:
        """Normaliza dados brutos do TikTok para formato padrao."""
        try:
            views = raw.get("playCount", raw.get("plays", 0)) or 0
            likes = raw.get("diggCount", raw.get("likes", 0)) or 0
            comments = raw.get("commentCount", raw.get("comments", 0)) or 0
            shares = raw.get("shareCount", raw.get("shares", 0)) or 0

            engagement_rate = ((likes + comments + shares) / views * 100) if views > 0 else 0

            return {
                "platform": "tiktok",
                "id": raw.get("id", ""),
                "url": raw.get("webVideoUrl", raw.get("url", "")),
                "video_url": raw.get("videoUrl", raw.get("video_url", "")),
                "description": raw.get("text", raw.get("desc", "")),
                "author": raw.get("authorMeta", {}).get("name", raw.get("author", "")),
                "author_followers": raw.get("authorMeta", {}).get("fans", 0),
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "saves": raw.get("collectCount", 0) or 0,
                "engagement_rate": round(engagement_rate, 2),
                "duration": raw.get("videoMeta", {}).get("duration", raw.get("duration", 0)),
                "hashtags": [h.get("name", h) if isinstance(h, dict) else h
                             for h in raw.get("hashtags", [])],
                "music": raw.get("musicMeta", {}).get("musicName", raw.get("music", "")),
                "created_at": raw.get("createTimeISO", raw.get("createTime", "")),
                "cover_url": raw.get("covers", {}).get("default", ""),
                "scraped_at": datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"  Aviso: Erro normalizando item TikTok: {e}")
            return None

    # -----------------------------------------
    # INSTAGRAM
    # -----------------------------------------

    def scrape_instagram(
        self,
        hashtags: list[str] = None,
        profiles: list[str] = None,
        urls: list[str] = None,
    ) -> list[dict]:
        """
        Scrape reels/posts virais do Instagram.

        Args:
            hashtags: Lista de hashtags
            profiles: Lista de perfis (ex: ['instagram.com/username'])
            urls: Lista de URLs diretas de posts

        Returns:
            Lista de videos com metricas normalizadas
        """
        print("\n" + "=" * 60)
        print("SCRAPING INSTAGRAM")
        print("=" * 60)

        input_data = {
            "resultsLimit": SCRAPING["max_videos_instagram"],
            "resultsType": "posts",
        }

        if hashtags:
            input_data["hashtags"] = hashtags
            print(f"  Hashtags: {hashtags}")
        if profiles:
            input_data["directUrls"] = [
                f"https://www.instagram.com/{p.replace('@', '')}/"
                for p in profiles
            ]
            print(f"  Perfis: {profiles}")
        if urls:
            input_data["directUrls"] = urls

        raw_items = self._run_actor(SCRAPING["instagram_actor"], input_data)

        # Normalizar e filtrar apenas videos/reels
        videos = []
        for item in raw_items:
            video = self._normalize_instagram(item)
            if video and video["views"] >= SCRAPING["min_views_instagram"]:
                videos.append(video)

        videos = self._sort_videos(videos)

        print(f"  {len(videos)} reels virais encontrados (>{SCRAPING['min_views_instagram']:,} views)")
        return videos

    def _normalize_instagram(self, raw: dict) -> dict | None:
        """Normaliza dados brutos do Instagram para formato padrao."""
        try:
            # Filtrar apenas videos/reels
            media_type = raw.get("type", raw.get("productType", ""))
            if media_type not in ("video", "reels", "Video", "Reels", "clips"):
                # Tentar detectar por outras propriedades
                if not raw.get("videoUrl") and not raw.get("video_url"):
                    return None

            views = raw.get("videoPlayCount", raw.get("videoViewCount", raw.get("plays", 0))) or 0
            likes = raw.get("likesCount", raw.get("likes", 0)) or 0
            comments = raw.get("commentsCount", raw.get("comments", 0)) or 0

            engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0

            return {
                "platform": "instagram",
                "id": raw.get("id", raw.get("shortCode", "")),
                "url": raw.get("url", raw.get("postUrl", "")),
                "video_url": raw.get("videoUrl", raw.get("video_url", "")),
                "description": raw.get("caption", raw.get("text", "")),
                "author": raw.get("ownerUsername", raw.get("owner", {}).get("username", "")),
                "author_followers": raw.get("ownerFollowerCount", 0),
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": 0,  # Instagram nao expoe shares publicamente
                "saves": 0,
                "engagement_rate": round(engagement_rate, 2),
                "duration": raw.get("videoDuration", 0),
                "hashtags": raw.get("hashtags", []),
                "music": raw.get("musicInfo", {}).get("title", "") if raw.get("musicInfo") else "",
                "created_at": raw.get("timestamp", raw.get("takenAt", "")),
                "cover_url": raw.get("displayUrl", raw.get("thumbnailUrl", "")),
                "scraped_at": datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"  Aviso: Erro normalizando item Instagram: {e}")
            return None

    # -----------------------------------------
    # UTILIDADES
    # -----------------------------------------

    def _sort_videos(self, videos: list[dict]) -> list[dict]:
        """Ordena videos por criterio configurado."""
        sort_key = SCRAPING["sort_by"]

        if sort_key == "engagement":
            return sorted(videos, key=lambda v: v["engagement_rate"], reverse=True)
        elif sort_key == "views":
            return sorted(videos, key=lambda v: v["views"], reverse=True)
        else:  # recent
            return sorted(videos, key=lambda v: v["created_at"], reverse=True)

    def save_results(self, videos: list[dict], filename: str = "scraped_videos.json"):
        """Salva resultados em JSON."""
        filepath = DATA_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(videos, f, ensure_ascii=False, indent=2)
        print(f"\n  Resultados salvos em: {filepath}")
        return filepath


# -----------------------------------------
# USO DIRETO
# -----------------------------------------

if __name__ == "__main__":
    scraper = ApifyScraper()

    # Exemplo: scraping por hashtag
    tiktok_videos = scraper.scrape_tiktok(hashtags=["marketing digital"])
    instagram_videos = scraper.scrape_instagram(hashtags=["marketing digital"])

    all_videos = tiktok_videos + instagram_videos
    scraper.save_results(all_videos)
