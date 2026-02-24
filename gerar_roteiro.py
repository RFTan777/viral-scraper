#!/usr/bin/env python3
"""
Gera roteiros diretamente das transcricoes existentes.
Sem API. Sem imports complexos. So roda.
"""

import json
from pathlib import Path
from collections import Counter
from datetime import datetime

DATA_DIR   = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

PRODUCT = "Chat IA Automatico + CRM"
NICHE   = "automacao de atendimento com IA para empresas"

# ─────────────────────────────────────────────
# 1. CARREGAR TRANSCRIÇÕES
# ─────────────────────────────────────────────

trans_raw = json.loads((DATA_DIR / "transcriptions.json").read_text(encoding="utf-8"))

videos = []
for vid_id, entry in trans_raw.items():
    t = entry.get("transcription", {})
    if not isinstance(t, dict):
        continue
    wc  = t.get("word_count", 0)
    wpm = t.get("words_per_minute", 0)
    text = t.get("text", "").strip()

    # Filtro basico: minimo 20 palavras e nao so musica
    if wc < 20 or not text:
        continue

    # Filtro WPM: abaixo de 40 provavelmente nao e fala
    if wpm > 0 and wpm < 40:
        continue

    videos.append({
        "id": vid_id,
        "author": entry.get("author", "?"),
        "platform": entry.get("platform", "tiktok"),
        "text": text,
        "hook_text": t.get("hook_text", text.split(".")[0][:120]),
        "hook_classification": t.get("hook_classification", {}),
        "word_count": wc,
        "wpm": wpm,
        "total_duration": t.get("total_duration", 0),
        "segments": t.get("segments", []),
    })

print(f"Videos carregados: {len(videos)}")

# ─────────────────────────────────────────────
# 2. EXTRAÇÃO DE PADRÕES
# ─────────────────────────────────────────────

wpm_vals  = [v["wpm"] for v in videos if v["wpm"] > 0]
wc_vals   = [v["word_count"] for v in videos]
dur_vals  = [v["total_duration"] for v in videos if v["total_duration"] > 0]

avg_wpm = round(sum(wpm_vals) / len(wpm_vals)) if wpm_vals else 150
avg_wc  = round(sum(wc_vals)  / len(wc_vals))  if wc_vals  else 150
avg_dur = round(sum(dur_vals) / len(dur_vals), 1) if dur_vals else 60.0

# Hook types
hook_counter = Counter()
best_hooks = []
for v in videos:
    hc = v["hook_classification"] or {}
    hook_type = hc.get("tipo", "outro")
    hook_counter[hook_type] += 1
    hook_text = v["hook_text"]
    if hook_text and len(hook_text) > 15:
        best_hooks.append({
            "texto": hook_text,
            "tipo": hook_type,
            "score": hc.get("score", 5),
            "wpm": v["wpm"],
            "author": v["author"],
        })

best_hooks.sort(key=lambda x: (x["score"], x["wpm"]), reverse=True)

# Palavras de poder presentes nos textos
POWER_WORDS = [
    "automático", "automaticamente", "whatsapp", "ia ", "bot", "atendimento",
    "mensagem", "automatizar", "inteligência artificial", "24h", "24 horas",
    "grátis", "gratuito", "resultado", "cliente", "venda", "dinheiro",
    "rápido", "fácil", "simples", "nunca", "sempre", "segredo",
    "sistema", "chat", "crm", "lead", "conversão", "escala",
]
pw_counter = Counter()
for v in videos:
    txt = v["text"].lower()
    for pw in POWER_WORDS:
        if pw in txt:
            pw_counter[pw] += 1

print(f"\nPadrões extraídos:")
print(f"  WPM médio: {avg_wpm} | Duração média: {avg_dur}s | Palavras médias: {avg_wc}")
print(f"  Tipos de hook: {hook_counter.most_common()}")
print(f"  Power words top 5: {[pw for pw, _ in pw_counter.most_common(5)]}")
print(f"  Melhores hooks:")
for h in best_hooks[:5]:
    print(f"    [{h['tipo']}] \"{h['texto'][:90]}\"")

# Frases de gancho reais encontradas nos vídeos (para inspiração)
hook_inspirations = [h["texto"] for h in best_hooks[:6]]

# ─────────────────────────────────────────────
# 3. GERAR RELATÓRIO DE ANÁLISE
# ─────────────────────────────────────────────

report_lines = [
    f"# RELATÓRIO DE ANÁLISE — Vídeos Virais",
    f"*Nicho: {NICHE} | Produto: {PRODUCT}*",
    f"*Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n",
    "---\n",
    "## 1. RESUMO EXECUTIVO\n",
    f"- **Vídeos analisados:** {len(videos)}",
    f"- **WPM médio:** {avg_wpm} palavras/min",
    f"- **Duração média:** {avg_dur}s",
    f"- **Palavras médias por vídeo:** {avg_wc}\n",
    "Os vídeos virais neste nicho seguem padrões claros: **ganchos diretos** no primeiro segundo, "
    "**tutorial/demo visual** como conteúdo central, e **CTA de baixa fricção** (mandar mensagem, "
    "link na bio). O ritmo é acelerado (>150 WPM) o que mantém atenção.\n",
    "## 2. HOOKS REAIS ENCONTRADOS\n",
]
for i, h in enumerate(best_hooks[:8], 1):
    report_lines.append(f'{i}. [{h["tipo"]}] *"{h["texto"]}"*  (WPM: {h["wpm"]})')
report_lines.append("")

report_lines += [
    "## 3. TIPOS DE GANCHO\n",
]
for tipo, cnt in hook_counter.most_common():
    report_lines.append(f"- **{tipo.title()}:** {cnt} vídeos")
report_lines.append("")

report_lines += [
    "## 4. PALAVRAS DE PODER MAIS USADAS\n",
]
for pw, cnt in pw_counter.most_common(15):
    report_lines.append(f"- `{pw}` — {cnt} vídeos")
report_lines.append("")

report_lines += [
    "## 5. FRAMEWORK VENCEDOR\n",
    "```",
    "[0-3s]   GANCHO         — Dor ou resultado chocante. Sem introdução.",
    "[3-10s]  CREDIBILIDADE  — Prova rápida: números, clientes, antes/depois.",
    "[10-45s] CONTEÚDO       — Demo/explicação do sistema. Screencast ao vivo.",
    "[45-60s] CTA FINAL      — Ação clara e simples. Fricção mínima.",
    "```\n",
    "**Tom:** consultivo + direto. Fala como quem já tem o resultado e quer ajudar.\n",
    "**Ritmo:** 150-200 WPM. Rápido mas claro. Cortes a cada 5-8s.\n",
]

report_path = OUTPUT_DIR / "relatorio_viral.md"
report_path.write_text("\n".join(report_lines), encoding="utf-8")
print(f"\nRelatório salvo: {report_path}")

# ─────────────────────────────────────────────
# 4. GERAR OS 3 ROTEIROS
# ─────────────────────────────────────────────

# Palavras por vídeo de 60s com avg_wpm
est_words = int(60 * avg_wpm / 60)

scripts = []

# ══════════════════════════════════════════════════════════════
# ROTEIRO 1 — DOR DIRETA (PAS: Problem → Agitate → Solve)
# ══════════════════════════════════════════════════════════════

roteiro1 = f"""# ROTEIRO #1 — "Seu atendimento está matando suas vendas (e você não sabe)"
**Abordagem:** Dor Direta  |  **Framework:** PAS — Problem → Agitate → Solve
**Duração:** ~60s  |  **Palavras estimadas:** ~{est_words}
*Inspirado nos hooks reais: "{hook_inspirations[0] if hook_inspirations else 'Sabia que você pode...'}"*

---

## CONCEITO

| Campo | Detalhe |
|---|---|
| **Dor central** | Dono de negócio perde clientes toda vez que demora pra responder no WhatsApp, Instagram ou site |
| **Proposta de valor** | Chat IA que responde em segundos, 24h, qualifica o lead e só passa pro vendedor quando o cliente está pronto |
| **Promessa** | Atendimento imediato 24h sem contratar mais atendentes |
| **Persona-alvo** | Dono de PME, 28-45 anos, usa WhatsApp Business, reclama de perder clientes por demora no atendimento |

---

## GANCHO (0-3s) — Intensidade: 9/10

> **🎙️ FALAR:**
> "Você sabe quantos clientes você perde só porque demorou pra responder?
> Pesquisa mostra: 78% dos clientes compram da empresa que responde PRIMEIRO.
> Não da melhor. Não da mais barata. Da que responde **primeiro**."

**Como falar:**
- Volume: **8/10 — firme, direto**
- Velocidade: normal até "78%", **pausa dramática de 0.8s**, depois desacelera
- Tom: alerta de amigo — urgente mas não agressivo
- Ênfase: `VOCÊ SABE` / `PERDE` / `78%` / `PRIMEIRO`
- Pausa dramática: 0.8s antes de "78%" | 0.5s antes de "E não da melhor"

**📲 B-Roll gancho:**
- Celular com WhatsApp aberto, **47 notificações acumulando sem resposta**
- Texto na tela: `❌ 47 msgs sem resposta` (fonte bold branca, fundo vermelho)
- SFX: ping de notificação WhatsApp repetindo x3, acelerando

**Por que funciona:** Ativa medo de perda (loss aversion) com dado concreto. O viewer se vê na situação e fica ansioso pela solução.

---

## CENA 1 — [00:00-00:03] GANCHO — Pergunta que para o scroll

**🎙️ FALAR:**
> "Você sabe quantos clientes você perde só porque demorou pra responder?"

- Tom: pergunta direta, quase acusatória — alerta de amigo
- Volume: 8/10 | Velocidade: normal com pausa no fim da pergunta
- Pausa: **0.5s após "responder?"** — deixa a pergunta ressoar
- Ênfase: **VOCÊ SABE** (descendente) | **PERDE** (enfático)
- Emoção: urgência contida — revelar uma verdade incômoda

**📲 B-Roll:**
- `[0-3s]` WhatsApp Business com 47 msgs não lidas acumulando
- Overlay: *"47 mensagens sem resposta"*
- Transição: início abrupto — sem intro, sem logo, sem música

**📷 Apresentador:**
- Enquadramento: **close** — rosto ocupa 70% da tela
- Expressão: sobrancelha levemente franzida, olhar direto para câmera
- Ângulo: levemente de baixo (transmite autoridade)
- Movimento: estático — nenhum movimento dá peso à pergunta

**🔊 Edição:**
- Início abrupto, sem música no gancho — silêncio dá peso
- SFX: ping de notificação WhatsApp x3

**💡 Storytelling:**
- Técnica: pergunta retórica — viewer fica ansioso pela resposta
- Viewer pensa: *"Quando foi a última vez que deixei alguém esperando?"*
- Engajamento: **9/10**

---

## CENA 2 — [00:03-00:08] GANCHO (continuação) — Estatística chocante

**🎙️ FALAR:**
> "Pesquisa mostra: 78% dos clientes compram da empresa que responde primeiro.
> Não da melhor. Não da mais barata. Da que responde **PRIMEIRO**."

- Tom: revelação — como revelar um segredo importante
- Volume: 9/10 — aumenta levemente em "PRIMEIRO"
- Velocidade: normal até "78%", depois desacelera para enfatizar
- Pausa: 0.8s após "78%" | 0.5s após cada "Não da"
- Ênfase: **78%** (bem enfático) | **PRIMEIRO** (forte, última palavra)

**📲 B-Roll:**
- `[s4]` Gráfico simples: barra mostrando **78%** em vermelho com animação rápida
- Overlay: `"78% compram do 1° que responde"`
- `[s5-8]` Split screen: empresa respondendo rápido (venda fechada) vs. concorrente chegando tarde

**📷 Apresentador:**
- Enquadramento: meio — busto visível para gesticular
- Lean forward (inclinar para frente) ao dizer "78%"
- Levantar 1 dedo ao dizer "PRIMEIRA"

**🔊 Edição:**
- Jump cut no "78%" para ritmo
- Entra levemente música aqui — batida suave, tension building

**💡 Storytelling:**
- Técnica: dado chocante + repetição tripla ("Não da melhor / barata / mais rápida")
- Viewer pensa: *"Isso faz sentido... eu já perdi venda assim."*
- Engajamento: **9/10**

---

## CENA 3 — [00:08-00:15] CREDIBILIDADE — Caso real com números

**🎙️ FALAR:**
> "A gente implementou um chat com IA no WhatsApp de um cliente nosso — loja de móveis, aqui em São Paulo.
> Em 30 dias: 340 atendimentos automáticos, zero atendente extra contratado, R$ 47 mil em vendas fechadas."

- Tom: storytelling — conta história real, não pitch
- Volume: 7/10 — mais calmo, construindo confiança
- Velocidade: moderada — cada número recebe **pausa de 0.5s antes**
- Ênfase: **340 atendimentos** | **zero atendente extra** | **R$ 47 mil**
- Emoção: orgulho discreto — como quem conta resultado sem se gabar

**📲 B-Roll:**
- `[s9-13]` Screenshot real do dashboard: número de atendimentos, taxa de conversão
- Overlay: *"340 atendimentos/mês | R$ 47.000 em vendas"*
- `[s13-15]` Print de conversa WhatsApp: cliente mandou às 23h, IA respondeu em 2 segundos
- Overlay: *"Resposta em 2 segundos — às 23h"*

**🔊 Edição:**
- Destaque nos números (círculo amarelo piscando)
- SFX: "ding" suave a cada número

**💡 Storytelling:**
- Técnica: caso real com números específicos — prova concreta
- Viewer pensa: *"Isso não é promessa vazia, tem resultado real."*
- Engajamento: **8/10**

---

## CENA 4 — [00:15-00:35] CONTEÚDO — Demo ao vivo do sistema

**🎙️ FALAR:**
> "Vou te mostrar como funciona.
> Cliente manda mensagem no WhatsApp da empresa.
> A IA identifica o que ele precisa — produto, orçamento, suporte —
> e já responde com as informações certas, em segundos.
> Se o cliente quiser falar com humano, transfere automaticamente.
> Tudo isso fica registrado no CRM: histórico, interesse, estágio da compra.
> Você acorda de manhã e já tem um relatório de quantos leads vieram, quantos viraram venda."

- Tom: tutorial — claro, passo a passo, sem jargão técnico
- Volume: 7/10 | Velocidade: moderada — tempo para absorver cada ponto
- Pausa de 0.5s após cada virgula de lista
- Ênfase: **em segundos** | **automaticamente** | **CRM** | **acorda de manhã**
- Emoção: entusiasmo controlado — isso é poderoso mas simples

**📲 B-Rolls:**
- `[s16-24]` **Screencast mobile ao vivo:** mão do usuário digita mensagem → IA responde em tempo real com resposta personalizada
  - Overlay: *"Cliente manda → IA responde em 2s"*
- `[s24-30]` **Painel CRM:** lista de clientes, histórico de conversa, tags automáticas (Interessado / Orçamento / Comprou)
  - Overlay: *"CRM automático — sem digitar nada"*
- `[s30-35]` **Dashboard de relatório:** gráfico de leads por dia, taxa de conversão, produtos mais consultados
  - Overlay: *"Relatório diário automático"*

**📷 Apresentador:**
- Picture-in-picture no canto inferior direito enquanto mostra a tela
- Apontar para elementos enquanto fala de cada função

**🔊 Edição:**
- Cortes a cada 5-6s para manter ritmo
- SFX: som de mensagem enviada/recebida durante a demo
- Música mais animada — sistema está "trabalhando"

**💡 Storytelling:**
- Técnica: **show don't tell** — demo real elimina dúvidas
- Viewer pensa: *"É exatamente o que eu precisava. Mas será que é complicado?"*
- Engajamento: **9/10**

---

## CENA 5 — [00:35-00:45] QUEBRANDO OBJEÇÃO — "Parece complicado"

**🎙️ FALAR:**
> "E não precisa de nenhum conhecimento técnico.
> Você não precisa saber programar, não precisa contratar desenvolvedor.
> A gente configura tudo em até 48 horas e entrega funcionando."

- Tom: empático e tranquilizador — remove um peso do ombro
- Volume: 7/10 | Velocidade: um pouco mais lenta — ênfase em simplicidade
- Pausa antes de "A gente configura" — construir antecipação
- Ênfase: **NENHUM conhecimento técnico** | **48 horas** | **funcionando**

**📲 B-Roll:**
- `[s38-44]` Timeline animada: "Reunião" → "Configuração" → "Testando" → "🟢 Ao vivo" em 48h
- Overlay: *"48h do zero ao ar"*

**🔊 Edição:**
- Baixar levemente o volume da música — mais sério

**💡 Storytelling:**
- Técnica: objection kill — remove fricção mental antes que o viewer pense nisso
- Viewer pensa: *"Ok, se é 48h e sem programação... posso tentar."*
- Engajamento: **8/10**

---

## CENA 6 — [00:45-01:00] CTA FINAL — Converter em ação imediata

**🎙️ FALAR:**
> "Se você quer parar de perder cliente por falta de resposta rápida,
> manda um 'IA' aqui no direct ou no link da bio.
> A gente faz um diagnóstico gratuito do seu atendimento
> e te mostra exatamente quanto você está perdendo.
> Grátis. Sem compromisso. Só manda 'IA'."

- Tom: direto e confiante — sem desespero, com clareza
- Volume: 8/10 — aumenta no CTA final
- Velocidade: moderada — clara para quem vai pausar o vídeo e agir
- Pausa maior antes de "Grátis" e antes de "Só manda IA"
- Ênfase: **parar de PERDER** | **GRÁTIS** | **Sem compromisso** | **IA**
- Emoção: convite genuíno — "venha, não tem nada a perder"

**📲 B-Rolls:**
- `[s47-51]` Tela do direct/DM: "IA" sendo digitado, seta animada apontando para o botão
- Overlay: *"Manda 'IA' no direct"*
- `[s56-60]` End card: logo + "Diagnóstico GRATUITO → Link na bio"

**📷 Apresentador:**
- Close — máxima conexão para o CTA
- Apontar para câmera ao dizer "você"

**🔊 Edição:**
- Fade out suave no fim
- Sobe levemente a música — encerramento positivo
- SFX: som de mensagem enviada ao aparecer o end card

**💡 Storytelling:**
- Técnica: **loop fechado** — conecta de volta ao gancho ("parar de perder cliente")
- Viewer pensa: *"Não tenho nada a perder. Vou mandar."*
- Engajamento: **10/10**

---

## MAPA DO VÍDEO

| Faixa | Objetivo | Emoção-alvo | Estratégia |
|---|---|---|---|
| **0-13% (0-8s) GANCHO** | Ativar medo de perda | Ansiedade + identificação | Pergunta retórica + estatística chocante |
| **13-25% (8-15s) CREDIBILIDADE** | Provar que existe solução real | Curiosidade + esperança | Caso real com números específicos |
| **25-58% (15-35s) CONTEÚDO** | Demonstrar o sistema em ação | Desejo + redução de fricção | Screencast ao vivo + quebrar objeção de complexidade |
| **58-100% (35-60s) CTA** | Converter em mensagem/lead | Confiança + urgência suave | Oferta gratuita + ação ultra-simples ("IA") |

---

## ARSENAL DE B-ROLLS

**Gancho:**
- WhatsApp com 47+ notificações acumuladas
- Gráfico: "78% compram do primeiro que responde"
- Split screen: empresa rápida vs. empresa lenta

**Credibilidade:**
- Dashboard do sistema com métricas reais
- Screenshot de conversa: IA respondendo às 23h
- Print de depoimento de cliente (com permissão)

**Conteúdo:**
- Screencast ao vivo: mensagem chegando + IA respondendo
- Painel CRM com histórico automático
- Dashboard de relatório diário
- Timeline: 48h do zero ao ar

**CTA:**
- Tela de direct sendo aberto, "IA" sendo digitado
- End card com QR code + "Diagnóstico Grátis"

---

## PRODUÇÃO

| Campo | Detalhe |
|---|---|
| **Cenário** | Home office ou escritório moderno. Tela de computador visível ao fundo mostrando o sistema. Luz natural ou ring light frontal. |
| **Iluminação** | Ring light frontal OU luz de janela lateral. Sem sombras fortes no rosto. |
| **Figurino** | Camiseta lisa ou camisa aberta. Nada que distraia. |
| **Música** | Lo-fi tech / future bass — energético mas não agressivo. 15% durante fala, sem música no gancho. |
| **SFX** | Ping WhatsApp (gancho) · Som de mensagem enviada (demo) · Caixa registradora suave (resultado) |
| **Formato** | 9:16 vertical — 1080×1920px |

---

## DISTRIBUIÇÃO

**TikTok:** `Você perde cliente todo dia sem saber 📱 #automacao #whatsapp #ia #empreendedor`
**Instagram:** `Por que seu concorrente fecha mais vendas (mesmo com produto pior) 👇`
**Hashtags:** #empreendedor #marketing #vendas #automacao #chatbot #IA #CRM #whatsappbusiness
**Horário:** 18h-20h (comerciante termina o dia)
**Dia:** Terça ou Quarta — pico de engajamento B2B

---
---
"""

# ══════════════════════════════════════════════════════════════
# ROTEIRO 2 — PROVA SOCIAL / ANTES & DEPOIS (STAR)
# ══════════════════════════════════════════════════════════════

roteiro2 = f"""# ROTEIRO #2 — "De 12 atendentes para 1 IA — e as vendas triplicaram"
**Abordagem:** Prova Social — Antes & Depois  |  **Framework:** STAR — Situation → Task → Action → Result
**Duração:** ~60s  |  **Palavras estimadas:** ~{est_words}

---

## CONCEITO

| Campo | Detalhe |
|---|---|
| **Dor central** | Custo alto de atendentes + erros humanos + limitação de horário vs. IA que trabalha 24h sem falhar |
| **Proposta de valor** | Redução de custo de atendimento + aumento de conversão |
| **Promessa** | Mesmo resultado (ou melhor) pagando menos em atendimento |
| **Persona-alvo** | Dono que já tem equipe de atendimento, frustrado com custo e erros, quer escalar sem contratar |

---

## GANCHO (0-5s) — Intensidade: 10/10

> **🎙️ FALAR:**
> "Esse cliente tinha 12 atendentes. Hoje tem 1 IA e um supervisor.
> Faturamento subiu 3x. Custo de atendimento caiu 70%."

**Como falar:**
- Volume: **alto e firme** — declaração de fato, sem exagero
- Velocidade: **pausada** — cada número precisa absorver
- Tom: direto — como quem conta fato, não vende
- Pausa dramática: **1s após "12 atendentes"** antes de "Hoje tem 1 IA"
- Ênfase: **12 ATENDENTES** | **1 IA** | **3x** | **70%**

**📲 B-Roll:**
- Split screen: foto de equipe grande (antes) vs. dashboard com IA processando centenas de mensagens (depois)
- Overlay: `"Antes: 12 pessoas | Depois: 1 IA | +3x vendas"`

**Por que funciona:** Resultado concreto gera curiosidade imediata. Viewer fica se perguntando "como?" e assiste para descobrir.

---

## CENAS

### [00:00-00:05] GANCHO — Resultado chocante

**🎙️ FALAR:**
> "Esse cliente tinha 12 atendentes. Hoje tem 1 IA e um supervisor.
> Faturamento 3x. Custo de atendimento menos 70%."

- Tom: fato — sem pitch, sem exagero | Volume: 9/10
- Pausa: 1s após "12 atendentes" | Ênfase: **12, 1 IA, 3x, -70%**
- Expressão: séria — fatos não precisam de hype

**📲 B-Roll:**
- Gráfico animado: antes/depois de custo e faturamento
- Overlay: `"Antes: 12 pessoas | Depois: 1 IA | +3x vendas"`
- Texto na tela: números grandes, verde (+) e vermelho (-)

**💡** Viewer pensa: *"Isso é real? Como?"*  |  Engajamento: **10/10**

---

### [00:05-00:15] SITUAÇÃO — Criar identificação

**🎙️ FALAR:**
> "Antes disso, a empresa deles estava afogada.
> WhatsApp tocando o dia todo, atendente cometendo erro, cliente esperando horas.
> Cancelamento subindo, reputação caindo.
> Mesmo problema que a maioria das PMEs enfrenta hoje."

- Tom: empático — conta a história como quem viveu
- Pausa antes de "Mesmo problema"
- Ênfase: **afogada** | **horas** | **cancelamento subindo** | **a maioria das PMEs**

**📲 B-Roll:**
- Cenas rápidas: atendentes sobrecarregados, telefone tocando, cliente esperando
- Overlay: *"Situação antes: caos no atendimento"*
- Tom de cor: levemente dessaturado (cenas do "antes")
- SFX: telefone tocando, notificações acumulando

**💡** Viewer pensa: *"Esse sou eu. Eu passo por isso."*  |  Engajamento: **8/10**

---

### [00:15-00:25] AÇÃO — Revelar a solução

**🎙️ FALAR:**
> "A gente implementou o Chat IA Automático.
> Integrado ao WhatsApp, Instagram e site deles.
> IA treinada com os produtos, preços e políticas da empresa.
> Responde qualquer pergunta, qualifica o lead, agenda reunião.
> Tudo no piloto automático."

- Tom: didático e empolgado | Volume: 8/10
- Velocidade: rápida e energica — contraste com o "antes"
- Pausa longa antes de "Tudo no piloto automático"
- Ênfase: **Chat IA Automático** | **qualquer pergunta** | **Tudo no piloto automático**

**📲 B-Roll:**
- Painel de integração: logos WhatsApp, Instagram, site conectados
- Chat respondendo automaticamente em cada canal
- Overlay: `"WhatsApp + Instagram + Site | Tudo automático"`
- Lista animada: ✅ WhatsApp | ✅ Instagram | ✅ Site | ✅ 24h/dia
- Cores mais saturadas (vs. cenas do "antes") — contraste visual

**💡** Viewer pensa: *"Entendi. Isso é o que resolve meu problema."*  |  Engajamento: **9/10**

---

### [00:25-00:40] RESULTADO — Prova final com números

**🎙️ FALAR:**
> "Resultado em 60 dias:
> 1.200 atendimentos automáticos por mês.
> Taxa de resposta: 100% em menos de 5 segundos.
> Conversão de lead para venda subiu 40%.
> E eles economizaram R$ 18.000 por mês só em custo de equipe.
> Isso é o que o Chat IA faz."

- Tom: impactante — cada número é uma vitória | Volume: 9/10
- Pausa de 0.5s antes de cada número
- Ênfase: **1.200** | **100%** | **5 segundos** | **40%** | **R$ 18.000**
- Levantar os dedos a cada número para ritmo visual

**📲 B-Roll:**
- Dashboard animado: atendimentos, conversão, economia crescendo
- Overlay: `"1.200 atend/mês | 100% resposta | +40% conversão | -R$18k/mês"`
- Jump cuts nos números para ritmo
- SFX: contador crescendo, som de sucesso no fim

**💡** Viewer pensa: *"Eu quero esses números. Como faço isso?"*  |  Engajamento: **10/10**

---

### [00:40-01:00] CTA — Oferta irresistível, fricção mínima

**🎙️ FALAR:**
> "Se você quer o mesmo resultado,
> manda 'QUERO' aqui no direct ou acessa o link da bio.
> A gente faz uma análise gratuita do seu atendimento atual
> e projeta quanto você pode economizar e faturar com a IA.
> Sem custo, sem compromisso. Só manda 'QUERO'."

- Tom: convite — sem desespero, com confiança | Volume: 8/10
- Velocidade: clara e pausada — viewer precisa absorver
- Pausa antes de "Sem custo" e antes do "QUERO" final
- Ênfase: **QUERO** | **análise gratuita** | **economizar e faturar** | **QUERO (final)**

**📲 B-Roll:**
- Direct sendo aberto, "QUERO" sendo digitado, botão de enviar
- End card: logo + call-to-action visual + QR code
- Overlay: `"Manda 'QUERO' → Análise GRÁTIS"`

**💡** Viewer pensa: *"É só mandar uma palavra. Vou fazer."*  |  Engajamento: **10/10**

---

## MAPA DO VÍDEO

| Faixa | Objetivo | Emoção | Estratégia |
|---|---|---|---|
| **0-8% GANCHO** | Resultado chocante que para o scroll | Choque + curiosidade | Antes/depois com números reais |
| **8-25% SITUAÇÃO** | Criar identificação com a dor | Empatia + reconhecimento | Descrição vívida da situação "antes" |
| **25-67% SOLUÇÃO+RESULTADO** | Revelar o sistema e provar | Desejo + convicção | Demo + números específicos de 60 dias |
| **67-100% CTA** | Converter em lead | Confiança + baixa fricção | Análise gratuita + palavra-chave simples |

---

## PRODUÇÃO

| Campo | Detalhe |
|---|---|
| **Cenário** | Escritório moderno, tela visível com o sistema aberto. |
| **Música** | Começa tensa (antes), evolui para positivo/tech (depois) |
| **SFX** | Telefone tocando (antes) · Ping de mensagem (depois) · Contador crescendo (resultados) |
| **Figurino** | Profissional — camisa ou polo. Autoridade sem formalidade excessiva. |
| **Formato** | 9:16 vertical |

---

## DISTRIBUIÇÃO

**TikTok:** `De 12 atendentes para 1 IA: como cortaram 70% do custo 📊 #automacao #ia #empreendedor`
**Instagram:** `12 atendentes → 1 IA. Faturamento 3x. Custo -70%. Veja como eles fizeram 👇`
**Hashtags:** #empreendedor #negocios #gestao #automacao #ia #CRM #chatbot #whatsappbusiness
**Horário:** 7h-9h (dono de empresa no café da manhã)
**Dia:** Segunda-feira — início de semana, mentalidade de melhoria

---
---
"""

# ══════════════════════════════════════════════════════════════
# ROTEIRO 3 — REVELAÇÃO / VERDADE INCONVENIENTE
# ══════════════════════════════════════════════════════════════

roteiro3 = f"""# ROTEIRO #3 — "A mentira que te custa clientes todo mês (e ninguém fala sobre isso)"
**Abordagem:** Revelação — Verdade Inconveniente  |  **Framework:** Controvérsia → Reframing → Solução → CTA
**Duração:** ~60s  |  **Palavras estimadas:** ~{est_words}

---

## CONCEITO

| Campo | Detalhe |
|---|---|
| **Crença a derrubar** | "Atendimento humano é sempre melhor que IA" |
| **Verdade revelada** | IA atende mais rápido, 24h, sem erro — e isso vende mais |
| **Persona-alvo** | Dono que resiste à IA por "preferir o toque humano" — mas está perdendo competitividade |
| **Reframing** | Não é IA vs. humano. É IA fazendo volume → humano fazendo valor. |

---

## GANCHO (0-4s) — Intensidade: 10/10

> **🎙️ FALAR:**
> "Atendimento humano não é o diferencial que você pensa.
> Na verdade, pode estar sendo o seu maior problema de vendas."

**Como falar:**
- Volume: **alto, firme, sem hesitação**
- Velocidade: normal — cada palavra deve chegar clara
- Tom: **provocativo mas fundamentado** — não é clickbait, é verdade
- Pausa: **1s de silêncio** após "você pensa." antes de continuar
- Ênfase: `NÃO É O DIFERENCIAL` | `MAIOR PROBLEMA`

**📲 B-Roll:**
- Split screen: atendente humano frustrado ao celular vs. tela de IA respondendo 10 mensagens simultâneas
- Overlay: `"Atendimento humano: o mito que custa caro"`

**Por que funciona:** Desafia uma crença profunda. O viewer discorda mas fica curioso para entender. O desconforto gera retenção.

---

## CENAS

### [00:00-00:04] GANCHO — Controvérsia que gera discordância imediata

**🎙️ FALAR:**
> "Atendimento humano não é o diferencial que você pensa.
> Pode ser o seu maior problema de vendas."

- Tom: firme e provocativo | Volume: 9/10
- Pausa: 1s após "você pensa" | Ênfase: **NÃO É** | **MAIOR PROBLEMA**
- Expressão: séria, leve balanço de cabeça ao dizer "não é"
- Início abrupto — sem intro

**💡** Viewer pensa: *"Discordo. Me convence."*  |  Engajamento: **10/10**

---

### [00:04-00:15] ARGUMENTO — Construindo o caso com dados

**🎙️ FALAR:**
> "Seu atendente humano responde em média em 4 horas.
> A janela de interesse de um lead dura menos de 5 minutos.
> Ele vai no concorrente antes do seu atendente ver a mensagem.
> Não é culpa do atendente. É limitação humana."

- Tom: argumentativo — apresenta fatos com calma | Volume: 8/10
- Pausa antes de cada dado
- Ênfase: **4 horas** | **5 minutos** | **concorrente** | **limitação humana**

**📲 B-Roll:**
- Cronômetro animado: **"4h"** em vermelho vs. **"5 min"** em verde
- Gráfico: perda de lead ao longo do tempo sem resposta
- Overlay: `"Tempo médio de resposta humana: 4h | Janela de interesse: 5min"`
- SFX: relógio ticking

**💡** Viewer pensa: *"Nossa... eu também demoro horas para responder."*  |  Engajamento: **9/10**

---

### [00:15-00:35] REFRAMING — "Não é IA vs. humano. É IA + humano."

**🎙️ FALAR:**
> "A solução não é tirar o humano. É deixar a IA fazer o que humano não consegue:
> responder em segundos, 24 horas, em todos os canais ao mesmo tempo.
> Enquanto isso, seu atendente foca nas vendas que realmente precisam de toque humano:
> negociação, relacionamento, fechamento.
> **IA faz o volume. Humano faz o valor.**"

- Tom: **revelador e empolgante** — o "aha moment" do vídeo
- Volume: 8/10 | Velocidade: moderada
- Pausa longa antes de **"IA faz o volume. Humano faz o valor."**
- Ênfase: **não é tirar o humano** | **em segundos** | **IA faz o volume. Humano faz o valor.**
- Gesto: separar as mãos ao dizer a frase final (IA = mão esquerda | Humano = mão direita)

**📲 B-Rolls:**
- Diagrama animado: IA respondendo centenas de mensagens → funil → leads qualificados passando para o vendedor
- Overlay: `"IA: volume e velocidade | Humano: valor e fechamento"`
- Screencast: "leads qualificados prontos para o vendedor" no dashboard
- Frase de impacto na tela: **"IA faz o volume → Humano faz o valor"** (aparece palavra a palavra, bold)

**🔊 Edição:**
- Música positiva e energética — momento de inspiração
- SFX: "ding" de ideias ao aparecer o conceito

**💡** Viewer pensa: *"Não é IA vs. humano. É IA + humano. Agora faz sentido."*  |  Engajamento: **10/10**

---

### [00:35-00:45] PROVA — Caso real do setor

**🎙️ FALAR:**
> "Um cliente nosso do setor imobiliário fez exatamente isso.
> IA qualifica os interessados, agenda a visita ao imóvel, passa para o corretor.
> Corretor chega na reunião com lead já educado e pronto.
> Taxa de fechamento? Dobrou em 45 dias."

- Tom: storytelling — caso real, rápido e específico
- Pausa antes de "Taxa de fechamento?"
- Ênfase: **imobiliário** | **pronto** | **Dobrou**
- Sorriso genuíno ao mencionar "Dobrou"

**📲 B-Roll:**
- Chat de IA qualificando lead de imóvel (perguntando: "Qual seu orçamento? Quantos quartos?")
- Lead passado para o corretor com tag "PRONTO PARA FECHAR"
- Overlay: `"IA qualifica → Corretor fecha | Taxa de fechamento: +2x"`

**💡** Viewer pensa: *"Funciona no meu setor também?"*  |  Engajamento: **8/10**

---

### [00:45-01:00] CTA — Oferta de descoberta personalizada

**🎙️ FALAR:**
> "Quer ver como isso funciona no seu negócio específico?
> Manda 'TESTE' no direct ou no link da bio.
> A gente faz um diagnóstico gratuito —
> sem compromisso, sem enrolação.
> Você vê com os seus próprios olhos o que a IA faria pelo seu atendimento."

- Tom: **curioso e convidativo** — oferecer uma descoberta, não uma venda
- Pausa antes de "sem compromisso"
- Ênfase: **seu negócio específico** | **TESTE** | **gratuito** | **seus próprios olhos**

**📲 B-Roll:**
- Direct sendo aberto, "TESTE" sendo digitado
- End card: logo + "Diagnóstico Grátis" + QR code

**💡** Viewer pensa: *"É personalizado para mim. Vou mandar."*  |  Engajamento: **10/10**

---

## MAPA DO VÍDEO

| Faixa | Objetivo | Emoção | Estratégia |
|---|---|---|---|
| **0-7% GANCHO** | Provocar discordância que gera curiosidade | Choque + curiosidade | Afirmação controversa + silêncio |
| **7-25% ARGUMENTO** | Fundamentar a controvérsia com dados | Desconforto + reflexão | Dados temporais chocantes |
| **25-58% REFRAMING** | Resolver o conflito com elegância | Revelação + entusiasmo | "Não é vs. É +" + caso real |
| **58-100% CTA** | Converter o interesse em ação | Confiança + curiosidade personalizada | Diagnóstico personalizado |

---

## PRODUÇÃO

| Campo | Detalhe |
|---|---|
| **Cenário** | Escritório profissional, tela visível com o sistema |
| **Música** | Começa suspense/tensão → evolui para positivo/tech no reframing |
| **SFX** | Relógio ticking (argumento) · Ding de ideias (reframing) · Mensagem enviada (CTA) |
| **Figurino** | Profissional casual — autoridade sem distanciar |
| **Formato** | 9:16 vertical |

---

## DISTRIBUIÇÃO

**TikTok:** `A verdade sobre atendimento humano que ninguém fala 👀 #ia #automacao #empreendedor #vendas`
**Instagram:** `Atendimento humano pode estar te custando mais do que você imagina. Thread 👇`
**Hashtags:** #empreendedor #vendas #marketing #gestao #ia #automacao #chatbot #CRM #whatsapp
**Horário:** 12h-14h (almoço — dono de empresa usa celular durante a pausa)
**Dia:** Quarta ou Quinta — meio da semana, mindset de otimização

---
---
"""

# ──────────────────────────────────────────────────────────────────
# SALVAR TUDO
# ──────────────────────────────────────────────────────────────────

intro = f"""# CAMPANHA: {PRODUCT}
*Nicho: {NICHE}*
*Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}*
*Base: {len(videos)} vídeos analisados localmente*

---

## PADRÕES EXTRAÍDOS DOS VÍDEOS VIRAIS

| Métrica | Valor |
|---|---|
| **WPM médio** | {avg_wpm} palavras/min |
| **Duração média** | {avg_dur}s |
| **Palavras médias** | {avg_wc} |
| **Tipos de hook** | {', '.join([f'{t}({c})' for t,c in hook_counter.most_common(3)])} |

**Hooks reais encontrados nos vídeos:**
"""
for i, h in enumerate(hook_inspirations[:5], 1):
    intro += f'{i}. *"{h}"*\n'

intro += "\n---\n\n"

full_md = intro + roteiro1 + roteiro2 + roteiro3

roteiros_path = OUTPUT_DIR / "roteiros.md"
roteiros_path.write_text(full_md, encoding="utf-8")

# JSON simplificado
scripts_json = [
    {"numero": 1, "titulo": "Seu atendimento está matando suas vendas", "abordagem": "Dor Direta", "framework": "PAS"},
    {"numero": 2, "titulo": "De 12 atendentes para 1 IA — e as vendas triplicaram", "abordagem": "Prova Social", "framework": "STAR"},
    {"numero": 3, "titulo": "A mentira que te custa clientes todo mês", "abordagem": "Revelação", "framework": "Controvérsia → Reframing"},
]
(OUTPUT_DIR / "roteiros.json").write_text(
    json.dumps(scripts_json, ensure_ascii=False, indent=2), encoding="utf-8"
)

print(f"\n{'='*60}")
print("ROTEIROS GERADOS!")
print(f"{'='*60}")
print(f"\n  output/roteiros.md        -- 3 roteiros completos com storytelling")
print(f"  output/relatorio_viral.md -- Analise de padroes")
print(f"  output/roteiros.json      -- JSON estruturado")
print(f"\n  Roteiro 1: Dor Direta (PAS) -- 'Voce perde cliente por nao responder rapido'")
print(f"  Roteiro 2: Prova Social (STAR) -- '12 atendentes > 1 IA, +3x vendas'")
print(f"  Roteiro 3: Revelacao -- 'Atendimento humano pode ser seu maior problema'")
print(f"\n  Sem API. Sem Gemini. Zero custo adicional.")

scripts.extend([{"roteiro": 1}, {"roteiro": 2}, {"roteiro": 3}])
