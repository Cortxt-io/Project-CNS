# ADR: Beslutspunkt-kritiker — designriktning efter research

> Status: **riktning satt** (discovery/research-pass 2026-06-14, session-77bcfd86, story #146).
> Beslutsprosa (svenska). Gäller story #146 "Decision-point critic" och triage-överlapp i `scripts/triage.py`.

## Bakgrund
Vi designade en self-invokad "beslutspunkt-kritiker" som vid en beslutspunkt granskar Claudes eget
förslag på två linser (SUBSTANS · ÖVERLAPP), fas-medveten via aktiv sessionstyp. Innan fler
fas-varianter byggs gjordes en lätt riktad research (är detta rätt sätt?). Den utmanade två av
designens pelare. Denna ADR fäster slutsatserna så vi inte bygger vidare på fel premiss.

## Beslut (tre riktningsändringar)

1. **Grinda mot EXTERN signal, inte mot modellen själv.**
   *Intrinsic* self-correction (modellen rättar sig utan extern feedback) förbättrar empiriskt ofta
   inte och kan försämra — den lyfter bara med en reliabel extern signal (Huang et al. 2023,
   "LLMs Cannot Self-Correct Reasoning Yet"; TACL-översikt "When Can LLMs Actually Correct…").
   → Kritikern ska hålla förslaget mot något utanför Claude: **katalogen** (`catalog.yaml`),
   **board/issue-status**, befintlig kod (grep), och vid behov en **separat granskar-kontext**
   (annan agent/modell, inte samma pass). Ren "tänk igen"-kritik räknas inte som grind.

2. **Fas läses från ARBETSOBJEKTET, inte från sessionstypen.**
   Branschpraxis (Jira/GitLab/Plane) lägger livscykel-status på work item, inte på arbetspasset.
   Att härleda fas ur sessionstyp gör fasbedömningen passberoende och inkonsekvent för samma objekt.
   → Fasen för kritikerns lins ska läsas ur **fokus-objektets status** (idé-status / issue-board /
   PR-läge) — sessionstypen får vara en *fallback/bekvämlighet*, inte sanning. Sammanfaller med
   befintlig board-delegering (CLAUDE.md: stage/status bor på board) och `idea-dab230b2` (fas per objekt).

3. **Överlapp: Jaccard som grovsåll, embeddings som semantiskt lager.**
   Token-Jaccard (nuvarande `find_overlaps`, 0.30) fångar nästan-identisk text men missar "samma idé,
   andra ord". Branschstandard: MinHash/LSH för skala på ytlik text, **embeddings + cosinus** för
   semantisk nära-dubblett. → Behåll Jaccard som billigt första filter; lägg ett embedding-lager
   ovanpå för semantisk dedup (eget delivery-steg, testas mot vår faktiska idé-kö).

## Konsekvens
- Story #146 omramas: kritikern är en **extern-signal-grind**, inte ren self-critique; fas ur objekt.
- `scripts/triage.find_overlaps` (levererad) är korrekt som *steg 1* — inte återvändsgränd, men inte slutmål.
- Prior art: ingen dokumenterad fas-medveten redundans+substans-grind i stora agent-ramverk
  (MetaGPT/AutoGPT m.fl.) — vår kombination verkar ovanlig (osäkert: deras kod ej läst).

## Kvarstående (testas mot egen data, ej webb)
- Embedding-modell + cosinus-tröskel för våra korta idé-texter.
- Hur stor extern signal som räcker för att vända self-critique från skadlig till nyttig i produktbeslut
  (forskningen är på reasoning-tasks, inte produktstyrning).

## Källor
- Huang et al. 2023, arxiv.org/abs/2310.01798 · TACL "When Can LLMs Actually Correct Their Own Mistakes?"
- Milvus/Zilliz: MinHash-LSH & dedup at scale · Plane / GitLab work-item status docs
- MetaGPT (IBM think) · AutoAgents (arxiv 2309.17288)
