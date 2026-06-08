---
created: '2026-06-07'
updated: '2026-06-08'
slug: cortxt-graph-view
title: Cortxt Graph View
kind: component
part_of: interface
stage: idea
status: idea
feeds: []
depends_on: []
summary: "Cortxt-dashboardens primära yta: en scope-baserad nodkarta som visualiserar hela frameworket med semantisk zoom, fokus och relationer (part_of/feeds/depends_on)."
tags: []
url_live: ''
url_repo: https://github.com/rian010194/cortxt
---

## Syfte

Grafen är inte en vy bland flera utan dashboardens centrala yta. Du ser hela frameworket på en gång (system som containrar, komponenter inuti), fokuserar en nod (dämpar övriga, lyser kopplingar, öppnar inspektor), och zoomar semantiskt in i ett system. Ersätter kortgrid + explorer som primär navigering.

## Beroenden

## Status

Designbeslut fattade (se planning/decisions.md). Implementation ej påbörjad.

## Nästa steg

## Risker

- **Technical**: Hybrid-layout + semantisk zoom är icke-trivialt i Reactflow.
- **Adoption**: Risk att kartan blir snygg men inte används som faktisk navigering.
- **Ops**: Renderar mot portföljdata — kräver att migreringen körts så inspektorn slipper tomma nya sektioner.

## Arbetslogg

## Anteckningar
