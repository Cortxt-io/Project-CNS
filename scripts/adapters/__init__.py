"""Drift-ekrar (deploy-adaptrar) mot externa ytor.

Första ekern i integrations-mönstret (#78): CNS *agerar* mot en nods ``deploy``-yta
(connect/status/deploy). Skild från ryggraden (GitHub, rörs ej) — se minnet
``integration-ryggrad-vs-ekrar``. Varje adapter är ett plain-REST-lager (samma form som
``scripts/prs_client.py``): modulfunktioner, ``requests``, fail-open utan token, plain dicts.
"""
