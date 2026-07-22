# Faculty Identity

> Knowledge objects store facts. Services derive meaning.

Faculty directory, catalog faculty, department roster, and schedule instructor
observations describe people from different source and temporal contexts. A
source observation is not itself a durable institutional person identity.
`FacultyIdentityService` links only observations supported by exact identifiers,
exact normalized names, reviewed aliases, or bounded deterministic name rules.
Uncertain matches remain separate and are reported as ambiguous.

## Identity is not appointment

| Concept | Meaning |
|---|---|
| Identity | Which observations refer to the same person |
| Appointment | A person's effective relationship to an institutional unit |
| Administrative appointment | A time-bounded administrative role |
| Employment status | Effective employment category or active status |
| Teaching assignment | A person associated with a section and term |

A `FacultyIdentity` contains observed and normalized names, source-observation
references, identifiers actually published by sources, matching methods,
confidence, provenance, ambiguity, and a deterministic fingerprint. It contains
no appointment, tenure, FTE, faculty-home, employment, or workload assertion.

## Deterministic matching

Matching precedence is deliberately narrow:

1. exact published institutional identifier;
2. exact normalized full name;
3. explicitly governed person aliases;
4. compatible middle-name forms for the same exact given and family names;
5. a given-name initial only when exactly one compatible identity exists.

The service does not use fuzzy similarity, an LLM, department coincidence,
title, or teaching subject as identity evidence. The governed Bob/Robert Colvin
alias set demonstrates one identity with multiple observations while preserving
every published name and source record.

The audit reports observation and identity counts, singleton and multi-source
clusters, ambiguity, largest clusters, source-system and schema-field coverage,
and deterministic fingerprints. Name-derived identity remains weaker than a
shared authoritative institutional person identifier. This layer enables later
appointment observation; it does not define populations or denominators.

