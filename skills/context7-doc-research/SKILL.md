---
name: context7-doc-research
description: Retrieve accurate, up-to-date library and framework documentation through Context7 during implementation tasks. Use when coding against external dependencies, validating API usage, or reducing outdated examples in generated code.
---

# Context7 Doc Research

## Overview

Use Context7 as the primary source for dependency-specific coding guidance.
Prefer targeted retrieval for concrete libraries and versions used in the task.

## Workflow

1. Identify external library or framework used by the task.
2. Resolve the correct library identifier in Context7.
3. Retrieve focused documentation relevant to the current change.
4. Apply guidance in implementation with minimal assumptions.
5. Record key references in task notes when behavior is critical.

## Usage rules

- Do not query Context7 for repository-internal architecture decisions.
- Use Context7 for API signatures, version-specific behavior, and integration patterns.
- Keep retrieval focused to avoid noisy context.

## Quality checks

- Confirm examples match project language and dependency versions.
- If docs conflict with existing codebase patterns, flag and escalate to architecture review.

Use `references/research-playbook.md` for a short operational playbook.
