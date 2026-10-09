"""Ask Khidki: a Strands agent on Amazon Bedrock that explains, never decides.

The agent can only read and simulate (tools.py). Every number in its answer must come from a tool output
(guard.py), or the answer is replaced by a deterministic template built from the same tool outputs, and the
response says so. If Bedrock is unavailable, the template answers alone. The product never depends on the LLM.
"""
