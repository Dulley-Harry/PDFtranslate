from __future__ import annotations

import json
import unittest
import urllib.error
import urllib.request

from pdftranslate.bridge import BridgeError
from pdftranslate.bridge import TranslationJob
from pdftranslate.bridge import build_batch_prompt
from pdftranslate.bridge import build_batch_schema
from pdftranslate.bridge import parse_batch_output
from pdftranslate.bridge import start_bridge


class FakeBatcher:
    def __init__(self, result: str = "测试译文") -> None:
        self.result = result
        self.calls: list[tuple[list[dict], str]] = []

    def submit(self, messages: list[dict], model: str) -> str:
        self.calls.append((messages, model))
        return self.result

    def status(self) -> dict:
        return {"backend": "fake", "translated_items": len(self.calls)}


class BatchContractTests(unittest.TestCase):
    def test_schema_requires_translation_rows(self) -> None:
        schema = build_batch_schema()
        self.assertIn("translations", schema["properties"])
        self.assertEqual(schema["required"], ["translations"])

    def test_prompt_contains_all_job_ids_and_injection_boundary(self) -> None:
        jobs = [
            TranslationJob(messages=[{"role": "user", "content": "Input:\n\nA"}], requested_model="codex-cli", id="a"),
            TranslationJob(messages=[{"role": "user", "content": "Input:\n\nB"}], requested_model="codex-cli", id="b"),
        ]
        prompt = build_batch_prompt(jobs)
        self.assertIn('"id":"a"', prompt)
        self.assertIn('"id":"b"', prompt)
        self.assertIn("untrusted source material", prompt)
        self.assertIn("Do not use tools or web search", prompt)

    def test_batch_output_is_keyed_back_to_jobs(self) -> None:
        jobs = [
            TranslationJob(messages=[{"role": "user", "content": "A"}], requested_model="codex-cli", id="a"),
            TranslationJob(messages=[{"role": "user", "content": "B"}], requested_model="codex-cli", id="b"),
        ]
        result = parse_batch_output(
            json.dumps(
                {"translations": [{"id": "b", "text": "乙"}, {"id": "a", "text": "甲"}]},
                ensure_ascii=False,
            ),
            jobs,
        )
        self.assertEqual(result, {"a": "甲", "b": "乙"})

    def test_batch_output_rejects_missing_job(self) -> None:
        jobs = [
            TranslationJob(messages=[{"role": "user", "content": "A"}], requested_model="codex-cli", id="a"),
            TranslationJob(messages=[{"role": "user", "content": "B"}], requested_model="codex-cli", id="b"),
        ]
        with self.assertRaises(BridgeError):
            parse_batch_output('{"translations":[{"id":"a","text":"甲"}]}', jobs)


class BridgeHTTPTests(unittest.TestCase):
    def test_chat_completions_endpoint(self) -> None:
        fake = FakeBatcher("翻译完成")
        with start_bridge(batcher=fake, api_key="test-token") as bridge:
            payload = json.dumps(
                {"model": "codex-cli", "messages": [{"role": "user", "content": "hello"}]}
            ).encode("utf-8")
            request = urllib.request.Request(
                bridge.base_url + "/chat/completions",
                data=payload,
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8"))

        self.assertEqual(body["choices"][0]["message"]["content"], "翻译完成")
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0][1], "codex-cli")

    def test_api_requires_local_bearer_token(self) -> None:
        fake = FakeBatcher()
        with start_bridge(batcher=fake, api_key="secret") as bridge:
            request = urllib.request.Request(
                bridge.base_url + "/models",
                headers={"Authorization": "Bearer wrong"},
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request, timeout=5)
            self.assertEqual(caught.exception.code, 401)

    def test_health_does_not_require_secret(self) -> None:
        fake = FakeBatcher()
        with start_bridge(batcher=fake, api_key="secret") as bridge:
            url = f"http://{bridge.host}:{bridge.port}/health"
            with urllib.request.urlopen(url, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8"))
            self.assertEqual(body["status"], "ok")
            self.assertEqual(body["backend"], "fake")

    def test_non_loopback_bind_is_rejected(self) -> None:
        with self.assertRaises(BridgeError):
            start_bridge(host="0.0.0.0", batcher=FakeBatcher())


if __name__ == "__main__":
    unittest.main()
