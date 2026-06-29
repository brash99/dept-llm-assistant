# faculty_travel_procedures

## Root cause

Required document retrieved but outside final top_k.

Raw rank: 16  
Dedup rank: 7  
Rerank rank: 7  
Final rank: none

## Diagnosis

The query correctly points toward faculty travel, but the retrieved chunk from
Faculty Travel Procedures lacks strong document-title context. The document title
in metadata is generic: "Word Document".

## Failure type

Metadata/title-context weakness.

## Future fixes

- prepend document title/path to embedding text
- improve document title extraction
- consider title-aware retrieval or score boosting
