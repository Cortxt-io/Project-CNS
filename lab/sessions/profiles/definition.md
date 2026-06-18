---
type: definition
title: Definition / spec
mode: definition
agents: [produktchef, losningsarkitekt]
---

# Definition-session

Syfte: definitionssteget mellan triage och delivery. Fixera *vad*, *varför* och
*acceptanskriterier* innan en rad kod skrivs — det är här dyra felbyggen undviks.
Output = en granskningsbar spec som delivery-passet exekverar mot.

## Agentbeteende
- **@produktchef** äger vad/varför: problemet, målbilden, och acceptanskriterier i
  Given/When/Then-form. Skriv kriterierna direkt på issuet via `cortxt_add_acceptance`
  (parsas under `## Acceptanskriterier`, skilt från todos = agentens DoD).
- **@losningsarkitekt** skissar hur + risker: berörda filer/komponenter, dataflöde,
  beroenden (`cortxt_set_depends_on`), och öppna frågor som måste besvaras före delivery.
- **Ingen kod.** Detta är ett definitionspass — inga Edit/Write mot produktkod.
- Öppna frågor lämnas *i specen* så de tvingas besvaras innan delivery, inte gissas bort.
- Sätt `type` på issuet (`cortxt_set_issue_type`: story|bug|spike|chore) så delivery-passet
  vet vad det exekverar.
- Vägval presenteras med AskUserQuestion-väljaren; ren bokföring frågar inte.

## Kedja
- Forka gärna från ett triage-pass (`cortxt_fork_session`) och låt delivery-passet forka
  härifrån — definition → delivery via sessionsträdet, med specen som handoff.

## Avslut
- Rapport: vilka issues fick acceptanskriterier, vilka beroenden sattes, vilka öppna
  frågor kvarstår (blockerar delivery om obesvarade).
- `cortxt_save_session` med länk till berörd quest/nod.
