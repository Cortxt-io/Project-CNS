---
prose: record
date: 2026-07-12
status: frozen
supersedes: null
---

# Agentur-lagret fryst 2026-07-12

Detta är ett **register**, inte en beskrivning. Det redigeras inte. Väcks lagret skrivs ett nytt
register som sätter `supersedes:` till detta.

## Vad som frystes

Hela agenturen: lagret som svarar på frågan *"vem/vilken modell ska göra detta"*. Koden är flyttad
hit med `git mv` — historiken är intakt, inget är raderat.

- **Rådgivning/routning:** `router.py`, `recommend.py`, `agentur_routing.py`, `capabilities.py`,
  `agent_roles.py`, `agent_registry.py`, `gen_agentur.py`, `scaffold_roster.py`, `tool_families.py`,
  `bemanna.py`, `validate_agent.py`, `validate_org.py`, `agent_eval.py`, `agent_guardrails.py`
- **Hookar** (körde vid varje prompt): `idea_prompt_hook.py`, `btw_capture.py`, `dirigent_check.py`,
  `ekonom_tracker.py`
- **Exekvering:** `dispatch.py`, `mcp_router.py`, `claude_client.py`, `worktree.py`, `tui/`
- **Registret:** `agents/` (27 agenter), `org/` (manifest + bemanningsmatris),
  `config-agenturer/`, `skills/` (`org-maintenance`, `staff-role`)
- **Tester:** `tests/frozen/` (14 filer). De raderas inte — de är beviset som gör lagret väckbart.
  De körs inte (`pytest.ini` exkluderar katalogen), eftersom modulerna medvetet inte längre ligger
  på `scripts`-namespacet.

## Varför

Lagret körde vid varje tangenttryck och **ljög tyst medan det gjorde det**. Vid frysningen var
följande sant — verifierat mot källan, inte antaget:

1. **Den riktiga routningen var redan död.** `agentur_routing.route()` kräver
   `lab/exports/agents.json`. Den filen fanns inte. Squaden var tom, varje gång.
2. **Det som syntes i prompten var inte agenturen.** `[ROUTING] @devops-engineer` kom ur
   `router.py:ROUTING_RULES` — en handunderhållen nyckelordstabell — inte ur agentur-modellen.
   Statusradens `delivery` var en *sessionstyp* ur `session_store`, inte en avdelning. De två såg
   ut att höra ihop och gjorde det inte.
3. **Ekonomin bokförde mot fel nycklar.** `ekonom_tracker.AGENT_MODEL_TIER` hade kvar svenska
   slugs (`devops-ingenjor`, `ekonomichef`) efter den engelska namnmigreringen. Nästan varje pass
   föll till `DEFAULT_TIER`. Siffrorna var inte fel — de var meningslösa.
4. **`cns status` var redan trasigt.** Det importerade `scripts.tui.viewmodel`, en fil som aldrig
   har funnits i repot (bekräftat: `git cat-file -e HEAD:...` → does not exist). `lab/CLAUDE.md`
   beskrev den ändå. Samma gällde selftest-checken `_orientering`.

Ett lager som ljuger tyst i varje prompt är värre än inget lager. Frysningen tar bort lögnen utan
att kasta arbetet.

## Fällan som fanns på vägen ut (och som är lagad)

`recommend.py` **är inte routning** — den är cockpitens datakälla. `command_center.py` och
`board.py` gjorde lata default-importer av `scripts.recommend` som låg *utanför* de try/except-block
som följde dem. Att bara flytta filen hade gett `ImportError` → `/api/command-center` **500** →
tom cockpit på app.cortxt.io.

Seamet härdades först (`try/except ImportError` → tom lista), med regressionstest i
`tests/test_command_center.py::test_survives_frozen_recommend` och motsvarande i `test_board.py`.
Cockpitens **missions överlever** (de hämtas direkt ur GitHub); bara **orders** blir tom.

## Vad som lever kvar

CNS Core (`cns.py`, root-`scripts/`) och portfölj-pipelinen (`vault_reader`, `phase_derive`,
`venture_cli`, `venture_checklist`, `roadmap`, `reconcile`, `systemmap`), GitHub-ryggraden
(`issues_client`, `gh_project_sync`, `prs_client`) samt cockpiten (`command_center`, `board`,
`lab/app/server.py`). Inget av dessa importerade någonsin routningslagret — det var därför snittet
gick att göra rent.

Kvarhållna gränsfall, och varför: `session_store`, `health`, `idea_inbox` och `lease_store` har
levande konsumenter utanför agenturen. `worktree` och `claude_client` hade inga alls — de följde med.

## Kommandon som nu avvisar

`cns tui` · `cns status` · `cns dispatch` · `cns agent-ask` · `cns agent-tools` · `cns mcp-servers`
→ `_frozen()` i `cns.py`, exit 2, med pekare hit. Selftest-checkarna för recommend, dispatch-loop
och LLM-ping är borttagna; `_orientering` bevisar numera istället att cockpiten degraderar utan
agentur-lagret.

Statuslinjen och de fem hookarna är borttagna ur arbetsytans `.claude/settings.json`
(backup: `.claude/settings.json.pre-freeze-2026-07-12.bak` — arbetsytan är inte ett git-repo).

## För att väcka lagret

1. Bestäm **vad** som ska väckas. "Hela agenturen" är förmodligen fel svar — punkt 1–3 ovan säger
   att stora delar aldrig fungerade som avsett.
2. Flytta tillbaka valda moduler till `lab/scripts/`, deras tester till `tests/`.
3. Laga de tre lögnerna: generera `agents.json` (`gen_agentur.py`), migrera
   `ekonom_tracker.AGENT_MODEL_TIER` till engelska slugs, och avgör om `ROUTING_RULES` ska finnas
   kvar eller ersättas av `agentur_routing`.
4. `viewmodel.py` måste faktiskt skrivas innan `cns status` kan väckas.
5. Skriv ett nytt register som `supersedes:` detta.
