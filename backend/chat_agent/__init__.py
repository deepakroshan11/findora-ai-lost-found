"""
Findora chat agent — a small tool-calling agent written from scratch.

    llm.py        OpenAI-compatible chat client (plain `requests`, no SDK)
    tools.py      The tools the agent may call + their JSON schemas
    agent.py      The agent loop: LLM -> tool call -> result -> LLM -> ... -> answer
    ratelimit.py  Tiny in-memory sliding-window rate limiter for the endpoint
"""
