"""
=============================================================
MODULO: ENVIO PARA IA DE CRIACAO DE VIDEO (fal.ai)
=============================================================
Envia prompts cinematograficos dos roteiros para APIs de IA
de geracao de video. Suporte a Kling 1.6 e Wan2.1 via fal.ai.

APIs gratuitas suportadas:
  - Kling AI v1.6 Standard (fal.ai) — realismo, alta qualidade
  - Wan2.1 1.3B (fal.ai) — open source, rapido
  - CogVideoX-5b (fal.ai) — open source, bom para b-rolls

Creditos gratuitos: fal.ai oferece creditos ao criar conta.
Crie sua chave em: https://fal.ai/dashboard/keys
"""

import json
import time
import requests
from pathlib import Path

from config import OUTPUT_DIR


# -----------------------------------------------------------
# ENDPOINTS DOS MODELOS (fal.ai queue API)
# -----------------------------------------------------------

MODELS = {
    "kling": {
        "id": "fal-ai/kling-video/v1.6/standard/text-to-video",
        "nome": "Kling AI v1.6 Standard",
        "max_duration": 10,
        "descricao": "Alta qualidade, realismo excelente, ideal para pessoas",
    },
    "kling_pro": {
        "id": "fal-ai/kling-video/v1.6/pro/text-to-video",
        "nome": "Kling AI v1.6 Pro",
        "max_duration": 10,
        "descricao": "Qualidade maxima, mais lento, melhor para cenas principais",
    },
    "wan": {
        "id": "fal-ai/wan/v2.1/1.3b/text-to-video",
        "nome": "Wan2.1 1.3B",
        "max_duration": 5,
        "descricao": "Open source rapido, bom para b-rolls e ambientes",
    },
    "wan_14b": {
        "id": "fal-ai/wan/v2.1/14b/text-to-video",
        "nome": "Wan2.1 14B",
        "max_duration": 5,
        "descricao": "Open source alta qualidade, melhor resultado do Wan",
    },
    "cogvideo": {
        "id": "fal-ai/cogvideox-5b",
        "nome": "CogVideoX-5b",
        "max_duration": 6,
        "descricao": "Open source, bom para conteudo editorial",
    },
}

FAL_QUEUE_BASE = "https://queue.fal.run"
POLL_INTERVAL = 8   # segundos entre cada verificacao de status
MAX_POLL_ATTEMPTS = 75  # 75 * 8s = 10 minutos maximos por clip


class VideoAISender:
    """Envia roteiros para IAs de criacao de video via fal.ai."""

    def __init__(self, fal_api_key: str, model: str = "kling"):
        if model not in MODELS:
            raise ValueError(f"Modelo '{model}' invalido. Opcoes: {list(MODELS.keys())}")

        self.api_key = fal_api_key
        self.model_key = model
        self.model_info = MODELS[model]
        self.model_id = self.model_info["id"]

        self.output_dir = OUTPUT_DIR / "video_gerado"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

    # ----------------------------------------------------------
    # ENVIO DE ROTEIRO COMPLETO
    # ----------------------------------------------------------

    def send_script(self, script: dict) -> dict:
        """
        Envia um roteiro completo para geracao de video.
        Gera um clip por cena que tenha ai_video_prompt.
        Retorna dicionario com URLs e paths dos clips gerados.
        """
        titulo = script.get("titulo", "Sem titulo")
        print(f"\n{'=' * 60}")
        print(f"  IA DE VIDEO: {titulo}")
        print(f"  Modelo: {self.model_info['nome']}")
        print(f"  {self.model_info['descricao']}")
        print(f"{'=' * 60}")

        scene_prompts = self._extract_scene_prompts(script)
        global_prompt = self._extract_global_prompt(script)

        if not scene_prompts and not global_prompt:
            print("  AVISO: Nenhum ai_video_prompt encontrado no roteiro.")
            return {"status": "sem_prompts", "titulo": titulo, "clips": []}

        print(f"\n  {len(scene_prompts)} cena(s) para gerar")

        results = []
        for i, prompt_data in enumerate(scene_prompts, 1):
            print(f"\n  [{i}/{len(scene_prompts)}] Gerando: {prompt_data['label']}")
            print(f"    Prompt: {prompt_data['prompt'][:120]}...")

            result = self._generate_and_download(prompt_data, i)
            results.append(result)

            if result["status"] == "ok":
                print(f"    OK! Clip salvo: {result.get('local_path', result.get('url', ''))}")
            else:
                print(f"    ERRO: {result.get('erro', 'desconhecido')}")

            # Pausa entre requisicoes para evitar rate limit
            if i < len(scene_prompts):
                time.sleep(2)

        # Salvar resultado em JSON
        output_data = {
            "titulo": titulo,
            "modelo": self.model_info["nome"],
            "total_cenas": len(scene_prompts),
            "clips_gerados": sum(1 for r in results if r["status"] == "ok"),
            "clips": results,
        }
        self._save_results(output_data, titulo)

        print(f"\n  Total: {output_data['clips_gerados']}/{len(scene_prompts)} clips gerados")
        return output_data

    def send_global_prompt(self, script: dict) -> dict:
        """
        Envia apenas o prompt global do roteiro (video inteiro de uma vez).
        Util para gerar uma versao completa de 5-10s representando o video.
        """
        global_prompt = self._extract_global_prompt(script)
        if not global_prompt:
            print("  AVISO: ai_production_prompt nao encontrado no roteiro.")
            return {"status": "sem_prompt_global"}

        titulo = script.get("titulo", "video")
        print(f"\n  Gerando video global: {titulo}")
        print(f"  Prompt: {global_prompt['prompt'][:120]}...")

        result = self._generate_and_download(global_prompt, 0)
        return result

    # ----------------------------------------------------------
    # EXTRACAO DE PROMPTS DO ROTEIRO
    # ----------------------------------------------------------

    def _extract_scene_prompts(self, script: dict) -> list[dict]:
        """Extrai ai_video_prompt de cada cena do roteiro."""
        prompts = []
        for cena in script.get("cenas", []):
            ai_p = cena.get("ai_video_prompt", {})
            prompt_text = ai_p.get("prompt_en", "")
            if not prompt_text:
                continue

            duration = ai_p.get("clip_duration_seconds", 5)
            duration = min(int(duration), self.model_info["max_duration"])

            prompts.append({
                "label": f"Cena {cena.get('numero', '?')} [{cena.get('momento', '')}] {cena.get('bloco', '')}",
                "prompt": prompt_text,
                "negative_prompt": ai_p.get("negative_prompt_en", "blurry, low quality, watermark, text overlay, distorted face"),
                "duration": duration,
                "aspect_ratio": ai_p.get("aspect_ratio", "9:16"),
                "cena_numero": cena.get("numero", 0),
                "bloco": cena.get("bloco", ""),
                "fala": cena.get("fala", {}).get("texto", "") if isinstance(cena.get("fala"), dict) else "",
            })
        return prompts

    def _extract_global_prompt(self, script: dict) -> dict | None:
        """Extrai o prompt global de producao do roteiro."""
        prod = script.get("ai_production_prompt", {})
        prompt_text = prod.get("prompt_global_en", "")
        if not prompt_text:
            return None

        parametros = prod.get("parametros_api", {})
        return {
            "label": "Prompt Global — Video Completo",
            "prompt": prompt_text,
            "negative_prompt": parametros.get("negative_prompt", "blurry, low quality, watermark, distorted"),
            "duration": min(10, self.model_info["max_duration"]),
            "aspect_ratio": parametros.get("aspect_ratio", "9:16"),
            "cena_numero": 0,
            "bloco": "GLOBAL",
            "fala": "",
        }

    # ----------------------------------------------------------
    # GERACAO VIA fal.ai
    # ----------------------------------------------------------

    def _generate_and_download(self, prompt_data: dict, index: int) -> dict:
        """Submete, aguarda e baixa um clip gerado pela IA."""
        try:
            request_id = self._submit_job(prompt_data)
        except requests.HTTPError as e:
            return {
                "status": "erro",
                "label": prompt_data["label"],
                "erro": f"HTTP {e.response.status_code}: {e.response.text[:300]}",
            }
        except Exception as e:
            return {"status": "erro", "label": prompt_data["label"], "erro": str(e)}

        print(f"    Job enviado: {request_id}")

        try:
            video_url = self._poll_until_done(request_id)
        except TimeoutError:
            return {"status": "timeout", "label": prompt_data["label"], "request_id": request_id}
        except Exception as e:
            return {"status": "erro", "label": prompt_data["label"], "erro": str(e)}

        if not video_url:
            return {"status": "sem_url", "label": prompt_data["label"], "request_id": request_id}

        local_path = self._download_clip(video_url, index, prompt_data["cena_numero"])

        return {
            "status": "ok",
            "label": prompt_data["label"],
            "bloco": prompt_data["bloco"],
            "url": video_url,
            "local_path": str(local_path) if local_path else None,
            "request_id": request_id,
            "fala": prompt_data.get("fala", ""),
        }

    def _submit_job(self, prompt_data: dict) -> str:
        """Envia job para fila do fal.ai e retorna request_id."""
        endpoint = f"{FAL_QUEUE_BASE}/{self.model_id}"

        payload = {
            "prompt": prompt_data["prompt"],
            "negative_prompt": prompt_data.get("negative_prompt", ""),
            "duration": str(prompt_data.get("duration", 5)),
            "aspect_ratio": prompt_data.get("aspect_ratio", "9:16"),
        }

        resp = requests.post(endpoint, headers=self._headers, json=payload, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        request_id = data.get("request_id")
        if not request_id:
            raise ValueError(f"request_id ausente na resposta: {data}")
        return request_id

    def _poll_until_done(self, request_id: str) -> str | None:
        """Aguarda geracao e retorna URL do video quando pronto."""
        status_url = f"{FAL_QUEUE_BASE}/{self.model_id}/requests/{request_id}/status"
        result_url = f"{FAL_QUEUE_BASE}/{self.model_id}/requests/{request_id}"

        for attempt in range(MAX_POLL_ATTEMPTS):
            time.sleep(POLL_INTERVAL)

            resp = requests.get(status_url, headers=self._headers, timeout=15)
            resp.raise_for_status()
            status_data = resp.json()
            status = status_data.get("status", "")

            elapsed = (attempt + 1) * POLL_INTERVAL
            print(f"    [{elapsed}s] Status: {status}")

            if status == "COMPLETED":
                result_resp = requests.get(result_url, headers=self._headers, timeout=15)
                result_resp.raise_for_status()
                result = result_resp.json()
                return self._extract_video_url(result)

            if status == "FAILED":
                error = status_data.get("error", "erro desconhecido")
                raise RuntimeError(f"Geracao falhou: {error}")

        raise TimeoutError(f"Timeout apos {MAX_POLL_ATTEMPTS * POLL_INTERVAL}s")

    @staticmethod
    def _extract_video_url(result: dict) -> str | None:
        """Extrai URL do video do resultado da API."""
        # fal.ai retorna em formatos diferentes dependendo do modelo
        if "video" in result:
            v = result["video"]
            if isinstance(v, dict):
                return v.get("url") or v.get("file_url")
            if isinstance(v, str):
                return v

        if "videos" in result and result["videos"]:
            v = result["videos"][0]
            if isinstance(v, dict):
                return v.get("url") or v.get("file_url")

        # fallback
        for key in ("url", "file_url", "output_url"):
            if key in result:
                return result[key]

        return None

    def _download_clip(self, url: str, index: int, cena_numero: int) -> Path | None:
        """Baixa o clip gerado para o diretorio de saida."""
        try:
            resp = requests.get(url, timeout=120, stream=True)
            resp.raise_for_status()

            ext = ".mp4"
            filename = f"clip_{index:02d}_cena{cena_numero:02d}{ext}"
            path = self.output_dir / filename

            with open(path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            return path
        except Exception as e:
            print(f"    AVISO: Nao foi possivel baixar o clip: {e}")
            return None

    # ----------------------------------------------------------
    # SALVAR RESULTADOS
    # ----------------------------------------------------------

    def _save_results(self, data: dict, titulo: str):
        """Salva resultados da geracao em JSON."""
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in titulo)[:50]
        path = self.output_dir / f"resultado_{safe_name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  Resultado salvo: {path}")

    # ----------------------------------------------------------
    # UTILITARIOS
    # ----------------------------------------------------------

    @classmethod
    def listar_modelos(cls):
        """Mostra os modelos disponiveis."""
        print("\n  MODELOS DISPONIVEIS (fal.ai):")
        print("  " + "-" * 50)
        for key, info in MODELS.items():
            print(f"  {key:12s} | {info['nome']}")
            print(f"             | {info['descricao']}")
            print(f"             | Max: {info['max_duration']}s por clip")
            print()

    @staticmethod
    def validar_chave(fal_api_key: str) -> bool:
        """Valida se a chave da API fal.ai e valida."""
        test_url = "https://fal.run/fal-ai/fast-sdxl"
        headers = {"Authorization": f"Key {fal_api_key}"}
        try:
            resp = requests.get(test_url, headers=headers, timeout=10)
            return resp.status_code != 401
        except Exception:
            return False
