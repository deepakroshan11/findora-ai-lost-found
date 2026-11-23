"""Test helpers: a scripted stand-in for the LLM so agent tests are deterministic."""
import copy
import json


class ScriptedLLM:
    """Replays pre-written assistant messages and records every request it receives."""

    configured = True

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []          # deep copies of the `messages` sent each turn

    def chat(self, messages, tools=None):
        self.requests.append(copy.deepcopy(messages))
        if not self.replies:
            raise AssertionError("ScriptedLLM ran out of replies")
        return self.replies.pop(0)


def say(text):
    """An assistant message with a final text answer."""
    return {"role": "assistant", "content": text}


def call(name, args, call_id="call_1"):
    """An assistant message asking for one tool call."""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)},
        }],
    }
