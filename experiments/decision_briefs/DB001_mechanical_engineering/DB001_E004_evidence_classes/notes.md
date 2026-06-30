# DB001-E004 — Evidence Classes

Date: 2026-06-30

## Goal

Evaluate whether explicit Evidence Classes improve institutional reasoning.

## Changes

- Added EvidenceClass abstraction.
- Classified retrieved sources into:
  - Institutional Evidence
  - Planning Document
  - External Standard
  - External Comparator
- Grouped evidence by Evidence Class before prompt construction.
- Added Evidence Class labels to each retrieved source.
- Updated Decision Brief prompt to explain the role of each Evidence Class.

## Query

What additional resources would be required to establish a Mechanical Engineering major?
