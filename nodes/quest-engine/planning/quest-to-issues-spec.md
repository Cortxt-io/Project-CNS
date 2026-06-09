# Spec (UTKAST): Quest → GitHub Issues

Status: **utkast, ej godkänt.** Spec först — bygg inget förrän öppna frågor nedan är besvarade.

## 1. Mål
Flytta arbetsuppgifts-lagret ("quests") från CNS:s interna JSON-lager till **GitHub Issues**, och låta GitHub vara där arbete *bokförs och stängs*. CNS fortsätter äga **strukturen** (noder, relationer); GitHub äger **uppgifterna**.

## 2. Icke-mål
- Inte röra nodmodellen (`node.md`, `kind`/`stage`/relationer) — den är oförändrad.
- Inte migrera bort `eventstream` (Redis) — den loggar fortsatt aktivitet.
- Inte bygga egen issue-UI — GitHub är UI för uppgifter; dashboarden *speglar* dem.

## 3. Källa-till-sanning (KÄRNBESLUT — måste låsas först)
Förslag:
- **`node.md` = struktur/identitet.** Sanning i CNS (GitHub-repo via Contents API).
- **GitHub Issue = en arbetsuppgift.** Sanning på GitHub.
- **Brygga node ↔ issue:** issuen taggas med nodens slug. Förslag: **label `node:<slug>`** (maskinläsbar, filtrerbar) + sluggen i issue-bodyn för människor.
- En nod kan ha 0..N öppna issues. En issue tillhör exakt en nod (en `node:`-label).

> **Öppen fråga A:** label (`node:<slug>`) vs. en `### Node: <slug>`-rad i bodyn vs. GitHub Projects-fält? Label rekommenderas (filtrerbar via API). **Besvara innan bygge.**

## 4. Mappning quest → issue
| Quest-fält (idag) | Issue-motsvarighet |
|---|---|
| `id` | issue-nummer (`#N`) |
| `slug` (nod) | label `node:<slug>` |
| status `suggested/active/in_progress/completed/archived` | label `status:*` ELLER issue open/closed + ev. label. **Öppen fråga B.** |
| titel/beskrivning | issue title/body |
| `result_summary` (vid complete) | stäng-kommentar på issuen |
| auto-completion via push/PR | GitHub-native: "Closes #N" i PR stänger issuen vid merge |

> **Öppen fråga B:** Hur representeras quest-stage? Tre alternativ: (1) bara open/closed + en `status:in_progress`-label, (2) GitHub Projects-kolumner, (3) labels per stage. (1) är enklast; (2) ger kanban men mer API-yta. **Besvara innan bygge.**

## 5. MCP-kontrakt (app/mcp_server.py) — den enda brytande MCP-ändringen
Rename:n lämnade MCP-namnen orörda med flit — **ta hela MCP-kontraktsbytet här, en gång.**

Nuvarande → föreslaget:
- `cortxt_list_active_quests` → `cortxt_list_open_issues` (ev. arg `node_slug?`, `assignee?`)
- `cortxt_get_quest` → `cortxt_get_issue` (arg: issue-nummer)
- `cortxt_complete_quest` → `cortxt_close_issue` (arg: issue-nummer, `result_summary` → stäng-kommentar)
- NYTT: `cortxt_create_issue` (arg: `node_slug`, title, body) — annars finns inget skapande-verktyg.
- `cortxt_list_projects` / `cortxt_get_project` — oförändrade (läser noder).

Implementation: verktygen blir tunna omslag runt **GitHub Issues REST API**. MCP-servern har **redan GitHub-OAuth per användare** → använd den access-token för att agera som rätt användare (alternativt `CNS_GITHUB_TOKEN` som backenden redan har för server-initierade anrop).

> **Konsekvens:** byter verktygsnamn → **connectorn på claude.ai måste re-auth:as/uppdateras** (verktygslistan ändras). Planera ett uttalat omkopplings-ögonblick.

## 6. Backend
- **`scripts/quest_manager.py` / `quest.py`:** ersätts av en `issues_client.py` (eller behåll filnamn, byt innehåll) som wrappar Issues API: list/get/create/close, label-hantering `node:<slug>`.
- **`app/server.py` → `/api/webhook/github`:** auto-complete-logiken (push/PR/workflow_run → completa quest) **krymper** — GitHub stänger själv issues via "Closes #N" i merge:ad PR. Webhookens roll blir främst **eventstream-loggning** + ev. spegling av issue-events (`issues`, `issue_comment`) till Redis.
  - Lägg till `issues`/`issue_comment` i webhook-prenumerationen på GitHub.
- **CLI (`cns.py`):** `cns quest …`-kommandona pekas om till issues, eller deprekeras till `cns issue …`. **Öppen fråga C.**

> **Öppen fråga C:** Behålls `cns quest`-CLI:t (omdöpt/omdirigerat) eller tas det bort? Vissa flöden kan vilja skapa issues offline.

## 7. Dashboard (cortxt — separat repo)
- Quest-vyerna (`QuestBoardView`, `QuestDetailView`, `useQuest(s)`, `QuestCard`, `QuestSection`, `QuestStatusBadge`) pekas om mot de nya endpointsen/issue-formen.
- Lägre prio (cortxt får knaka): görs efter backend/MCP är på plats.

## 8. Migrering av befintliga quests
- Engångsskript: läs nuvarande quest-JSON (`exports/quests/*.json`), skapa motsvarande GitHub Issue per aktiv/öppen quest med rätt `node:<slug>`-label, stäng redan completade som closed med kommentar.
- Arkivera gamla JSON-filer (behåll för historik, sluta skriva till dem).

## 9. Stegordning (varje steg = egen PR, verifierbar)
0. **Lås öppna frågor A–C.**
1. `issues_client.py` + tester mot ett test-repo/label-schema.
2. MCP-verktygen pekas om (nya namn) — bakåtkompat: behåll gamla `*_quest`-namn som tunna alias en övergångsperiod om möjligt, annars hård brytning + connector-re-auth.
3. Webhook: lägg `issues`/`issue_comment`, krymp quest-auto-complete.
4. Migreringsskript (engång).
5. CLI-beslut (fråga C).
6. Dashboard-vyer.
7. Riv quest-JSON-lagret när inget läser det.

## 10. Risker
- **Dubbel sanning** om brygga/ägarskap inte låses (fråga A/B) → quests och issues driver isär.
- **Connector-brott** vid MCP-namnbyte → planerat omkopplings-ögonblick krävs.
- **Rate limits** på Issues API vid migrering/bulk → batcha.
- **OAuth-scope:** per-användar-token måste ha `repo`/`issues`-scope; verifiera i OAuth-flödet.

## Öppna frågor att besvara före bygge
- **A:** node↔issue-brygga: label `node:<slug>` (rek.) / body-rad / Projects-fält?
- **B:** quest-stage: open/closed + `status:in_progress`-label (rek.) / Projects-kolumner / stage-labels?
- **C:** `cns quest`-CLI: omdirigera till issues / döp om till `cns issue` / ta bort?
- **D:** MCP-namnbyte: hård brytning + re-auth, eller övergångsperiod med alias?
- **E:** token för Issues-anrop: per-användar-OAuth-token (rek.) eller `CNS_GITHUB_TOKEN`?
