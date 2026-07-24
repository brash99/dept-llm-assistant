# Session 2 — Building the Foundation

> **Archive notice:** Historical laboratory note. Current architecture, status, and commands are documented in [the session archive index](README.md).

*Project Design History*

---

**Date**

June 2026

---

# Introduction

With the overall vision established, the next challenge became obvious.

Before the framework could retrieve, organize, or reason over institutional knowledge, it first needed reliable access to that knowledge.

At the outset of the project, the department's documents already existed in a shared Google Drive containing decades of accumulated material. These files represented the collective institutional memory of the department, including course materials, advising documents, committee reports, accreditation records, administrative correspondence, research information, and historical archives.

The challenge was not obtaining data—it was creating a reliable and reproducible way to work with it.

This session therefore focused on building the infrastructure upon which every subsequent stage of the framework would depend.

---

# Objectives

The primary objectives for this session were:

1. Establish a reproducible development environment.

2. Separate source code from runtime data.

3. Create a reliable local mirror of the department Google Drive.

4. Design a storage layout capable of supporting future processing stages.

5. Establish a workflow suitable for both development and deployment.

Unlike later sessions, very little "AI" work occurred here.

Instead, this session established the engineering foundation that would make the remainder of the project possible.

---

# Development Architecture

One of the first decisions concerned where the framework would execute.

Development would occur primarily on a local MacBook while computationally intensive tasks—including embeddings and language model inference—would execute on a remote NVIDIA A100 GPU server.

GitHub naturally became the synchronization point between these environments.

```text
                Laptop
           (Development)
                 │
            git push/pull
                 │
             GitHub
                 │
                 ▼
         A100 Development Server
                 │
                 ▼
        Local vLLM / GPU Models
```

This architecture allowed rapid software development locally while taking advantage of dedicated GPU hardware for AI workloads.

---

# Separating Code from Data

A second architectural decision proved equally important.

Rather than mixing source code with institutional documents, the repository would contain only software.

All runtime data would reside beneath a dedicated `storage/` hierarchy that was excluded from version control.

```text
storage/
│
├── raw_drive/
├── normalized/
├── chunks/
├── embeddings/
├── vector_db/
├── cache/
├── logs/
└── models/
```

This decision established a clear distinction between the framework itself and the evolving corpus it would process.

The Git repository remained small, portable, and reproducible, while the much larger runtime data could be regenerated at any time.

---

# Google Drive Synchronization

The department's Google Drive became the canonical upstream data source.

Rather than processing documents directly from Google Drive, the framework would maintain a complete local mirror using `rclone`.

This approach offered several advantages.

- Offline operation.
- Faster processing.
- Reproducibility.
- Simplified debugging.
- Protection against accidental modification of source documents.

The local mirror therefore became the stable input to every subsequent stage of the processing pipeline.

```text
Google Shared Drive
         │
         ▼
     rclone sync
         │
         ▼
storage/raw_drive/
```

An unexpected lesson during development involved distinguishing between the Git repository itself and the runtime storage hierarchy.

Early synchronization attempts accidentally produced duplicate directory structures, reinforcing the importance of maintaining a clear separation between source code and generated data.

---

# Corpus Policy

As the mirrored corpus began to grow, another realization emerged.

Not every file belonged in the knowledge base.

Temporary files, hidden files, unsupported formats, and generated artifacts would only increase processing time while contributing little useful information.

Rather than scattering filtering logic throughout the codebase, a centralized corpus policy was introduced.

This policy would eventually determine:

- excluded folders
- excluded file extensions
- hidden files
- future parser selection

By defining these rules once, every stage of the framework could operate consistently.

---

# First Look at the Corpus

With synchronization operational, the scale of the problem became much clearer.

The mirrored repository contained approximately:

- 24,000 files
- over 55 GB of data
- dozens of document formats
- material spanning many years of departmental history

For the first time, the project transitioned from working with isolated examples to operating on a genuine institutional corpus.

This realization strongly influenced later architectural decisions.

Scalability was no longer optional.

It became a fundamental design requirement.

---

# Lessons Learned

Although this session involved relatively little artificial intelligence, it established several architectural principles that would remain central throughout the remainder of the project.

Most importantly, the project adopted a strict separation between:

- source documents
- generated artifacts
- software
- configuration

This separation dramatically simplified both development and experimentation.

The project also reinforced an important philosophy.

Infrastructure should be reliable enough that it becomes invisible.

Future sessions would build increasingly sophisticated knowledge-processing components without needing to revisit the mechanics of synchronization or storage organization.

---

# Looking Ahead

With a reproducible development environment established and a complete institutional corpus available locally, attention could finally shift toward understanding the contents of that corpus.

The next session would introduce corpus inventory and analysis, transforming a collection of thousands of files into something the framework could begin to understand.

The project was now ready to move from infrastructure toward knowledge.
