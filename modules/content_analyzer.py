"""
=============================================================
MODULO 5: ANALISADOR DE CONTEUDO (Google Gemini -- GRATUITO)
=============================================================
Desconstrucao de videos virais com nicho DINAMICO.
Extrai os 4 pilares genericos de conteudo viral:
  1) Gancho (como captura atencao)
  2) Credibilidade (como prova autoridade)
  3) Conteudo Central (como entrega valor)
  4) CTA (como direciona para acao)

Gemini 2.5 Flash = 1500 req/dia gratis = ~75 videos analisados/dia
"""

import json
import base64
from pathlib import Path
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI, OUTPUT_DIR
from modules.retry import gemini_retry


class ContentAnalyzer:
    """Desconstrucao de videos virais usando Gemini (gratuito). Nicho dinamico."""

    def __init__(self, niche: str = ""):
        self.niche = niche or "conteudo viral"
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=GEMINI["model"],
            generation_config={
                "max_output_tokens": GEMINI["max_tokens"],
                "temperature": GEMINI["temperature_analysis"],
            },
        )

    def analyze_all(self, videos: list[dict]) -> list[dict]:
        """
        Analisa profundamente todos os videos coletados.

        Args:
            videos: Lista completa com scraping + transcricao + video_analysis

        Returns:
            Lista atualizada com analise de conteudo
        """
        print("\n" + "=" * 60)
        print(f"DESCONSTRUCAO DE CONTEUDO — Nicho: {self.niche}")
        print("=" * 60)

        for i, video in enumerate(videos, 1):
            if not video.get("transcription"):
                print(f"  [{i}] Aviso: Sem transcricao para {video['id']}, pulando...")
                video["content_analysis"] = None
                continue

            print(f"  [{i}/{len(videos)}] Desconstruindo: {video['author']} ({video['platform']})")

            try:
                analysis = self._deep_analyze(video)
                video["content_analysis"] = analysis
                print(f"    OK: Desconstrucao completa!")
                gancho = analysis.get("gancho", {})
                cred = analysis.get("credibilidade", {})
                conteudo = analysis.get("conteudo_central", {})
                cta = analysis.get("cta", {})
                print(f"    Gancho: {gancho.get('score', '?')}/10")
                print(f"    Credibilidade: {cred.get('score', '?')}/10")
                print(f"    Conteudo: {conteudo.get('score', '?')}/10")
                print(f"    CTA: {cta.get('score', '?')}/10")
            except Exception as e:
                print(f"    ERRO: {e}")
                video["content_analysis"] = None

        analyzed = sum(1 for v in videos if v.get("content_analysis"))
        print(f"\n  {analyzed}/{len(videos)} videos desconstruidos")
        return videos

    @gemini_retry
    def _deep_analyze(self, video: dict) -> dict:
        """Analise profunda de um video individual usando Gemini."""

        transcription = video["transcription"]
        video_data = video.get("video_analysis", {}) or {}
        metrics = {
            "views": video.get("views", 0),
            "likes": video.get("likes", 0),
            "comments": video.get("comments", 0),
            "shares": video.get("shares", 0),
            "engagement_rate": video.get("engagement_rate", 0),
            "author_followers": video.get("author_followers", 0),
        }

        # Construir conteudo com imagens (frames)
        content_parts = []

        frames = video_data.get("extracted_frames", [])
        if frames:
            for frame_path in frames[:4]:
                if Path(frame_path).exists():
                    try:
                        img_data = Path(frame_path).read_bytes()
                        content_parts.append({
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": base64.b64encode(img_data).decode("utf-8"),
                            }
                        })
                    except Exception:
                        pass

        # Adicionar prompt de analise
        prompt = self._build_analysis_prompt(video, transcription, video_data, metrics)
        content_parts.append(prompt)

        response = self.model.generate_content(
            content_parts,
            generation_config={
                "temperature": GEMINI["temperature_analysis"],
                "max_output_tokens": GEMINI["max_tokens"],
            },
        )

        response_text = self._extract_response_text(response)
        if not response_text:
            return {"raw_analysis": "Gemini nao retornou resposta (possivel bloqueio de seguranca)"}

        try:
            clean = response_text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()

            json_start = clean.find("{")
            json_end = clean.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(clean[json_start:json_end])
            else:
                analysis = {"raw_analysis": response_text}
        except json.JSONDecodeError:
            analysis = {"raw_analysis": response_text}

        return analysis

    @staticmethod
    def _extract_response_text(response) -> str:
        """Extrai texto da resposta do Gemini de forma segura."""
        try:
            return response.text
        except (ValueError, AttributeError):
            pass
        try:
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    return candidate.content.parts[0].text
        except (AttributeError, IndexError, ValueError):
            pass
        return ""

    def _build_analysis_prompt(self, video, transcription, video_data, metrics) -> str:
        """Monta o prompt de desconstrucao com os 4 pilares genericos, adaptado ao nicho."""

        return f"""
Voce e o maior especialista do mundo em desconstruir videos curtos virais.
O nicho sendo analisado e: **{self.niche}**

Seu trabalho e dissecar CIRURGICAMENTE como cada video engaja a audiencia e a move para a acao desejada.

Analise o video abaixo extraindo ESTRITAMENTE os 4 pilares de um video viral eficaz:
  1. GANCHO — como o video captura atencao nos primeiros segundos
  2. CREDIBILIDADE — como o criador prova que sabe do que fala
  3. CONTEUDO CENTRAL — como entrega valor, demonstra expertise ou apresenta a solucao
  4. CTA — como direciona o espectador para a proxima acao

Contexto do nicho "{self.niche}": adapte sua analise para esse mercado especifico.
Identifique dores, desejos e linguagem proprios desse nicho.

Retorne APENAS um JSON valido (sem markdown code blocks, sem ```).

## DADOS DO VIDEO

**Plataforma:** {video['platform']}
**Autor:** {video['author']} ({metrics['author_followers']:,} seguidores)
**Descricao:** {video.get('description', 'N/A')}
**Hashtags:** {', '.join(video.get('hashtags', []))}
**Musica/Som:** {video.get('music', 'N/A')}

## METRICAS
- Views: {metrics['views']:,}
- Likes: {metrics['likes']:,}
- Comentarios: {metrics['comments']:,}
- Shares: {metrics['shares']:,}
- Taxa de Engajamento: {metrics['engagement_rate']}%

## TRANSCRICAO COMPLETA
"{transcription['text']}"

## HOOK VERBAL (primeiros 3s)
"{transcription.get('hook_text', 'N/A')}"

## DADOS DE EDICAO
- Duracao: {video_data.get('duration_seconds', 0)}s
- Total de cortes: {video_data.get('total_cuts', 0)}
- Cortes por minuto: {video_data.get('cuts_per_minute', 0)}
- Duracao media por segmento: {video_data.get('avg_segment_duration', 0)}s
- Ritmo de edicao: {video_data.get('editing_pace', 'N/A')}
- Palavras por minuto: {transcription.get('words_per_minute', 0)}

## SEGMENTOS COM TIMESTAMPS
{json.dumps(transcription.get('segments', [])[:20], ensure_ascii=False, indent=2)}

Se imagens foram fornecidas acima, analise-as como frames-chave do video (o primeiro e o hook visual).

Retorne APENAS este JSON (sem markdown, sem ```):
{{
    "gancho": {{
        "score": 8,
        "tipo_gancho": "pergunta | estatistica | dor | historia | controversia | comando | cenario | dado_alarmante | provocacao",
        "texto_verbal": "transcricao EXATA dos primeiros segundos (gancho falado)",
        "texto_visual": "o que aparece na tela durante o gancho",
        "texto_overlay": "texto sobreposto na tela durante o gancho (se houver)",
        "gatilho_emocional": "qual emocao e ativada (medo, curiosidade, desejo, frustacao, inveja, urgencia, etc)",
        "persona_alvo": "perfil EXATO do publico-alvo deste video no nicho {self.niche}",
        "por_que_funciona": "explicacao psicologica de por que esse gancho captura atencao"
    }},
    "credibilidade": {{
        "score": 7,
        "tipo_prova": "case | demonstracao | numeros | bastidores | depoimento | certificacao | experiencia | antes_depois | autoridade_social",
        "como_se_posiciona": "como o criador se apresenta como autoridade no nicho {self.niche}",
        "credenciais_mencionadas": "certificacoes, experiencia, resultados citados",
        "resultados_citados": "numeros concretos mencionados",
        "prova_social": "depoimentos, metricas, logos, prints mostrados",
        "transicao_gancho_para_credibilidade": "como conecta o gancho com a prova de autoridade"
    }},
    "conteudo_central": {{
        "score": 8,
        "tipo_conteudo": "tipo do conteudo principal (tutorial, demonstracao, historia, comparacao, revelacao, etc)",
        "como_apresenta": "metodo de apresentacao (screencast, fala direta, animacao, antes_depois, analogia, etc)",
        "elementos_mencionados": ["lista de elementos, ferramentas, conceitos mencionados"],
        "nivel_complexidade": "leigo | intermediario | avancado",
        "beneficios_destacados": ["lista dos beneficios MAIS enfatizados"],
        "objecoes_antecipadas": ["objecoes que o video antecipa e responde"],
        "momento_aha": "o ponto exato onde o viewer entende o valor — timestamp + descricao"
    }},
    "cta": {{
        "score": 7,
        "tipo_cta": "link_na_bio | DM | formulario | whatsapp | calendly | comentario | landing_page | seguir | comprar | outro",
        "texto_exato": "o texto EXATO do CTA falado pelo criador",
        "urgencia_aplicada": "escassez | bonus_temporal | prazo | vagas_limitadas | preco_subindo | nenhuma",
        "oferta": "o que oferece como proximo passo",
        "friccao": "alta | media | baixa (quao facil e para o viewer tomar acao)",
        "conexao_com_gancho": "como o CTA conecta de volta ao gancho/dor do inicio"
    }},
    "estrutura_narrativa": {{
        "framework": "identificar o framework usado (AIDA, PAS, storytelling, problema_solucao, antes_depois, outro)",
        "distribuicao_tempo": {{
            "gancho_pct": 20,
            "credibilidade_pct": 15,
            "conteudo_central_pct": 50,
            "cta_pct": 15
        }},
        "transicoes": ["como cada bloco se conecta ao proximo"],
        "tecnicas_retencao": ["loops abertos", "pattern interrupts", "curiosity gaps", "promessas", "etc"]
    }},
    "entonacao_e_performance": {{
        "tom_predominante": "consultivo | urgente | empatico | autoritario | conversacional | humoristico | provocativo",
        "variacoes_por_bloco": {{
            "gancho": "tom usado no gancho",
            "credibilidade": "tom usado na credibilidade",
            "conteudo": "tom usado no conteudo central",
            "cta": "tom usado no CTA"
        }},
        "palavras_por_minuto": 180,
        "palavras_poder": ["lista de palavras-chave de impacto usadas"],
        "jargoes_nicho": ["termos tecnicos ou do nicho {self.niche} usados"]
    }},
    "producao_e_visual": {{
        "cenario": "descricao do cenario/ambiente",
        "enquadramento": "close | meio | aberto | variado",
        "usa_screencast": true,
        "elementos_graficos": "descricao dos elementos visuais usados",
        "qualidade_producao": "baixa | media | alta | profissional",
        "branding_visivel": "elementos de marca visiveis"
    }},
    "pontos_fortes": [
        "3-5 pontos fortes do video no contexto do nicho {self.niche}"
    ],
    "pontos_fracos": [
        "2-3 pontos que poderiam melhorar"
    ],
    "por_que_converte": "explicacao concisa de por que este video e eficaz para o nicho {self.niche}",
    "licoes_para_replicar": [
        "3-5 taticas ESPECIFICAS que podem ser replicadas no nicho {self.niche}"
    ]
}}"""

    # -----------------------------------------
    # RELATORIO CONSOLIDADO
    # -----------------------------------------

    def generate_report(self, videos: list[dict]) -> str:
        """Gera relatorio consolidado comparando todos os videos."""
        print("\n" + "=" * 60)
        print("GERANDO RELATORIO CONSOLIDADO")
        print("=" * 60)

        summaries = []
        for v in videos:
            if not v.get("content_analysis"):
                continue
            ca = v["content_analysis"]
            gancho = ca.get("gancho", {})
            cred = ca.get("credibilidade", {})
            conteudo = ca.get("conteudo_central", {})
            cta = ca.get("cta", {})
            summaries.append({
                "autor": v["author"],
                "plataforma": v["platform"],
                "views": v["views"],
                "engagement": v["engagement_rate"],
                "gancho_score": gancho.get("score", "?"),
                "tipo_gancho": gancho.get("tipo_gancho", "?"),
                "gatilho_emocional": gancho.get("gatilho_emocional", "?"),
                "credibilidade_score": cred.get("score", "?"),
                "tipo_prova": cred.get("tipo_prova", "?"),
                "resultados_citados": cred.get("resultados_citados", "?"),
                "conteudo_score": conteudo.get("score", "?"),
                "tipo_conteudo": conteudo.get("tipo_conteudo", "?"),
                "como_apresenta": conteudo.get("como_apresenta", "?"),
                "elementos": conteudo.get("elementos_mencionados", []),
                "cta_score": cta.get("score", "?"),
                "tipo_cta": cta.get("tipo_cta", "?"),
                "oferta": cta.get("oferta", "?"),
                "framework": ca.get("estrutura_narrativa", {}).get("framework", "?"),
                "pontos_fortes": ca.get("pontos_fortes", []),
                "pontos_fracos": ca.get("pontos_fracos", []),
                "licoes": ca.get("licoes_para_replicar", []),
            })

        if not summaries:
            print("  Aviso: Nenhum video com analise completa. Pulando relatorio.")
            return "Nenhum video analisado com sucesso para gerar relatorio."

        summaries_json = json.dumps(summaries, ensure_ascii=False, indent=2)
        if len(summaries_json) > 30000:
            summaries = summaries[:10]
            summaries_json = json.dumps(summaries, ensure_ascii=False, indent=2)
            print(f"  Aviso: Dados muito grandes, limitando a {len(summaries)} videos")

        prompt = f"""
Com base na desconstrucao de {len(summaries)} videos virais no nicho "{self.niche}",
gere um RELATORIO ESTRATEGICO completo em Markdown focado em como replicar essas tecnicas.

## DADOS DOS VIDEOS DESCONSTRUIDOS:
{summaries_json}

Gere o relatorio com estas secoes:

# RELATORIO DE DESCONSTRUCAO — Videos Virais: {self.niche}

## 1. RESUMO EXECUTIVO
Visao geral dos padroes encontrados e potencial de replicacao no nicho {self.niche}.

## 2. GANCHOS QUE CONVERTEM
Quais ganchos sao mais eficazes, quais gatilhos emocionais geram mais engajamento,
exemplos concretos dos melhores ganchos encontrados.

## 3. ESTRATEGIAS DE CREDIBILIDADE
Como os melhores criadores provam autoridade no nicho {self.niche},
tipos de prova social mais usados, resultados e numeros mais citados.

## 4. COMO OS TOP PERFORMERS ENTREGAM CONTEUDO
Formatos de conteudo mais usados, nivel de complexidade,
como simplificam conceitos, padroes de apresentacao.

## 5. CTAs QUE GERAM ACAO
Tipos de CTA mais eficazes, ofertas que funcionam,
nivel de friccao, como conectam o CTA de volta ao gancho.

## 6. FRAMEWORKS NARRATIVOS VENCEDORES
Distribuicao de tempo por bloco, transicoes mais eficazes, tecnicas de retencao.

## 7. PADROES DE PRODUCAO E VISUAL
Cenarios, elementos visuais, qualidade vs. autenticidade.

## 8. PLANO DE ACAO: FRAMEWORK PARA O NICHO {self.niche.upper()}
Playbook pratico e acionavel com o passo a passo para criar videos que convertem,
baseado EXCLUSIVAMENTE nos padroes reais encontrados nos videos analisados.

Seja direto, pratico e acionavel. Use dados concretos dos videos analisados.
Tudo deve servir como blueprint para alguem que cria conteudo no nicho {self.niche}.
"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": GEMINI["temperature_analysis"],
                    "max_output_tokens": GEMINI["max_tokens"],
                },
            )
            report = self._extract_response_text(response)
            if not report:
                print("  Aviso: Gemini nao retornou texto (possivel bloqueio de seguranca)")
                report = f"# Relatorio nao gerado\n\nO Gemini bloqueou a resposta. Dados brutos:\n\n```json\n{summaries_json}\n```"
        except Exception as e:
            print(f"  ERRO ao gerar relatorio: {e}")
            report = f"# Erro ao gerar relatorio\n\nErro: {e}\n\nDados brutos:\n\n```json\n{summaries_json}\n```"

        report_path = OUTPUT_DIR / "relatorio_viral.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"  Relatorio salvo em: {report_path}")
        return report

    def save_analyses(self, videos: list[dict], filename: str = "content_analyses.json"):
        """Salva todas as analises de conteudo."""
        analyses = {}
        for v in videos:
            if v.get("content_analysis"):
                analyses[v["id"]] = {
                    "platform": v["platform"],
                    "author": v["author"],
                    "views": v["views"],
                    "engagement_rate": v["engagement_rate"],
                    "content_analysis": v["content_analysis"],
                }

        filepath = OUTPUT_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(analyses, f, ensure_ascii=False, indent=2)
        print(f"  Analises salvas em: {filepath}")
        return filepath
