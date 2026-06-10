# AGENTUR.md — org-schema (Plan A)

Agenturen är hur **vi driver portföljen** (Plan A, `.claude/`) — inte produktkod.
Den är strukturerad som ett riktigt produktbolag: avdelningar, roller, titlar.

**Bärande princip:** *agenterna ÄR de anställda, skills ÄR deras kompetenser.*
Att skapa en agent = rekrytering (HR-chef). Att förbättra en = utbildning (Kompetensutvecklare).
Det som bygger agenturen själv är därför **People + Platform** — inte en verkstad.

Varje agent har `name` (slug = routing-nyckel), `title` (jobbtitel) och `department` i frontmatter.
`department` speglas i `scripts/router.py:DEPARTMENT`.

## Org-schema

```
                         Rikard — VD
                              │
                   operativ-chef (Operativ chef, COO)
                              │
   ┌──────────┬──────────┬───┴────┬──────────┬──────────┬──────────┬──────────┐
 Produkt     R&D     Engineering Platform  People    Program     Drift   Ekonomi/Komm
```

## Avdelningar

### Ledning
| slug | titel |
|------|-------|
| `operativ-chef` | Operativ chef (COO) |

Driver orkestrering och strategiska beslut; eskaleringspunkt under VD (Rikard).

### Produkt — *vad ska vi bygga*
| slug | titel |
|------|-------|
| `produktchef` | Produktchef |
| `losningsarkitekt` | Lösningsarkitekt |

Produktchefen fångar och triagerar idéer; lösningsarkitekten tar en idé med känd riktning
och levererar teknisk skiss (flöde: produktchef → losningsarkitekt → operativ-chef).

### R&D — *vad finns där ute*
| slug | titel |
|------|-------|
| `forskningsledare` | Forskningsledare |

Webb-research och verifiering mot minst två källor; skriver findings till wiki.

### Engineering — *bygg det*
| slug | titel |
|------|-------|
| `backend-utvecklare` | Backend-utvecklare |
| `frontend-utvecklare` | Frontend-utvecklare |
| `fullstack-utvecklare` | Fullstack-utvecklare |
| `devops-ingenjor` | DevOps-ingenjör |
| `terminal-utvecklare` | Terminal-UI-utvecklare |

### Platform — *intern infrastruktur*
| slug | titel |
|------|-------|
| `plattformsingenjor` | Plattformsingenjör |

Hooks, automation, `session_store.py`, agent-host — agenturens egen infrastruktur.

### People — *agenturen själv*
| slug | titel |
|------|-------|
| `hr-chef` | HR-chef (CHRO) |
| `kompetensutvecklare` | Kompetensutvecklare (L&D) |

HR-chefen rekryterar (validerar ny agent före skapande); kompetensutvecklaren tränar
(förbättrar agentprompter).

### Program — *orkestrering av arbetspass*
| slug | titel |
|------|-------|
| `programledare` | Programledare |
| `sessionskoordinator` | Sessionskoordinator |

Programledaren designar session-trädet (innan arbete); sessionskoordinatorn kedjar pass
(reagerar på done-signal) och flaggar hängande arbete.

### Drift — *operations*
| slug | titel |
|------|-------|
| `lagesanalytiker` | Lägesanalytiker |
| `underhallsingenjor` | Underhållsingenjör |

Lägesanalytikern ger nulägesrapport vid passstart; underhållsingenjören städar zombie-noder
och stale wiki.

### Ekonomi
| slug | titel |
|------|-------|
| `ekonomichef` | Ekonomichef (CFO) |

Vaktar token-/credits-förbrukning; grindar dyra operationer (grön/gul/röd).

### Kommunikation
| slug | titel |
|------|-------|
| `teknisk-skribent` | Teknisk skribent |

Skriver wiki-sidor (arkitektur, memory cards), uppdaterar stale termer.

## Kompetenser (skills) per avdelning

Skills bär `department` i frontmatter. **Gemensam** = delas brett, ägs ej av en avdelning.

| Avdelning | Skills |
|-----------|--------|
| Ekonomi | `ekonomi-uppskattning` |
| Program | `session-bokfor`, `session-handoff`, `cns-fork`, `cns-sync`, `cns-flush` |
| Engineering | `issue-lifecycle`, `pr-protokoll` |
| Produkt | `idea-triage`, `idea-session`, `nod-granska` |
| Kommunikation | `wiki-underhall` |
| People | `agent-studio` |
| Platform | `new-skill`, `new-session-profile` |
| Gemensam | `eskalera-uppat`, `agent-routing`, `cortxt-quests` |

## Underhåll
Lägg till en ny agent → uppdatera detta org-schema OCH `scripts/router.py` (`MODEL_TIER`,
`ROUTING_RULES`, `DEPARTMENT`) i samma ändring. Slugen är ett routing-kontrakt — byt inte löst.
