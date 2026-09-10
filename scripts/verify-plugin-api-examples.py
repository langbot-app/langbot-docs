"""Run the API documentation snippets with the installed SDK and a mock Host.

Usage: python scripts/verify-plugin-api-examples.py
This checks SDK calls and result shapes, not external platform delivery.
"""

from __future__ import annotations

import asyncio
import ast
import inspect
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from langbot_plugin.api.entities.builtin.runner.context import RunnerContext
from langbot_plugin.api.entities.builtin.runner.errors import (
    AgentAPIError,
    AgentAPIException,
)
from langbot_plugin.api.proxies.runner import RunnerAPIProxy
from langbot_plugin.api.proxies.langbot_api import LangBotAPIProxy
from langbot_plugin.api.entities.builtin.provider.message import Message

ROOT = Path(__file__).resolve().parents[1]


class Host:
    def __init__(self):
        self.calls = []

    async def call_action(self, action, data, timeout=15):
        name = action.value
        self.calls.append((name, data))
        responses = {
            "invoke_llm": {
                "message": {"role": "assistant", "content": "Hello!"},
                "usage": {"total_tokens": 8},
            },
            "invoke_rerank": {"results": [{"index": 0, "relevance_score": 0.9}]},
            "list_parsers": {
                "parsers": [{"plugin_author": "demo", "plugin_name": "Parser"}]
            },
            "invoke_parser": {"text": "guide", "sections": [], "metadata": {}},
            "vector_list": {
                "items": [{"id": "chunk", "document": "guide", "metadata": {}}],
                "total": 1,
            },
            "list_plugins_manifest": {"plugins": []},
            "list_commands": {"commands": []},
            "call_platform_api": {"result": {"id": "123456", "name": "Example"}},
            "call_tool": {"result": {"id": "alice"}},
            "reply_stream": {"result": {"ok": True, "mock": True}},
            "history_page": {
                "items": [],
                "has_more": not data.get("before_cursor"),
                "prev_cursor": "older",
                "next_cursor": None,
            },
            "state_set": {"success": True},
            "state_get": {"value": "setup"},
        }
        if name not in responses:
            raise AssertionError(f"Unexpected Host action: {name}")
        return responses[name]

    async def call_action_generator(self, action, data, timeout=15):
        assert action.value == "invoke_llm_stream"
        yield {"chunk": {"role": "assistant", "content": "Hello", "is_final": False}}
        yield {"chunk": {"role": "assistant", "content": "!", "is_final": True}}
        yield {"usage": {"total_tokens": 8}}


def context():
    return RunnerContext.model_validate(
        {
            "run_id": "docs-run",
            "trigger": {"type": "user_message"},
            "event": {
                "event_id": "docs-event",
                "event_type": "message.received",
                "source": "test",
            },
            "input": {"content": "Hello"},
            "delivery": {"surface": "test"},
            "runtime": {},
            "resources": {
                "models": [{"model_id": "model"}],
                "tools": [
                    {"tool_name": "event_get_actor"},
                    {"tool_name": "event_reply"},
                ],
            },
            "context": {
                "available_apis": {
                    "history_page": True,
                    "state": True,
                    "reply_stream": True,
                }
            },
        }
    )


def snippets(locale, page):
    source = (ROOT / locale / f"plugin/dev/apis/{page}.mdx").read_text()
    if page == "common":
        headings = {
            "zh": ("### 模型流式输出与用量", "## 其他资源 API"),
            "en": ("### Model streaming and usage", "## Additional resource APIs"),
            "ja": ("### モデルのストリーミングと使用量", "## その他のリソース API"),
        }[locale]
        start = source.index(headings[0])
        end = source.index("\n### ", start + len(headings[0]))
        source = source[start:end] + source[source.index(headings[1]) :]
    return re.findall(r"^```python\n(.*?)^```", source, re.M | re.S)


async def execute(block, namespace):
    # Examples are function bodies; signature reference blocks may include stubs.
    function = "async def example():\n" + "\n".join(
        "    " + line for line in block.splitlines()
    )
    tree = ast.parse(function)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = ast.unparse(node.func.value)
        cls = (
            LangBotAPIProxy
            if owner == "self.plugin"
            else RunnerAPIProxy
            if owner == "api"
            else None
        )
        if cls is not None:
            signature = inspect.signature(getattr(cls, node.func.attr))
            signature.bind(
                None,
                *([None] * len(node.args)),
                **{kw.arg: None for kw in node.keywords},
            )
    exec(compile(tree, "plugin-api-doc-example", "exec"), namespace)
    await namespace["example"]()


async def main():
    total = 0
    for page in ("common", "agent-run", "platform"):
        blocks = snippets("zh", page)
        for locale in ("en", "ja"):
            assert blocks == snippets(locale, page), f"{page}: {locale} code differs"
        for block in blocks:
            host = Host()
            api = RunnerAPIProxy(context(), host)
            ctx = SimpleNamespace(api=api, log=AsyncMock())
            namespace = {
                "Any": Any,
                "Message": Message,
                "api": api,
                "ctx": ctx,
                "self": SimpleNamespace(
                    plugin=LangBotAPIProxy(host), get_run_api=lambda _: api
                ),
                "model_uuid": "model",
                "rerank_model_uuid": "model",
                "collection_id": "collection",
                "storage_path": "files/guide.pdf",
                "bot_uuid": "bot",
                "print": lambda *args: None,
            }
            await execute(block, namespace)
            if "reply.update" in block:
                ops = [
                    data["operation"]
                    for name, data in host.calls
                    if name == "reply_stream"
                ]
                assert ops == ["update", "update", "finish"], ops
            if "older =" in block:
                pages = [data for name, data in host.calls if name == "history_page"]
                assert len(pages) == 2 and pages[1]["before_cursor"] == "older"
            if "except PermissionDeniedError" in block:
                # Exercise both documented error handlers with the real SDK proxy.
                api._allowed_tool_names = frozenset()
                await execute(block, namespace)
                ctx.log.assert_awaited()
                api._allowed_tool_names = frozenset({"event_get_actor"})
                host.call_action = AsyncMock(
                    side_effect=AgentAPIException(
                        AgentAPIError(
                            code="host.action_error", message="Failed", retryable=False
                        )
                    )
                )
                await execute(block, namespace)
                assert ctx.log.await_count == 2
            total += 1
    print(
        f"{total} API examples passed; all three locales have identical code. Host delivery is mocked."
    )


if __name__ == "__main__":
    asyncio.run(main())
