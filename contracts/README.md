# Data Contracts

## Purpose

Formal agreements between data producers and consumers.
Breaking changes require approval + 30-day deprecation window.

## Structure

- `schemas/` - Pydantic models + YAML definitions
- Versioned: `petition_events_v1.yaml`, `petition_events_v2.yaml`

## Schema Evolution Rules

✅ Allowed: Add nullable column, add enum value
❌ Forbidden: Remove column, rename column, change type

## Enforcement

- CI validates contracts on every PR
- Runtime validation via Great Expectations
