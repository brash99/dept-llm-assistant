# AGENTS.md

## Project

This repository contains the Institutional Semantic Observatory, an evidence-centered decision-support system for Christopher Newport University.

The canonical server repository is /work/brash/dept-llm-assistant.

## Core principle

Knowledge objects store facts. Services derive meaning.

## Permanent architecture

Use the following six-layer architecture in all planning, documentation, and implementation work:

1. Evidence Layer
2. Semantic Layer
3. Reasoning Layer
4. Evidence Fitness
5. Scenario Modeling
6. Institutional Digital Twin

Layers 1 through 5 are required for the August 1, 2026 Quentin milestone. Layer 6 is a longer-term objective.

Do not replace this architecture with arbitrary phase labels.

## Primary objective

The primary objective through August 1, 2026 is to support Quentin's benchmark question:

If CNU reduces full-time faculty from approximately 275 to 250, which departments should lose positions?

The system must not manufacture recommendations when the evidence is inadequate. It must identify available evidence, missing evidence, evidence quality, strategic considerations, and decision readiness.

## Evidence rules

Evidence quantity is not evidence diversity.

Do not count drafts, revisions, filename variants, or duplicate document families as independent evidence.

Preserve distinctions among institutional evidence, institutional self-studies, external standards, external comparators, and constitutional evidence.

A single-year enrollment snapshot is not an enrollment trend.

Institutional values must come from identified sources such as the Strategic Compass or leadership-approved strategic materials. They must not be invented by the model.

## Engineering rules

Prefer targeted, test-backed improvements over broad architectural rewrites.

Inspect the existing implementation before changing architecture.

Do not casually rename major concepts, layers, services, directories, or knowledge-object types.

Add regression tests for bug fixes and semantic refinements when practical.

Never report that a test passed unless it was actually run.

## Documentation rules

Documentation must describe the system as it currently exists.

Use the permanent six-layer architecture.

Distinguish implemented, partially implemented, planned, and aspirational capabilities.

Keep Mac instructions separate from A100 server instructions.

Use /work/brash/dept-llm-assistant as the canonical A100 path.

Remove obsolete commands, paths, duplicated instructions, and contradictory descriptions.

## Operational safety

Do not commit, push, deploy, delete data, rebuild large indexes, or modify production configuration unless explicitly instructed.

After making requested changes, stop after verification unless commit, push, or deployment was explicitly requested.
