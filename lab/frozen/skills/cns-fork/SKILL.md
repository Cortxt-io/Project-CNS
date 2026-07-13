---
name: cns-fork
department: Program
description: Bokför en fork av det pågående arbetspasset som en barn-session i CNS sessionsträdet (main → forks → forks-under-forks). Använd när ett sidospår knoppas av från ett pass och bör kunna spåras tillbaka till sitt ursprung — t.ex. när användaren säger "forka det här", "bokför sidospåret", "det blev en egen gren", eller när en /btw-aside växer till ett eget arbetspass.
---

# /cns-fork — bokför en fork i sessionsträdet

Sessioner (AI-arbetspass) bildar ett **träd** i CNS: ett rot-/"main"-pass kan ha
forks, och forks kan ha egna forks. Varje fork-post bär ett explicit `parent_id`
till passet den sprang ur — det är vad ett träd kräver. Detta är **ren bokföring**
i datalagret (pushas till GitHub som idéer/sessioner), inte att spawna en faktisk
Claude-process.

Varför ett eget kommando och inte `/btw`: `/btw`-hookens payload saknar fork-event
och förälder-id, så parent-länken kan bara gissas i efterhand. `cortxt_fork_session`
skriver `parent_id` direkt vid forktillfället. `/btw` kan vara en *trigger* som
anropar detta, men fundamentet är den explicita forken.

## När den ska köras
- När ett sidospår knoppas av från ett pass och bör kunna attribueras tillbaka.
- När en `/btw`-aside visar sig vara värd ett eget arbetspass.
- Proaktivt enligt arbetsregeln (CNS-bokföring utan att fråga om lov) — men
  **bekräfta** vilket föräldrapass och vilket spår forken hör till innan push.

## Steg

1. **Hitta föräldern.** Vilken session är detta en fork av? `cortxt_list_sessions`
   (ev. `status='running'` för pass som fortfarande är i gång) ger kandidat-id:n.
   Är detta första passet i kedjan finns ingen förälder — då är det ett rot-pass:
   använd `cortxt_start_session` i stället (rot = `parent_id` saknas).

2. **Knyt spåret (valfritt).** Vad arbetar forken på? `link_kind` + `link_ref`
   (`node`/`issue`/`quest`/`idea`) är ortogonalt mot `parent_id` — en fork kan
   samtidigt höra till ett issue och vara barn till en annan session.

3. **Forka.** `cortxt_fork_session`:
   - `parent_id` — föräldra-sessionens id (obligatoriskt; okänt id → fel).
   - `fork_name` — kort mänsklig etikett på grenen.
   - `summary` — vad forken ska göra / varför den knoppades av.
   - `link_kind` / `link_ref` — spåret forken arbetar på (valfritt).
   - `transcript_id` — Claude Code-sessionens id för spårbarhet bakåt.

   Forken startar som `running`; avsluta den senare med `cortxt_mark_session_done`
   eller spola ner slutsatsen med `/cns-flush`.

4. **Granska trädet.** `cortxt_get_session_tree` (valfri `root_id`) visar grenen
   nästlad — bekräfta att forken hamnade under rätt förälder.

5. **Rapportera.** Kort: fork-id, förälder, etikett och länkat spår.

## Push-läge (samma varning som cns-flush)
Pushen kräver GitHub-credentials (`CNS_GITHUB_TOKEN` + `GITHUB_REPO`, eller
OAuth-env remote). Saknas de skrivs forken till disk men pushen misslyckas —
säg då till användaren att den sparades lokalt men inte nådde GitHub.

## Relaterat
- `/cns-flush` — spola ner ett (fork-)pass slutsats i CNS.
- `/cns-sync` — överlappsdetektering mellan sessioner på samma spår.
