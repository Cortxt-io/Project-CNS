# data/

Denna mapp innehaller exporterad projektdata fran CNS.

## Generera projects.json

Fran CNS-repots rot:

```bash
python cns.py export json --output projects/project-vault-dashboard/dashboard/data/projects.json
```

Eller till stdout (for pipe):

```bash
python cns.py export json > path/to/projects.json
```

## Schema

Se `planning/api-schema.md` for fullstandig schemadokumentation.

## Uppdatering

Kor exportkommandot igen efter varje andring i CNS-projekten for att halla dashboarden aktuell.
