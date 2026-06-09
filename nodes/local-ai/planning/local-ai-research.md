# Local AI — Research

## BESLUT (2026-06-09)

**Lokal AI-deploy är uppskjuten tills hårdvaran uppgraderas.**

Systemets GPU är Intel UHD Graphics 610 (integrerat, 1 GB delat VRAM).
Ingen av de planerade modellerna kan köras GPU-accelererat på denna hårdvara.
CPU-only-inferens är tekniskt möjligt men ger 10–50× långsammare svarstider
än GPU — oanvändbart för interaktiva sessioner.

---

## Besvarat

### Runtime: WSL2 vs native Windows
**Beslut: Ollama native Windows** (avvakta tills HW uppgraderas).
Ollama har stöd för native Windows sedan v0.3 och kräver ingen WSL2.
GPU-passthrough via WSL2 CUDA är möjligt men onödigt komplext när native fungerar.

### VRAM-krav per modell

| Modell | Storlek | VRAM (Q4) | Möjlig på nuv. HW? |
|--------|---------|-----------|-------------------|
| Qwen 2.5-Coder 7B | 7B | ~5–6 GB | ✗ (1 GB VRAM) |
| Qwen 2.5-Coder 14B | 14B | ~10–12 GB | ✗ |
| Qwen 2.5 7B | 7B | ~5–6 GB | ✗ |
| GLM-4 9B | 9B | ~6–7 GB | ✗ |
| CodeGeeX4 9B | 9B | ~6–7 GB | ✗ |

CPU-only: Qwen 2.5-Coder 1.5B (Q4, ~1 GB RAM) är enda realistiska alternativet
— men svarstider på 30–120 s/svar. Inte lämpligt för agentarbete.

### Integrationsansats
**Beslut: alternativ (a) — Ollama OpenAI-kompatibelt API.**
Ollama exponerar `/v1/chat/completions` (OpenAI-kompatibelt). Adaptern i
`agent_host.py` pekar om `base_url` mot `http://localhost:11434/v1` när
`provider=qwen|glm`. Inget separat `requests`-anrop behövs.

**Modul-placering:** ny modul `scripts/local_ai.py` (inte i `agent_host.py`)
— håller concerns separerade och låter TUI och andra konsumenter använda den utan
att dra in hela agent-host-beroendeträdet.

### Modellval per uppgift (när HW finns)
- Kodfokus: Qwen 2.5-Coder 7B (eller 14B om VRAM räcker)
- Research/summarize: Qwen 2.5 7B general
- Multilingual: GLM-4 9B

---

## Öppna frågor (kvarstår tills HW uppgraderas)

- [ ] **VRAM-bekräftelse:** Vilken GPU ska ersätta UHD 610? (8 GB VRAM minimum för 7B-modeller)
- [ ] **Startkommando** att lägga i CLAUDE.md / README: `ollama serve` + `ollama pull qwen2.5-coder:7b`
- [ ] **CPU-only test:** Om snabbhet inte är kritisk — testa Qwen 2.5-Coder 1.5B Q4 på CPU som proof-of-concept

---

## Nästa steg (efter HW-uppgradering)
1. Installera Ollama native Windows
2. `ollama pull qwen2.5-coder:7b`
3. Skapa `scripts/local_ai.py` med OpenAI-kompatibel klient mot `localhost:11434/v1`
4. Lägg `provider: qwen` i `agent-definition.schema.json`-instanser
5. Verifiera via `/agent-studio` → välj kodfokus → provider qwen → kör
