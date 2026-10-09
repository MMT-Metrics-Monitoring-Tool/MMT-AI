# MMT-AI

This is an LLM module for Metrics Monitoring Tool (MMT).\
For the main MMT project, see https://github.com/MMT-Metrics-Monitoring-Tool/MMT.

## Description

This project contains a chatbot that answers questions about the user's software project and the COMP.SE.610 course.\
Each question is answered with a single LLM call: the backend puts the full course pages, the upcoming course dates (extracted in code) and the user's current MMT project data into the prompt.\
See [backend/README.md](backend/README.md) for the architecture, API, token contract with MMT, tests and evals.

## Misc.

- UI button to stop answer generation.
- Expand and improve the retrieved project data + formatting (member names, members without logged hours).
- Grow the evaluation set (`backend/evals/`) from real questions and negative feedback.
- Integrate with MMT to allow saving course documents as context? (Briefly discussed spring 2025.)
