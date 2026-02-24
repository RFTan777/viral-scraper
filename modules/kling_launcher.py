"""
=============================================================
MODULO: KLING.AI LAUNCHER — 100% GRATUITO
=============================================================
Abre o Kling.ai no browser automaticamente e copia cada
prompt cinematografico para a area de transferencia.

Sem API, sem custo. Voce so precisa ter conta no Kling.ai.
Crie sua conta gratis em: https://app.kling.ai

Fluxo automatico:
  1. Browser abre no Kling.ai
  2. Prompt copiado com Ctrl+C
  3. Voce cola (Ctrl+V) e clica Gerar
  4. Pressiona Enter para proximo prompt
"""

import io
import json
import subprocess
import sys
import webbrowser
from pathlib import Path

# Garante UTF-8 no terminal do Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from config import OUTPUT_DIR


KLING_URL = "https://app.kling.ai/video-editor/text-to-video"

# Instrucoes de uso exibidas para cada cena
INSTRUCOES = """
  COMO USAR NO KLING.AI:
  -------------------------------------------
  1. Cole o prompt (Ctrl+V) no campo de texto
  2. Duracao: 5s ou 10s
  3. Formato: 9:16 (Vertical - para Reels/TikTok)
  4. Camera Movement: Automatic (deixe a IA escolher)
  5. Clique em "Generate"
  6. Aguarde ~2 minutos
  7. Volte aqui e pressione Enter para o proximo
  -------------------------------------------
"""


class KlingLauncher:
    """Abre Kling.ai no browser com prompts copiados automaticamente."""

    def __init__(self):
        self.output_dir = OUTPUT_DIR

    def launch(self, scripts: list[dict]) -> None:
        """
        Abre Kling.ai para cada cena de cada roteiro.
        Copia prompt para clipboard antes de abrir.
        """
        prompts = self._collect_prompts(scripts)

        if not prompts:
            print("\n  AVISO: Nenhum ai_video_prompt encontrado.")
            print("  Gere os roteiros primeiro (opcao 4 no menu).")
            return

        self._save_prompts_txt(prompts)

        print(f"\n{'=' * 60}")
        print(f"  KLING.AI LAUNCHER — {len(prompts)} cenas para gerar")
        print(f"{'=' * 60}")
        print(f"\n  Todos os prompts salvos em:")
        print(f"  {self.output_dir / 'prompts_kling.txt'}")
        print(f"\n  Conta gratis: https://app.kling.ai (66 clips/dia)")

        print("\n  Voce quer:")
        print("    1. Modo automatico — abre browser e copia 1 por 1 [Enter]")
        print("    2. Modo manual — apenas mostra os prompts na tela")
        modo = input("\n  Escolha [1/2]: ").strip() or "1"

        if modo == "2":
            self._mostrar_todos(prompts)
            return

        print(INSTRUCOES)
        input("  Pressione Enter para comecar o primeiro prompt...")

        for i, p in enumerate(prompts, 1):
            self._processar_prompt(p, i, len(prompts))

            if i < len(prompts):
                resposta = input("\n  [Enter] = proximo prompt  |  [q] = sair: ").strip().lower()
                if resposta == "q":
                    print(f"\n  Parado em {i}/{len(prompts)}. Os demais estao em prompts_kling.txt")
                    break

        print(f"\n{'=' * 60}")
        print("  CONCLUIDO!")
        print(f"  {len(prompts)} prompts processados.")
        print(f"  Lembre de baixar os videos gerados no Kling.ai.")
        print(f"{'=' * 60}")

    def _processar_prompt(self, p: dict, index: int, total: int) -> None:
        """Exibe prompt, copia para clipboard e abre browser."""
        print(f"\n{'=' * 60}")
        print(f"  [{index}/{total}] {p['label']}")
        print(f"{'=' * 60}")

        if p.get("bloco"):
            print(f"  Bloco: {p['bloco']}")

        if p.get("fala"):
            fala = p["fala"]
            resumo = fala[:120] + "..." if len(fala) > 120 else fala
            print(f"  Fala: \"{resumo}\"")

        print(f"\n  PROMPT (copiado automaticamente):\n")
        # Indenta o prompt para legibilidade
        for linha in p["prompt"].split(". "):
            if linha.strip():
                print(f"    {linha.strip()}.")

        if p.get("negative"):
            print(f"\n  Negative: {p['negative']}")

        print(f"\n  Aspect Ratio: 9:16  |  Duracao sugerida: {p.get('duration', 5)}s")

        # Copiar para clipboard
        copiado = self._copy_to_clipboard(p["prompt"])
        if copiado:
            print("\n  Prompt copiado para o clipboard!")
        else:
            print("\n  AVISO: Nao foi possivel copiar automaticamente.")
            print("  Copie manualmente o prompt acima.")

        # Abrir browser
        webbrowser.open(KLING_URL)
        print("  Browser aberto no Kling.ai!")
        print(INSTRUCOES)

    def _mostrar_todos(self, prompts: list[dict]) -> None:
        """Exibe todos os prompts no terminal sem abrir browser."""
        print(f"\n{'=' * 60}")
        for i, p in enumerate(prompts, 1):
            print(f"\n[{i}/{len(prompts)}] {p['label']}")
            print(f"Bloco: {p['bloco']}")
            print(f"\nPROMPT:\n{p['prompt']}")
            if p.get("negative"):
                print(f"\nNegative: {p['negative']}")
            print("-" * 60)

    def _collect_prompts(self, scripts: list[dict]) -> list[dict]:
        """Extrai todos os ai_video_prompt dos roteiros."""
        prompts = []
        for script in scripts:
            titulo = script.get("titulo", "Roteiro")
            for cena in script.get("cenas", []):
                ai_p = cena.get("ai_video_prompt", {})
                prompt_text = ai_p.get("prompt_en", "")
                if not prompt_text:
                    continue

                fala_obj = cena.get("fala", {})
                fala_texto = fala_obj.get("texto", "") if isinstance(fala_obj, dict) else ""

                prompts.append({
                    "label": f"{titulo} — Cena {cena.get('numero', '?')} [{cena.get('momento', '')}]",
                    "prompt": prompt_text,
                    "negative": ai_p.get("negative_prompt_en", "blurry, low quality, watermark, text overlay, distorted face"),
                    "duration": ai_p.get("clip_duration_seconds", 5),
                    "bloco": cena.get("bloco", ""),
                    "fala": fala_texto,
                    "estilo": ai_p.get("style_reference", ""),
                })

        # Adicionar prompts globais se existirem
        for script in scripts:
            prod = script.get("ai_production_prompt", {})
            prompt_global = prod.get("prompt_global_en", "")
            if prompt_global:
                prompts.append({
                    "label": f"{script.get('titulo', 'Roteiro')} — PROMPT GLOBAL",
                    "prompt": prompt_global,
                    "negative": prod.get("parametros_api", {}).get("negative_prompt", "blurry, low quality"),
                    "duration": 10,
                    "bloco": "GLOBAL — Video Completo",
                    "fala": "",
                    "estilo": prod.get("style_guide_en", ""),
                })

        return prompts

    @staticmethod
    def _copy_to_clipboard(text: str) -> bool:
        """Copia texto para area de transferencia no Windows."""
        try:
            subprocess.run(
                ["clip"],
                input=text.encode("utf-8"),
                check=True,
                capture_output=True,
            )
            return True
        except FileNotFoundError:
            # Tenta xclip no Linux
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode("utf-8"),
                    check=True,
                    capture_output=True,
                )
                return True
            except Exception:
                return False
        except Exception:
            return False

    def _save_prompts_txt(self, prompts: list[dict]) -> None:
        """Salva todos os prompts em arquivo .txt para consulta."""
        path = self.output_dir / "prompts_kling.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write("PROMPTS PARA KLING.AI\n")
            f.write("Copie e cole cada prompt em: https://app.kling.ai\n")
            f.write("Configuracao: Duracao 5-10s | Formato 9:16 Vertical\n\n")
            f.write("=" * 60 + "\n\n")

            for i, p in enumerate(prompts, 1):
                f.write(f"[{i}] {p['label']}\n")
                f.write(f"Bloco: {p['bloco']}\n")
                if p.get("fala"):
                    f.write(f"Fala: \"{p['fala']}\"\n")
                f.write(f"Estilo: {p.get('estilo', '')}\n")
                f.write(f"\nPROMPT:\n{p['prompt']}\n")
                f.write(f"\nNEGATIVE PROMPT:\n{p.get('negative', '')}\n")
                f.write(f"\nDuracao sugerida: {p.get('duration', 5)}s | Aspect Ratio: 9:16\n")
                f.write("\n" + "-" * 60 + "\n\n")
