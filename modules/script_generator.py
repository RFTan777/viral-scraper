"""
=============================================================
MODULO 6: GERADOR DE ROTEIROS — NICHO DINAMICO
=============================================================
Cria campanhas e scripts de video adaptaveis a qualquer nicho.
Gera roteiros ultra-detalhados com base nos padroes extraidos
dos videos analisados.
"""

import json
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI, OUTPUT_DIR
from modules.retry import gemini_retry


class ScriptGenerator:
    """Gera roteiros de venda/conteudo para qualquer nicho."""

    def __init__(self, niche: str = ""):
        self.niche = niche or "conteudo viral"
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=GEMINI["model"],
            generation_config={
                "max_output_tokens": GEMINI["max_tokens"],
                "temperature": GEMINI["temperature"],
            },
            system_instruction=self._build_system_prompt(),
        )

    def _build_system_prompt(self) -> str:
        """Constroi system prompt dinamico baseado no nicho."""
        return f"""Voce e um estrategista de campanhas de video especializado no nicho: {self.niche}.

Voce ja produziu +500 roteiros de alta conversao para criadores de conteudo e empresas nesse nicho.

======================================================
PUBLICO-ALVO: Definido pelo nicho "{self.niche}"
======================================================
- Identifique o perfil exato do publico-alvo deste nicho
- Entenda suas dores, desejos, frustrações e linguagem
- Adapte o tom, exemplos e referencias ao universo desse nicho
- Use a linguagem que esse publico usa no dia a dia

======================================================
FRAMEWORK: GANCHO -> CREDIBILIDADE -> CONTEUDO -> CTA
======================================================

1. GANCHO (0-20%) — Capturar atencao nos primeiros 2-3 segundos.
   Deve ser IMPOSSIVEL de ignorar. Usar gatilhos emocionais fortes.
   Tipos eficazes: pergunta provocativa, estatistica chocante, dor identificavel,
   historia intrigante, controversia, comando direto.

2. CREDIBILIDADE (20-35%) — Provar autoridade RAPIDO.
   Mostrar resultados, experiencia, casos de sucesso. Nao e curriculo, e PROVA.

3. CONTEUDO CENTRAL (35-75%) — Entregar valor real.
   O espectador precisa sair com algo util, uma transformacao ou uma demonstracao
   que o faca DESEJAR o proximo passo.

4. CTA (75-100%) — Direcionar para a acao desejada.
   Claro, direto, com urgencia quando apropriado. Conectar de volta ao gancho.

======================================================
REGRAS
======================================================
- TOM adaptado ao nicho {self.niche}: profissional mas acessivel
- GANCHOS sempre fortes e impossivel de ignorar
- B-ROLLS detalhados e especificos em TODA cena
- LINGUAGEM do nicho — usar termos e referencias que o publico conhece
- CADA SEGUNDO tem proposito. Zero enrolacao.
- JSON valido sempre. Sem markdown code blocks, sem ```.
"""

    def generate_scripts(
        self,
        videos: list[dict],
        topic: str,
        niche: str = "",
        style: str = "educativo",
        num_scripts: int = 3,
        duration_seconds: int = 60,
    ) -> list[dict]:
        """Gera multiplos roteiros ultra-detalhados."""
        # Atualizar nicho se fornecido
        if niche:
            self.niche = niche

        print("\n" + "=" * 60)
        print(f"GERANDO ROTEIROS — Nicho: {self.niche}")
        print("=" * 60)
        print(f"  Tema: {topic}")
        print(f"  Nicho: {self.niche}")
        print(f"  Estilo: {style}")
        print(f"  Duracao alvo: {duration_seconds}s")
        print(f"  Quantidade: {num_scripts}")

        patterns = self._extract_patterns(videos)

        print(f"\n  Gerando brief estrategico...")
        brief = self._generate_strategic_brief(patterns, topic, style)
        print(f"    OK: Brief pronto!")

        scripts = []
        approaches = self._define_approaches(style, num_scripts)

        for i, approach in enumerate(approaches, 1):
            print(f"\n  [{i}/{num_scripts}] Gerando roteiro: {approach['nome']}...")
            script = self._generate_elite_script(
                brief=brief, patterns=patterns, topic=topic,
                approach=approach, duration=duration_seconds,
            )
            scripts.append(script)
            print(f"    OK: Roteiro #{i} gerado!")

        self._save_scripts(scripts, topic)
        self._save_scripts_markdown(scripts, topic)
        return scripts

    # -----------------------------------------
    # EXTRACAO DE PADROES
    # -----------------------------------------

    def _extract_patterns(self, videos: list[dict]) -> dict:
        """Extrai padroes detalhados dos videos desconstruidos."""
        patterns = {
            "ganchos": [], "credibilidade": [], "conteudo": [], "ctas": [],
            "estruturas": [], "tons": [], "tecnicas_retencao": [], "palavras_poder": [],
            "elementos": [],
            "metricas": {"avg_views": 0, "avg_engagement": 0, "avg_duration": 0, "avg_wpm": 0},
            "top_videos": [],
        }

        analyzed = [v for v in videos if v.get("content_analysis")]
        if not analyzed:
            return patterns

        analyzed_sorted = sorted(analyzed, key=lambda v: v.get("engagement_rate", 0), reverse=True)

        for v in analyzed_sorted:
            ca = v["content_analysis"]

            gancho = ca.get("gancho", {})
            if gancho:
                patterns["ganchos"].append({
                    "tipo": gancho.get("tipo_gancho"),
                    "gatilho": gancho.get("gatilho_emocional"),
                    "texto_verbal": gancho.get("texto_verbal"),
                    "persona": gancho.get("persona_alvo"),
                    "score": gancho.get("score"),
                    "views": v["views"],
                    "engagement": v["engagement_rate"],
                })

            cred = ca.get("credibilidade", {})
            if cred:
                patterns["credibilidade"].append({
                    "tipo_prova": cred.get("tipo_prova"),
                    "resultados": cred.get("resultados_citados"),
                    "como_se_posiciona": cred.get("como_se_posiciona"),
                    "score": cred.get("score"),
                })

            conteudo = ca.get("conteudo_central", {})
            if conteudo:
                patterns["conteudo"].append({
                    "tipo": conteudo.get("tipo_conteudo"),
                    "como_apresenta": conteudo.get("como_apresenta"),
                    "beneficios": conteudo.get("beneficios_destacados", []),
                    "momento_aha": conteudo.get("momento_aha"),
                    "score": conteudo.get("score"),
                })
                patterns["elementos"].extend(conteudo.get("elementos_mencionados", []))

            cta = ca.get("cta", {})
            if cta:
                patterns["ctas"].append({
                    "tipo": cta.get("tipo_cta"),
                    "texto": cta.get("texto_exato"),
                    "oferta": cta.get("oferta"),
                    "urgencia": cta.get("urgencia_aplicada"),
                    "score": cta.get("score"),
                })

            estrutura = ca.get("estrutura_narrativa", {})
            if estrutura:
                patterns["estruturas"].append({
                    "framework": estrutura.get("framework"),
                    "distribuicao": estrutura.get("distribuicao_tempo", {}),
                    "tecnicas": estrutura.get("tecnicas_retencao", []),
                })
                patterns["tecnicas_retencao"].extend(estrutura.get("tecnicas_retencao", []))

            ent = ca.get("entonacao_e_performance", {})
            if ent:
                patterns["tons"].append({
                    "tom": ent.get("tom_predominante"),
                    "variacoes": ent.get("variacoes_por_bloco", {}),
                    "wpm": ent.get("palavras_por_minuto"),
                })
                patterns["palavras_poder"].extend(ent.get("palavras_poder", []))

        for v in analyzed_sorted[:3]:
            ca = v.get("content_analysis", {})
            patterns["top_videos"].append({
                "autor": v["author"], "views": v["views"],
                "engagement": v["engagement_rate"],
                "tipo_gancho": ca.get("gancho", {}).get("tipo_gancho", ""),
                "tipo_conteudo": ca.get("conteudo_central", {}).get("tipo_conteudo", ""),
                "tipo_cta": ca.get("cta", {}).get("tipo_cta", ""),
                "pontos_fortes": ca.get("pontos_fortes", []),
            })

        patterns["metricas"]["avg_views"] = int(sum(v["views"] for v in analyzed) / len(analyzed))
        patterns["metricas"]["avg_engagement"] = round(sum(v["engagement_rate"] for v in analyzed) / len(analyzed), 2)
        durations = [v.get("video_analysis", {}).get("duration_seconds", 0) for v in analyzed if v.get("video_analysis")]
        patterns["metricas"]["avg_duration"] = round(sum(durations) / len(durations), 1) if durations else 0
        wpms = [v.get("transcription", {}).get("words_per_minute", 0) for v in analyzed if v.get("transcription")]
        patterns["metricas"]["avg_wpm"] = round(sum(wpms) / len(wpms)) if wpms else 150
        patterns["palavras_poder"] = list(set(filter(None, patterns["palavras_poder"])))
        patterns["tecnicas_retencao"] = list(set(filter(None, patterns["tecnicas_retencao"])))
        patterns["elementos"] = list(set(filter(None, patterns["elementos"])))

        return patterns

    # -----------------------------------------
    # BRIEF ESTRATEGICO
    # -----------------------------------------

    @gemini_retry
    def _generate_strategic_brief(self, patterns, topic, style) -> str:
        prompt = f"""
Analise os padroes abaixo (extraidos de videos REAIS virais no nicho "{self.niche}")
e crie um BRIEF ESTRATEGICO DE CAMPANHA.

## TOP VIDEOS ANALISADOS:
{json.dumps(patterns['top_videos'], ensure_ascii=False, indent=2)}

## GANCHOS QUE FUNCIONARAM:
{json.dumps(patterns['ganchos'][:5], ensure_ascii=False, indent=2)}

## PROVAS DE CREDIBILIDADE MAIS EFICAZES:
{json.dumps(patterns['credibilidade'][:5], ensure_ascii=False, indent=2)}

## COMO ENTREGAM CONTEUDO:
{json.dumps(patterns['conteudo'][:5], ensure_ascii=False, indent=2)}

## CTAs QUE GERAM ACAO:
{json.dumps(patterns['ctas'][:5], ensure_ascii=False, indent=2)}

## FRAMEWORKS:
{json.dumps(patterns['estruturas'][:5], ensure_ascii=False, indent=2)}

## TONS QUE CONVERTEM:
{json.dumps(patterns['tons'][:5], ensure_ascii=False, indent=2)}

## ELEMENTOS/REFERENCIAS:
{json.dumps(patterns['elementos'][:15], ensure_ascii=False)}

## PALAVRAS DE PODER:
{json.dumps(patterns['palavras_poder'][:20], ensure_ascii=False)}

## METRICAS:
{json.dumps(patterns['metricas'], ensure_ascii=False)}

BRIEFING: Tema={topic} | Nicho={self.niche} | Estilo={style}

Crie um brief de CAMPANHA adaptado ao nicho "{self.niche}" com:
1) DIAGNOSTICO DE DORES: quais dores/desejos mais resonam com o publico deste nicho
2) ARSENAL DE GANCHOS: 5 ganchos fortes prontos para usar, atacando dores/desejos reais
3) PLAYBOOK DE CREDIBILIDADE: como provar autoridade rapidamente neste nicho
4) ROTEIRO DE CONTEUDO: como entregar valor e demonstrar expertise
5) DIRECAO VOCAL: tom ideal para o nicho, ritmo, linguagem
6) DIRECAO VISUAL (B-ROLLS): lista especifica de B-rolls para cada bloco
7) CTA: como direcionar para a acao desejada

Seja ESPECIFICO para o nicho "{self.niche}". Nada generico. Dados concretos.
"""
        response = self.model.generate_content(prompt)
        return self._extract_text(response)

    @staticmethod
    def _extract_text(response) -> str:
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

    # -----------------------------------------
    # ABORDAGENS
    # -----------------------------------------

    def _define_approaches(self, style, num_scripts):
        all_approaches = [
            {"nome": "Dor Direta",
             "descricao": f"Abre com a DOR principal do publico do nicho {self.niche}. Gatilho emocional forte logo nos primeiros segundos.",
             "hook_style": "dado chocante ou cenario de dor identificavel",
             "emotional_arc": "choque/identificacao -> medo -> solucao -> urgencia"},
            {"nome": "Prova Social",
             "descricao": f"Abre com RESULTADO concreto no nicho {self.niche}. Numeros reais, caso de sucesso, antes/depois.",
             "hook_style": "resultado numerico impactante",
             "emotional_arc": "curiosidade -> prova -> como funciona -> quero o mesmo resultado"},
            {"nome": "Controversia Estrategica",
             "descricao": f"Abre com uma OPINIAO FORTE ou verdade incomoda sobre o nicho {self.niche}. Desafia o senso comum.",
             "hook_style": "afirmacao controversa que gera debate",
             "emotional_arc": "surpresa/discordancia -> argumentacao -> revelacao -> acao"},
            {"nome": "Historia Pessoal",
             "descricao": f"Abre com uma HISTORIA real e envolvente relacionada ao nicho {self.niche}. Storytelling que conecta.",
             "hook_style": "inicio de historia intrigante (ex: 'Ha 2 anos eu estava...')",
             "emotional_arc": "curiosidade -> identificacao -> transformacao -> inspiracao + acao"},
            {"nome": "Tutorial Pratico",
             "descricao": f"Abre com PROMESSA DE VALOR imediato no nicho {self.niche}. Entrega algo acionavel rapido.",
             "hook_style": "promessa especifica (ex: 'Em 60 segundos voce vai aprender...')",
             "emotional_arc": "curiosidade -> aprendizado -> momento aha -> quero mais"},
        ]
        return all_approaches[:num_scripts]

    # -----------------------------------------
    # GERACAO ELITE
    # -----------------------------------------

    @gemini_retry
    def _generate_elite_script(self, brief, patterns, topic, approach, duration) -> dict:
        estimated_words = int(duration * (patterns["metricas"].get("avg_wpm", 150) / 60))

        prompt = f"""
## BRIEF ESTRATEGICO DA CAMPANHA:
{brief}

## ABORDAGEM: {approach['nome']} — {approach['descricao']}
Gancho: {approach['hook_style']} | Arco: {approach['emotional_arc']}

## PARAMETROS:
Tema: {topic} | Nicho: {self.niche} | Duracao: {duration}s | ~{estimated_words} palavras

## TOP VIDEOS ANALISADOS:
{json.dumps(patterns['top_videos'], ensure_ascii=False, indent=2)}

## ELEMENTOS/REFERENCIAS:
{json.dumps(patterns['elementos'][:10], ensure_ascii=False)}

## PALAVRAS DE PODER:
{json.dumps(patterns['palavras_poder'][:15], ensure_ascii=False)}

---

INSTRUCAO: Gere um roteiro detalhado para o nicho "{self.niche}", tema "{topic}".

REQUISITOS OBRIGATORIOS:
1. GANCHO nos primeiros 2-3 segundos — capturar atencao do publico do nicho {self.niche}.
2. TOM adaptado ao nicho o video INTEIRO. Sem rodeios. Sem filler.
3. B-ROLLS em CADA cena — visuais relevantes ao nicho {self.niche}.
4. CONTEUDO que entrega VALOR REAL ao publico deste nicho.
5. CTA final direcionando para a acao desejada.

Retorne APENAS JSON valido (sem markdown code blocks, sem ```):

{{
    "titulo": "titulo impactante para o nicho {self.niche}",
    "abordagem": "{approach['nome']}",
    "duracao_alvo": {duration},
    "palavras_totais": {estimated_words},
    "conceito": {{
        "dor_ou_desejo_central": "a dor/desejo principal do publico que sera explorada",
        "proposta_de_valor": "o que o espectador ganha assistindo este video",
        "promessa": "resultado CONCRETO prometido",
        "persona_alvo": "perfil EXATO do publico-alvo no nicho {self.niche}"
    }},
    "gancho": {{
        "tipo": "{approach['hook_style']}",
        "texto_fala": "frase EXATA dos primeiros 2-3 segundos",
        "intensidade": "1-10",
        "como_falar": {{
            "volume": "alto | medio-alto | medio",
            "velocidade": "rapida | normal com pausas | pausada",
            "tom": "o tom ideal para este gancho",
            "enfase": "palavras para enfatizar",
            "pausa_dramatica": "onde pausar para impacto"
        }},
        "texto_tela": {{
            "texto": "texto sobreposto na tela",
            "posicao": "centro | topo | inferior",
            "animacao": "tipo de animacao",
            "timing": "segundo X a Y"
        }},
        "broll": {{
            "descricao": "descricao EXATA do B-roll do gancho",
            "tipo": "tipo do visual",
            "duracao": "X segundos",
            "transicao": "tipo de transicao"
        }},
        "visual_apresentador": {{
            "enquadramento": "close | meio | aberto",
            "expressao_facial": "descricao EXATA",
            "gesto": "o que fazer com maos/corpo"
        }},
        "por_que_funciona": "explicacao psicologica"
    }},
    "cenas": [
        {{
            "numero": 1,
            "momento": "00:00 - 00:03",
            "bloco": "GANCHO | CREDIBILIDADE | CONTEUDO | CTA",
            "funcao": "o que esta cena faz no video",
            "fala": {{
                "texto": "texto EXATO a ser falado",
                "entonacao": {{
                    "tom": "tom desta cena",
                    "volume": "1-10",
                    "velocidade": "descricao",
                    "pausas": "onde e quanto pausar",
                    "enfase": ["palavras + COMO enfatizar"],
                    "emocao_na_voz": "emocao predominante"
                }}
            }},
            "brolls": [
                {{
                    "descricao": "descricao EXATA do B-roll",
                    "tipo": "tipo do visual",
                    "duracao": "X segundos",
                    "momento_exato": "em qual segundo",
                    "transicao_entrada": "tipo de transicao",
                    "texto_overlay": "texto sobreposto (se houver)"
                }}
            ],
            "visual_apresentador": {{
                "enquadramento": "close | meio | aberto",
                "angulo_camera": "frontal | 45 graus | etc",
                "movimento": "estatico | zoom in | pan",
                "acao": "EXATAMENTE o que fazer",
                "cenario": "fundo visivel"
            }},
            "texto_tela": {{
                "texto": "overlay de texto",
                "estilo": "estilo visual",
                "animacao": "tipo de animacao"
            }},
            "edicao": {{
                "tipo_corte": "tipo de corte/transicao",
                "efeito": "efeito visual",
                "sfx": "efeito sonoro",
                "musica": "momento e intensidade da musica"
            }},
            "storytelling": {{
                "tecnica_retencao": "tecnica ativa nesta cena",
                "estado_mental_viewer": "o que o espectador esta PENSANDO",
                "nivel_engajamento": "1-10"
            }}
        }}
    ],
    "mapa_do_video": {{
        "00-20%_GANCHO": {{
            "objetivo": "capturar atencao",
            "emocao_alvo": "emocao desejada",
            "estrategia": "como fazer"
        }},
        "20-35%_CREDIBILIDADE": {{
            "objetivo": "provar autoridade",
            "emocao_alvo": "emocao desejada",
            "estrategia": "como fazer"
        }},
        "35-75%_CONTEUDO": {{
            "objetivo": "entregar valor",
            "emocao_alvo": "emocao desejada",
            "estrategia": "como fazer"
        }},
        "75-100%_CTA": {{
            "objetivo": "converter em acao",
            "emocao_alvo": "emocao desejada",
            "estrategia": "como fazer"
        }}
    }},
    "arsenal_brolls": {{
        "gancho_visuais": ["descricao de cada B-roll de gancho"],
        "credibilidade_visuais": ["descricao de cada visual de prova"],
        "conteudo_visuais": ["descricao de cada visual de conteudo"],
        "cta_visuais": ["descricao de cada visual de CTA"]
    }},
    "tecnicas_retencao_aplicadas": [
        {{"tecnica": "...", "onde_aplicada": "cena X", "como_funciona": "..."}}
    ],
    "cta_final": {{
        "tipo": "tipo do CTA",
        "texto_fala": "texto EXATO do CTA",
        "como_falar": "direcao vocal do CTA",
        "oferta": "o que oferece como proximo passo",
        "urgencia": "elemento de urgencia (se aplicavel)",
        "conexao_com_gancho": "como conecta de volta ao inicio",
        "broll_cta": "visual do CTA"
    }},
    "producao": {{
        "cenario_ideal": "descricao detalhada do cenario",
        "iluminacao": "tipo de iluminacao",
        "audio": {{
            "musica_sugerida": "genero e mood",
            "volume_musica": "porcentagem em relacao a voz",
            "sfx_chave": ["lista de efeitos sonoros"]
        }},
        "figurino": "descricao do figurino ideal",
        "formato": "9:16 vertical"
    }},
    "distribuicao": {{
        "titulo_tiktok": "descricao TikTok com gancho",
        "titulo_instagram": "descricao Instagram",
        "hashtags": {{
            "alcance": ["3-5 hashtags de alcance"],
            "nicho": ["3-5 hashtags do nicho {self.niche}"],
            "long_tail": ["2-3 especificas"]
        }},
        "horario_postagem": "melhor horario para o publico do nicho",
        "dia_semana": "melhor dia"
    }}
}}

REGRAS:
- GANCHO forte e impossivel de ignorar. O espectador TEM que parar de scrollar.
- TOM adaptado ao nicho {self.niche} o video inteiro.
- B-ROLLS em TODA cena. Descricoes EXATAS e relevantes ao nicho.
- Minimo 6-10 cenas seguindo GANCHO -> CREDIBILIDADE -> CONTEUDO -> CTA.
- Especifico ao tema: "{topic}"
"""

        response = self.model.generate_content(
            prompt,
            generation_config={
                "temperature": GEMINI["temperature"],
                "max_output_tokens": GEMINI["max_tokens"],
            },
        )

        response_text = self._extract_text(response)

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
                script = json.loads(clean[json_start:json_end])
            else:
                script = {"raw_script": response_text}
        except json.JSONDecodeError:
            script = {"raw_script": response_text}

        return script

    # -----------------------------------------
    # SALVAR
    # -----------------------------------------

    def _save_scripts(self, scripts, topic):
        json_path = OUTPUT_DIR / "roteiros.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(scripts, f, ensure_ascii=False, indent=2)
        print(f"\n  JSON: {json_path}")

    def _save_scripts_markdown(self, scripts, topic):
        md_path = OUTPUT_DIR / "roteiros.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# CAMPANHA: {topic}\n")
            f.write(f"*Nicho: {self.niche}*\n\n---\n\n")

            for i, script in enumerate(scripts, 1):
                title = script.get("titulo", f"Roteiro #{i}")
                f.write(f"# ROTEIRO #{i}: {title}\n")
                f.write(f"**Abordagem:** {script.get('abordagem', '')} | **Duracao:** ~{script.get('duracao_alvo', '?')}s\n\n")

                conceito = script.get("conceito", {})
                if conceito:
                    f.write("## CONCEITO\n\n")
                    for key, val in conceito.items():
                        if val:
                            f.write(f"**{key.replace('_',' ').title()}:** {val}\n\n")

                gancho = script.get("gancho", {})
                if gancho:
                    f.write("## GANCHO\n\n")
                    f.write(f"**Falar:** \"{gancho.get('texto_fala', '')}\"\n\n")
                    if gancho.get("intensidade"):
                        f.write(f"**Intensidade:** {gancho['intensidade']}/10\n\n")
                    como = gancho.get("como_falar", {})
                    if como:
                        f.write(f"**Tom:** {como.get('tom', '')} | **Volume:** {como.get('volume', '')} | **Velocidade:** {como.get('velocidade', '')}\n\n")
                    broll_gancho = gancho.get("broll", {})
                    if broll_gancho:
                        f.write(f"**B-Roll:** {broll_gancho.get('descricao', '')}\n\n")
                    if gancho.get("por_que_funciona"):
                        f.write(f"**Por que funciona:** {gancho['por_que_funciona']}\n\n")

                cenas = script.get("cenas", [])
                if cenas:
                    f.write("## ROTEIRO CENA A CENA\n\n")
                    for cena in cenas:
                        bloco = cena.get("bloco", "")
                        f.write(f"### [{cena.get('momento', '?')}] {bloco}\n")
                        if cena.get("funcao"):
                            f.write(f"*{cena['funcao']}*\n\n")
                        fala = cena.get("fala", {})
                        if isinstance(fala, dict):
                            f.write(f"**Falar:** \"{fala.get('texto', '')}\"\n\n")
                            ent = fala.get("entonacao", {})
                            if ent:
                                f.write(f"Tom: {ent.get('tom', '')} | Vol: {ent.get('volume', '')}/10 | {ent.get('velocidade', '')}\n\n")
                        brolls = cena.get("brolls", [])
                        if brolls:
                            f.write("**B-Rolls:**\n\n")
                            for br in brolls:
                                if isinstance(br, dict):
                                    f.write(f"- **[{br.get('momento_exato', '?')}]** {br.get('descricao', '')}\n")
                            f.write("\n")
                        story = cena.get("storytelling", {})
                        if story and story.get("tecnica_retencao"):
                            f.write(f"Retencao: {story['tecnica_retencao']}\n\n")
                        f.write("---\n\n")

                arsenal = script.get("arsenal_brolls", {})
                if arsenal:
                    f.write("## ARSENAL DE B-ROLLS\n\n")
                    for key, items in arsenal.items():
                        if isinstance(items, list) and items:
                            f.write(f"**{key.replace('_',' ').title()}:**\n\n")
                            for item in items:
                                f.write(f"- {item}\n")
                            f.write("\n")

                mapa = script.get("mapa_do_video", {})
                if mapa:
                    f.write("## MAPA DO VIDEO\n\n")
                    for faixa, info in mapa.items():
                        if isinstance(info, dict):
                            f.write(f"**{faixa}**\n\n")
                            for k, val in info.items():
                                f.write(f"- {k.replace('_',' ').title()}: {val}\n")
                            f.write("\n")

                cta = script.get("cta_final", {})
                if cta:
                    f.write("## CTA FINAL\n\n")
                    f.write(f"**Falar:** \"{cta.get('texto_fala', '')}\"\n\n")
                    if cta.get("oferta"):
                        f.write(f"**Oferta:** {cta['oferta']}\n\n")
                    if cta.get("urgencia"):
                        f.write(f"**Urgencia:** {cta['urgencia']}\n\n")

                prod = script.get("producao", {})
                if prod:
                    f.write("## PRODUCAO\n\n")
                    f.write(f"**Cenario:** {prod.get('cenario_ideal', '')}\n\n")
                    f.write(f"**Figurino:** {prod.get('figurino', '')}\n\n")

                dist = script.get("distribuicao", {})
                if dist:
                    f.write("## DISTRIBUICAO\n\n")
                    if dist.get("titulo_tiktok"):
                        f.write(f"**TikTok:** {dist['titulo_tiktok']}\n\n")
                    if dist.get("titulo_instagram"):
                        f.write(f"**Instagram:** {dist['titulo_instagram']}\n\n")
                    hashtags = dist.get("hashtags", {})
                    if isinstance(hashtags, dict):
                        all_tags = []
                        for tl in hashtags.values():
                            if isinstance(tl, list):
                                all_tags.extend(tl)
                        if all_tags:
                            f.write(f"**Hashtags:** {' '.join(all_tags)}\n\n")

                f.write("\n---\n---\n\n")

        print(f"  Markdown: {md_path}")
