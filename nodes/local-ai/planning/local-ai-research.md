# Local AI — Research

Besvara dessa frågor innan deploy-sessionen startar.

## Runtime: WSL2 vs native Windows

- Fråga: Ger WSL2 tillräcklig GPU-passthrough (CUDA) på detta system, eller är native Windows enklare?
- Fråga: Vilken Ollama-version stöder native Windows bra (utan WSL2)?
- Beslut att fatta: ett runtime-val, inte båda.

## VRAM-krav per modell

| Modell | Storlek | VRAM (Q4) | Primärt syfte |
|--------|---------|-----------|---------------|
| Qwen 2.5-Coder 7B | 7B | ~5–6 GB | Kodfokus |
| Qwen 2.5-Coder 14B | 14B | ~10–12 GB | Kodfokus, bättre |
| Qwen 2.5 7B | 7B | ~5–6 GB | General |
| GLM-4 9B | 9B | ~6–7 GB | Multilingual |
| CodeGeeX4 9B | 9B | ~6–7 GB | Kodfokus, alternativ |

- Fråga: Hur mycket VRAM finns på systemets GPU?
- Fråga: Ska vi köra en modell åt gången eller flera simultant?

## Runtime-alternativ

- **Ollama** — enklast att sätta upp, OpenAI-kompatibelt API, bra Windows-stöd sedan v0.3.
- **LM Studio** — GUI, bra för test, REST-API liknar OpenAI.
- **llama.cpp** — maximal kontroll, kräver manuell kompilering.
- Rekommendation att validera: Ollama native Windows, Qwen 2.5-Coder 7B Q4, endpoint `http://localhost:11434`.

## Integration med agent_host.py

- `agent_host.py` använder Claude Agent SDK idag. Qwen/GLM-stöd kräver antingen:
  a) Ollama OpenAI-kompatibelt API → `anthropic`-klient pekar om mot localhost (om Ollama stöder det).
  b) Separat `requests`-anrop mot `http://localhost:11434/api/chat` i ett nytt auth-fall i `can_use_tool`/auth-kedjan.
- Fråga: Ska local-AI-adaptern ligga i `agent_host.py` eller som en separat modul (`scripts/local_ai.py`)?

## Modellval per uppgift

- Kodfokus (generera/refaktorera Python): Qwen 2.5-Coder
- Research/summarize: Qwen 2.5 general eller GLM-4
- Multilingual (svenska/kinesiska): GLM-4

## Beslut att dokumentera här

- [ ] Runtime-val
- [ ] Modell(er) att installera
- [ ] VRAM-bekräftelse
- [ ] Integrationsansats (a eller b ovan)
- [ ] Startkommando att lägga i CLAUDE.md / README
