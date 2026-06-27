# Session 1 — Establishing the Vision

*Project Design History*

---

**Date**

June 2026

---

# Introduction

Every software project begins by solving a problem.

This project began by asking a question.

> *How should institutional knowledge be represented so that modern AI systems can reason over it effectively?*

At first glance, the answer appeared straightforward. Large Language Models had recently demonstrated remarkable capabilities in natural language understanding, and Retrieval-Augmented Generation (RAG) had become the dominant approach for providing language models with organization-specific knowledge. Numerous open-source frameworks already existed that promised to build chatbots over collections of documents with surprisingly little code.

It would have been easy to adopt one of these frameworks and produce a working prototype within a matter of hours.

Instead, a different path was chosen.

The objective of this project was never simply to build a departmental chatbot.

The objective was to understand **why** modern retrieval systems are structured the way they are and to construct that architecture from first principles.

This decision would ultimately shape every subsequent design choice.

---

# Objectives

The initial goals of the project were intentionally modest.

1. Build a local Retrieval-Augmented Generation system.

2. Operate entirely on local hardware.

3. Preserve complete control over institutional data.

4. Understand every architectural layer rather than treating existing frameworks as black boxes.

5. Create an implementation that could evolve into something substantially larger than a document search tool.

Although the first application would ultimately become a Department Knowledge Assistant, there was already an intuition that the architecture might eventually support broader institutional problems such as enrollment forecasting, strategic planning, and administrative decision support.

The project therefore began with architecture rather than application.

---

# Choosing Local Inference

An early design decision was that the language model would execute locally rather than through a hosted API.

Several motivations led to this decision.

First, institutional documents frequently contain information that should remain under local administrative control.

Second, local inference allows complete reproducibility of experiments.

Third, eliminating external API dependencies encourages architectural clarity by separating the language model from the remainder of the system.

After evaluating available options, the project adopted a locally hosted vLLM server serving the Qwen family of language models.

From the perspective of the remainder of the software, the language model would simply appear as an OpenAI-compatible endpoint.

This seemingly small decision proved important.

The application would communicate with an interface rather than a particular implementation.

The language model itself became replaceable.

---

# First Architectural Insight

One of the earliest discussions centered on an apparently simple question.

> Is this project about building a chatbot?

The answer gradually became "no."

The chatbot was merely one possible user interface.

The real problem was considerably broader.

The project was fundamentally concerned with representing institutional knowledge in a form that could later be retrieved, analyzed, and reasoned over.

That realization shifted the focus of the project from user interaction toward knowledge representation.

Although this distinction appeared subtle at the time, it would later motivate the introduction of canonical document representations, parser abstractions, provenance tracking, and reusable knowledge objects.

---

# Design Philosophy

Several principles emerged almost immediately.

## Learn the architecture.

Rather than relying on high-level orchestration frameworks, each major component would initially be implemented directly.

The purpose of the project was educational as well as practical.

Understanding every stage of the pipeline was considered more valuable than minimizing development effort.

---

## Separate responsibilities.

Even before the first significant code was written, the project emphasized separating independent concerns.

Data acquisition, parsing, normalization, retrieval, and reasoning would ultimately become distinct architectural layers.

This separation would make experimentation significantly easier as the framework evolved.

---

## Preserve flexibility.

Every implementation decision was evaluated according to a simple question.

> Will this make future experimentation easier or harder?

Whenever possible, the architecture favored interchangeable components rather than tightly coupled implementations.

This philosophy would later lead naturally to parser registries, embedding abstractions, configurable retrieval pipelines, and modular reasoning engines.

---

# Lessons Learned

Perhaps the most important lesson from the first session was that the project itself had been misidentified.

It was not a chatbot project.

It was not even a Retrieval-Augmented Generation project.

Instead, it was becoming an investigation into the architecture of institutional knowledge systems.

This realization established the intellectual direction for every subsequent session.

---

# Looking Ahead

The next challenge was no longer language models.

It was data.

Before knowledge could be retrieved or reasoned over, it first had to be acquired, organized, and understood.

The next session therefore turned toward constructing a reliable mirror of the department's shared Google Drive, establishing the corpus that would eventually become the foundation of the entire framework.
