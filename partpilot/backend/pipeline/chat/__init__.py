"""Guided chat — the machine asks, the user picks an answer.

A server-side conversation that narrows look-alike candidates down to one
SKU by asking questions derived from catalog metadata (fitment, brand,
part number, visual attributes). The user never types: every turn offers
a fixed set of options, so every answer provably narrows the candidate
set and nothing is ever invented.

This is the backend counterpart of the frontend's guided disambiguation
(`frontend/src/services/disambiguation.ts`) — the same question logic,
run server-side against catalog truth, with per-session memory.
"""
