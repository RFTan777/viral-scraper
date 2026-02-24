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

INSTRUCAO: Gere um roteiro CINEMATOGRAFICO PROFISSIONAL para o nicho "{self.niche}", tema "{topic}".

REQUISITOS OBRIGATORIOS:
1. GANCHO nos primeiros 2-3 segundos — capturar atencao do publico do nicho {self.niche}.
2. TOM adaptado ao nicho o video INTEIRO. Sem rodeios. Sem filler.
3. B-ROLLS em CADA cena — visuais relevantes ao nicho {self.niche}.
4. CONTEUDO que entrega VALOR REAL ao publico deste nicho.
5. CTA final direcionando para a acao desejada.
6. ai_video_prompt em CADA cena: prompt cinematografico detalhado em INGLES para ferramentas de IA de video (Kling, Runway, Wan2.1, Pika). Deve incluir: tipo de plano, angulo de camera, descricao fisica do apresentador, expressao facial exata, o que segura nas maos, descricao detalhada do ambiente ao redor, iluminacao, elementos de fundo, movimento de camera, estilo cinematografico, atmosfera.
7. ai_production_prompt global: guia de estilo visual completo para o video inteiro.

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
                    "tom": "tom desta cena: urgente | confidente | empolgado | intimo | autoritario | inspirador",
                    "volume": "1-10",
                    "velocidade": "palavras por minuto e ritmo: ex: 180wpm acelerado, pausas curtas",
                    "pausas": "onde pausar e por quanto tempo: ex: pausa de 0.5s apos palavra X",
                    "enfase": ["PALAVRA em maiusculo = enfase forte", "palavra* = enfase media"],
                    "emocao_na_voz": "emocao predominante: urgencia | empolgacao | empatia | autoridade | misterio",
                    "respiracao": "onde respirar naturalmente, efeito na fala",
                    "variacao_tonal": "como a voz sobe e desce ao longo da fala"
                }}
            }},
            "brolls": [
                {{
                    "descricao": "descricao EXATA do B-roll — o que aparece na tela",
                    "tipo": "screencast | ambiente | produto | grafico | before_after | mao_segurando",
                    "duracao": "X segundos",
                    "momento_exato": "em qual segundo do video",
                    "transicao_entrada": "corte seco | fade | zoom | swipe",
                    "texto_overlay": "texto sobreposto (se houver)",
                    "detalhe_visual": "detalhe especifico: ex: tela do celular mostrando X, mao segurando produto Y"
                }}
            ],
            "visual_apresentador": {{
                "enquadramento": "close extremo (apenas rosto) | close (busto) | meio (cintura) | aberto (corpo inteiro)",
                "angulo_camera": "frontal direto | 15 graus esquerda | 45 graus | levemente abaixo | levemente acima",
                "movimento_camera": "estatica | zoom in lento | pan esquerda | handheld leve | steadicam",
                "acao_corpo": "descricao EXATA do que o apresentador faz com o corpo",
                "maos": "o que as maos fazem: segura celular mostrando tela | aponta para grafico | gesticula | repousa",
                "objeto_em_maos": "se segura algo: descricao exata do objeto e como o mostra para camera",
                "expressao_facial": "expressao EXATA: sobrancelha erguida de surpresa | olhar direto com intensidade | sorriso contido",
                "olhar": "direto para camera | para objeto nas maos | para cima pensativo",
                "postura": "inclinado para frente com urgencia | relaxado | ereto e confiante",
                "cenario": {{
                    "local": "tipo de local: escritorio home office | cafe | estudio | exterior",
                    "fundo": "o que aparece ao fundo: parede clara | estante com livros | janela com luz natural",
                    "elementos_visiveis": ["item 1 ao fundo", "item 2", "detalhe de ambiente"],
                    "atmosfera": "sensacao do ambiente: profissional moderno | aconchegante | minimalista"
                }}
            }},
            "iluminacao": {{
                "tipo": "luz natural de janela | ring light | softbox lateral | luz de tela | ambiente escuro com destaque",
                "direcao": "esquerda | direita | frontal | de cima | contraluz",
                "intensidade": "1-10",
                "temperatura": "quente (3000K) | neutra (4500K) | fria (6500K)",
                "efeito": "o que a iluminacao transmite: autoridade | intimidade | urgencia | calor"
            }},
            "texto_tela": {{
                "texto": "overlay de texto exato",
                "estilo": "bold branco com sombra | destaque amarelo | letra de impacto | caption gerada",
                "posicao": "topo | centro | inferior | lateral",
                "animacao": "aparece com pop | digita | slide da esquerda | fade in",
                "timing": "aparece no segundo X, some no segundo Y"
            }},
            "edicao": {{
                "tipo_corte": "corte seco | L-cut | J-cut | jump cut | match cut | fade",
                "efeito_visual": "sem efeito | zoom brusco | slow motion | speed ramp | freeze frame",
                "sfx": "sem SFX | whoosh | click | notification sound | impacto grave | swipe",
                "musica": {{
                    "genero": "lo-fi | trap instrumental | cinematic | pop energetico | ambiente",
                    "volume": "porcentagem: ex 20% atras da voz",
                    "momento": "entra no segundo X, aumenta no Y, some no Z",
                    "mood": "tensao | empolgacao | esperanca | foco | urgencia"
                }}
            }},
            "storytelling": {{
                "tecnica_retencao": "cliffhanger | loop aberto | pergunta sem resposta | revelacao parcial | contraste",
                "estado_mental_viewer": "o que o espectador esta PENSANDO e SENTINDO neste momento",
                "nivel_engajamento": "1-10",
                "transicao_proxima_cena": "como esta cena puxa para a proxima — por que o viewer continua assistindo"
            }},
            "ai_video_prompt": {{
                "prompt_en": "Ultra-detailed English prompt for AI video generation (Kling/Runway/Wan2.1/Pika). Include ALL of: [SHOT TYPE] specific shot name. [SUBJECT] physical description of presenter (approximate age, ethnicity, clothing color and style, facial expression, body language). [HANDS/OBJECTS] exactly what they hold, how they hold it, what it shows. [ENVIRONMENT] exact room type, specific background elements visible (furniture, decor, objects on walls/desk), depth, textures. [LIGHTING] exact light setup, direction, quality, color temperature. [CAMERA] movement type, lens feel, depth of field. [STYLE] cinematic reference or aesthetic. [MOOD] atmosphere and emotional tone. [FORMAT] 9:16 vertical smartphone format.",
                "negative_prompt_en": "blurry, low quality, watermark, text overlay, distorted face, extra limbs, unrealistic",
                "style_reference": "cinematic documentary | lifestyle vertical | raw TikTok | professional brand | editorial",
                "clip_duration_seconds": 5,
                "aspect_ratio": "9:16"
            }}
        }}
    ],
    "mapa_do_video": {{
        "00-20%_GANCHO": {{
            "objetivo": "capturar atencao e criar curiosidade irresistivel",
            "emocao_alvo": "emocao desejada no espectador",
            "estrategia": "como exatamente executar"
        }},
        "20-35%_CREDIBILIDADE": {{
            "objetivo": "provar autoridade de forma rapida e incontestavel",
            "emocao_alvo": "emocao desejada",
            "estrategia": "como exatamente executar"
        }},
        "35-75%_CONTEUDO": {{
            "objetivo": "entregar valor real e criar desejo pelo proximo passo",
            "emocao_alvo": "emocao desejada",
            "estrategia": "como exatamente executar"
        }},
        "75-100%_CTA": {{
            "objetivo": "converter em acao com urgencia e clareza",
            "emocao_alvo": "emocao desejada",
            "estrategia": "como exatamente executar"
        }}
    }},
    "arsenal_brolls": {{
        "gancho_visuais": ["descricao cinematografica de cada B-roll de gancho"],
        "credibilidade_visuais": ["descricao de cada visual de prova de autoridade"],
        "conteudo_visuais": ["descricao de cada visual de entrega de valor"],
        "cta_visuais": ["descricao de cada visual de chamada para acao"]
    }},
    "tecnicas_retencao_aplicadas": [
        {{"tecnica": "nome da tecnica", "onde_aplicada": "cena X momento Y", "como_funciona": "mecanismo psicologico"}}
    ],
    "cta_final": {{
        "tipo": "tipo do CTA",
        "texto_fala": "texto EXATO do CTA",
        "como_falar": {{
            "tom": "tom do CTA",
            "velocidade": "ritmo da fala",
            "enfase": "palavras de impacto",
            "urgencia_vocal": "como criar urgencia na voz"
        }},
        "oferta": "o que oferece como proximo passo",
        "urgencia": "elemento de urgencia concreto",
        "conexao_com_gancho": "como fecha o loop aberto do gancho",
        "broll_cta": "visual exato do CTA"
    }},
    "producao": {{
        "cenario_ideal": "descricao detalhada do cenario de filmagem — local, disposicao, elementos",
        "iluminacao_setup": "setup completo de iluminacao: posicao de cada luz, tipo, temperatura",
        "audio": {{
            "musica_sugerida": "genero, mood e BPM sugerido",
            "volume_musica": "porcentagem relativa a voz por bloco",
            "sfx_chave": ["SFX com momento exato de uso"]
        }},
        "figurino": "descricao detalhada do figurino — cor, estilo, acessorios, por que transmite autoridade",
        "formato": "9:16 vertical — resolucao minima 1080x1920",
        "equipamento_minimo": "o minimo necessario para gravar com qualidade"
    }},
    "ai_production_prompt": {{
        "style_guide_en": "Complete visual style guide for the entire video: color palette, aesthetic, tone, reference films/creators",
        "color_grade_en": "Color grading description: warm/cool, saturation, contrast, LUT style",
        "camera_style_en": "Camera style throughout: handheld organic feel | static authority | dynamic movement",
        "subject_description_en": "Consistent main subject description for all scenes: physical appearance, clothing, presence",
        "primary_environment_en": "Main filming location: specific room details, decor, layout",
        "prompt_global_en": "COMPLETE unified prompt for generating the full video in one shot with AI tools. This is the master prompt combining all scenes into a cohesive 60-second vertical video narrative. Include all visual details, transitions, pacing, and style.",
        "modelo_recomendado": "Kling 1.6 Pro | Wan2.1 14B | CogVideoX-5b — escolha baseada no estilo",
        "razao_modelo": "por que este modelo e o melhor para este roteiro especifico",
        "parametros_api": {{
            "aspect_ratio": "9:16",
            "duration": "5",
            "cfg_scale": 0.5,
            "negative_prompt": "blurry, low quality, watermark, text overlay, distorted face, amateur, shaky"
        }}
    }},
    "distribuicao": {{
        "titulo_tiktok": "caption TikTok otimizada com gancho nos primeiros 125 caracteres",
        "titulo_instagram": "caption Instagram com storytelling e chamada para salvar",
        "hashtags": {{
            "alcance": ["3-5 hashtags de alcance massivo"],
            "nicho": ["3-5 hashtags especificas do nicho {self.niche}"],
            "long_tail": ["2-3 hashtags de nicho especifico com alta conversao"]
        }},
        "horario_postagem": "melhor horario com justificativa para o publico do nicho",
        "dia_semana": "melhor dia com justificativa"
    }}
}}

REGRAS CRITICAS:
- GANCHO: impossivel de ignorar. O espectador TEM que parar de scrollar nos primeiros 2 segundos.
- TOM adaptado ao nicho {self.niche} o video inteiro — nada generico.
- B-ROLLS: em TODA cena, com descricoes CINEMATOGRAFICAS e EXATAS.
- ENTONACAO: cada cena deve ter instrucoes vocais precisas como um diretor de cinema daria ao ator.
- AI_VIDEO_PROMPT: cada cena OBRIGATORIAMENTE deve ter prompt em ingles cinematografico profissional, detalhando objetos nas maos, expressao facial, ambiente ao redor, iluminacao, movimento de camera.
- Minimo 6-10 cenas seguindo GANCHO -> CREDIBILIDADE -> CONTEUDO -> CTA.
- ESPECIFICO ao tema: "{topic}" — zero generalizacao.
"""

        response = self.model.generate_content(
            prompt,
            generation_config={
                "temperature": GEMINI["temperature"],
                "max_output_tokens": GEMINI["max_tokens"],
            },
        )

        response_text = self._extract_text(response)

        script = self._parse_json_response(response_text)
        return script

    @staticmethod
    def _parse_json_response(response_text: str) -> dict:
        """Tenta parsear JSON da resposta, com fallback para repair."""
        clean = response_text.strip()

        # Remove markdown code fences
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        # Extrai o JSON entre { e }
        json_start = clean.find("{")
        if json_start < 0:
            return {"raw_script": response_text}

        # Tenta parse do JSON completo
        json_end = clean.rfind("}") + 1
        if json_end > json_start:
            try:
                return json.loads(clean[json_start:json_end])
            except json.JSONDecodeError:
                pass

        # JSON truncado (token limit atingido) — tenta reparar fechando estruturas abertas
        truncated = clean[json_start:]
        repaired = ScriptGenerator._repair_truncated_json(truncated)
        if repaired:
            return repaired

        return {"raw_script": response_text}

    @staticmethod
    def _repair_truncated_json(text: str) -> dict | None:
        """Tenta recuperar um JSON truncado fechando colchetes/chaves abertas."""
        # Conta abertura/fechamento de estruturas
        depth_curly = 0
        depth_square = 0
        in_string = False
        escape_next = False
        last_valid_pos = 0

        for i, ch in enumerate(text):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth_curly += 1
            elif ch == "}":
                depth_curly -= 1
                if depth_curly == 0:
                    last_valid_pos = i + 1
            elif ch == "[":
                depth_square += 1
            elif ch == "]":
                depth_square -= 1

        # Fecha as estruturas abertas
        closing = ""
        # Remove trailing comma/incomplete field antes de fechar
        trimmed = text.rstrip()
        # Remove ultima linha incompleta se nao tiver fechamento
        if trimmed and trimmed[-1] not in ('"', '}', ']', '0123456789'):
            # Volta ate a ultima virgula ou chave valida
            for i in range(len(trimmed) - 1, 0, -1):
                if trimmed[i] in (',', '{', '['):
                    trimmed = trimmed[:i]
                    break

        # Recontar apos trim
        depth_curly = 0
        depth_square = 0
        in_string = False
        escape_next = False
        for ch in trimmed:
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth_curly += 1
            elif ch == "}":
                depth_curly -= 1
            elif ch == "[":
                depth_square += 1
            elif ch == "]":
                depth_square -= 1

        closing = "]" * max(0, depth_square) + "}" * max(0, depth_curly)
        candidate = trimmed + closing

        try:
            result = json.loads(candidate)
            print("    AVISO: JSON truncado reparado automaticamente.")
            return result
        except json.JSONDecodeError:
            return None

    # -----------------------------------------
    # SALVAR
    # -----------------------------------------

    def _save_scripts(self, scripts, topic):
        json_path = OUTPUT_DIR / "roteiros.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(scripts, f, ensure_ascii=False, indent=2)
        print(f"\n  JSON: {json_path}")
        self._save_ai_prompts(scripts, topic)

    def _save_ai_prompts(self, scripts, topic):
        """Salva arquivo dedicado com todos os prompts para IA de video."""
        prompts_path = OUTPUT_DIR / "ai_video_prompts.md"
        with open(prompts_path, "w", encoding="utf-8") as f:
            f.write(f"# PROMPTS PARA IA DE VIDEO — {topic}\n")
            f.write(f"*Nicho: {self.niche} | Pronto para: Kling AI, Wan2.1, Runway, Pika*\n\n---\n\n")

            for i, script in enumerate(scripts, 1):
                title = script.get("titulo", f"Roteiro #{i}")
                f.write(f"## ROTEIRO #{i}: {title}\n\n")

                prod_prompt = script.get("ai_production_prompt", {})
                if prod_prompt:
                    f.write("### PROMPT GLOBAL (video completo)\n\n")
                    f.write(f"**Modelo recomendado:** {prod_prompt.get('modelo_recomendado', '')}\n")
                    f.write(f"**Motivo:** {prod_prompt.get('razao_modelo', '')}\n\n")
                    f.write("**PROMPT COMPLETO:**\n\n")
                    f.write(f"```\n{prod_prompt.get('prompt_global_en', '')}\n```\n\n")
                    f.write(f"**Negative prompt:** `{prod_prompt.get('parametros_api', {}).get('negative_prompt', '')}`\n\n")
                    f.write(f"**Style Guide:** {prod_prompt.get('style_guide_en', '')}\n\n")
                    f.write(f"**Color Grade:** {prod_prompt.get('color_grade_en', '')}\n\n")
                    f.write("---\n\n")

                cenas = script.get("cenas", [])
                if cenas:
                    f.write("### PROMPTS POR CENA\n\n")
                    for cena in cenas:
                        ai_prompt = cena.get("ai_video_prompt", {})
                        if ai_prompt:
                            f.write(f"#### [{cena.get('momento', '?')}] {cena.get('bloco', '')} — Cena {cena.get('numero', '?')}\n\n")
                            f.write(f"**PROMPT:**\n\n```\n{ai_prompt.get('prompt_en', '')}\n```\n\n")
                            f.write(f"**Negative:** `{ai_prompt.get('negative_prompt_en', '')}`\n\n")
                            f.write(f"**Estilo:** {ai_prompt.get('style_reference', '')} | **Duracao:** {ai_prompt.get('clip_duration_seconds', 5)}s | **Ratio:** {ai_prompt.get('aspect_ratio', '9:16')}\n\n")

                            fala = cena.get("fala", {})
                            ent = fala.get("entonacao", {}) if isinstance(fala, dict) else {}
                            if ent:
                                f.write(f"**Entonacao:** Tom: {ent.get('tom', '')} | Emocao: {ent.get('emocao_na_voz', '')} | {ent.get('velocidade', '')}\n\n")
                                if isinstance(fala, dict):
                                    f.write(f"**Fala:** _{fala.get('texto', '')}_\n\n")

                            f.write("---\n\n")

        print(f"  Prompts IA: {prompts_path}")

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
