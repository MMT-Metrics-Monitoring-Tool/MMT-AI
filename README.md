# MMT-AI

## Description

This project contains a prototype implementation of an MMT RAG chatbot system which uses project data as context.\\
This Markdown briefly explains development-relevant matters, with more information in the related thesis.\\
Currently, the RAG implementation using project data for generation is WIP, having been designed as a part of an M.Sc. (Tech) thesis. The implementation was left underway due to deficiencies in available hardware for utilizing the LLM with context from project data.

## DB Agent

A DB agent should be implemented to provide SQL data retrieval for RAG on demand. The current implementation includes all project data as a part of the system prompt. This causes extraneous data to be fed into the LLM. When this is implemented, the in-memory session storage can be simplified, with no requirement for manually saving the Runner objects any more.

The query analysis should route the user query to the DB agent when data from the user's project is required as context to answer the query. The agent should be provided with tools which execute and format the output of specific SQL queries. See for example LangChain Tools for this.

## Misc.

- Automated session clean-up from related data structures to allow production use.
- UI button to stop answer generation + Indicator of message processing (UX on LLM delays etc.).
- Expand and improve the retrieved project data + formatting.
- Expand vector store retrieval with PDF documents + integrate with MMT to allow saving course documents as context? (Briefly discussed spring 2025.)
- Hallucination grader.
