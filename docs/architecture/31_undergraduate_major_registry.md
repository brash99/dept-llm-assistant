# Governed Undergraduate Major Registry

The Undergraduate Major Registry is a Semantic Layer knowledge object for
stable, effective-dated facts about CNU undergraduate majors. It is not a
course-prefix lookup and it does not infer majors from completions.

Each immutable major records a stable identifier, published names and aliases,
degree types, status, effective dates when known, academic-unit ownership,
source-specific owner assertions, provenance, evidence, limitations, and a
deterministic fingerprint. Existing stable SEC program identifiers are reused.

The first registry combines three kinds of evidence:

- the 2025–26 official undergraduate catalog, checked against retained
  2021–22 through 2024–25 editions;
- the existing governed SEC program registry;
- Quentin Kidd's pasted department-major administrative mapping.

Administrative ownership is authoritative for the supplied rows. Conflicting
assertions remain explicit: the registry does not silently choose an owner for
Neuroscience, and it preserves catalog-placement conflicts for American
Studies and Studio Art. Catalog-only current majors and administrative-only
possible historical programs remain visible.

Catalog presence is evidence for a catalog edition, not an invented effective
start date. Future reviewed evidence may add dates, historical aliases, and
successor relationships without replacing historical facts.

The object is deliberately ready for later governed relationships:

`Department → owns → Major → requires → Capstone → offered_as → Section`

Capstone extraction and those relationships are not part of this registry.
