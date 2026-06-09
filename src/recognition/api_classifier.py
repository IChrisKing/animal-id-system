"""API 分类器 — DeepSeek/Claude API (Layer 2)"""

import asyncio
import json
import re
import time
from dataclasses import dataclass

import httpx

from src.utils.exceptions import (
    APIClassificationError,
    APIConnectionError,
    APITimeoutError,
    ClassificationParseError,
)


@dataclass
class ClassificationResult:
    class_name: str              # 'cat' | 'weasel' | 'bird' | 'other'
    confidence: float            # 0.0 ~ 1.0
    color: str = ""              # 颜色/花纹描述
    distinguishing_features: str = ""  # 显著特征描述


CLASSIFICATION_PROMPT = """你是一个野生动物识别专家。请仔细观察这张动物图片，判断它属于以下哪一类：
- cat (猫，包括家猫、野猫、各种毛色的猫)
- weasel (黄鼠狼，包括黄鼬、白鼬、雪貂等鼬科动物)
- bird (鸟，包括各种常见的鸟类)
- other (其他动物，不属于以上三类)

请以 JSON 格式返回，只返回 JSON 不要其他内容：
{"class": "cat", "confidence": 0.95, "color": "橘色虎斑", "distinguishing_features": "耳朵尖端有小缺口"}

注意 color 和 distinguishing_features 请用中文描述，这对后续个体识别很重要。"""


class APIClassifier:
    """多模态 LLM API 分类器，含缓存、重试、降级"""

    def __init__(
        self,
        provider: str = "deepseek",
        api_key: str = "",
        base_url: str = "https://api.deepseek.com/v1/chat/completions",
        model: str = "deepseek-chat",
        timeout: float = 10.0,
        max_retries: int = 3,
        temperature: float = 0.1,
    ):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature
        # 内存缓存: crop_hash → ClassificationResult
        self._cache: dict[str, ClassificationResult] = {}

    @property
    def cache_hits(self) -> int:
        return getattr(self, '_cache_hits', 0)

    @property
    def api_calls(self) -> int:
        return getattr(self, '_api_calls', 0)

    def classify_sync(self, crop_base64: str, crop_hash: str) -> ClassificationResult:
        """同步包装器 — 内部调用 async"""
        return asyncio.run(self.classify(crop_base64, crop_hash))

    async def classify(self, crop_base64: str, crop_hash: str) -> ClassificationResult:
        """
        分类单个动物裁剪区域。
        缓存命中 → 直接返回；否则调 API，失败则重试。
        """
        # 缓存检查
        if crop_hash in self._cache:
            if not hasattr(self, '_cache_hits'):
                self._cache_hits = 0
            self._cache_hits += 1
            return self._cache[crop_hash]

        if not hasattr(self, '_api_calls'):
            self._api_calls = 0

        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = await self._call_api(crop_base64)
                self._cache[crop_hash] = result
                self._api_calls += 1
                return result
            except (APIConnectionError, APITimeoutError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt  # 1s → 2s → 4s
                    await asyncio.sleep(wait)
            except ClassificationParseError:
                # 解析失败：重试（让 LLM 重新生成）
                last_error = ClassificationParseError("JSON 解析失败")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)

        raise APIClassificationError(
            f"API 分类失败 (重试 {self.max_retries} 次): {last_error}"
        )

    async def _call_api(self, crop_base64: str) -> ClassificationResult:
        """调用 LLM API"""
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{crop_base64}"},
                },
                {"type": "text", "text": CLASSIFICATION_PROMPT},
            ],
        }]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 300,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)

            if response.status_code == 401 or response.status_code == 403:
                raise APIConnectionError(f"API Key 无效 (HTTP {response.status_code})")
            if response.status_code == 429:
                raise APITimeoutError("API 频率限制 (429)")
            if response.status_code != 200:
                raise APIConnectionError(f"API 返回 HTTP {response.status_code}: {response.text[:200]}")

            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]
            return self._parse_response(raw_text)

        except httpx.TimeoutException:
            raise APITimeoutError(f"API 请求超时 ({self.timeout}s)")
        except httpx.ConnectError as e:
            raise APIConnectionError(f"无法连接 API: {e}")
        except (APIConnectionError, APITimeoutError, ClassificationParseError):
            raise
        except Exception as e:
            raise APIConnectionError(f"API 请求异常: {e}")

    def _parse_response(self, raw_text: str) -> ClassificationResult:
        """解析 LLM 返回的 JSON"""
        # 尝试提取 JSON（处理 markdown code block 包裹情况）
        # 1. 直接解析
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            # 2. 提取 ```json ... ``` 中的内容
            match = re.search(r'```(?:json)?\s*\n?(\{.*?\})\s*\n?```', raw_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    # 3. 提取第一个 { ... }
                    match2 = re.search(r'\{[^{}]*\}', raw_text)
                    if match2:
                        try:
                            data = json.loads(match2.group())
                        except json.JSONDecodeError:
                            raise ClassificationParseError(f"无法解析 JSON: {raw_text[:100]}")
                    else:
                        raise ClassificationParseError(f"响应中未找到 JSON: {raw_text[:100]}")
            else:
                match2 = re.search(r'\{[^{}]*\}', raw_text)
                if match2:
                    try:
                        data = json.loads(match2.group())
                    except json.JSONDecodeError:
                        raise ClassificationParseError(f"无法解析 JSON: {raw_text[:100]}")
                else:
                    raise ClassificationParseError(f"响应中未找到 JSON: {raw_text[:100]}")

        class_name = data.get("class", "other")
        if class_name not in ("cat", "weasel", "bird", "other"):
            class_name = "other"

        return ClassificationResult(
            class_name=class_name,
            confidence=float(data.get("confidence", 0.5)),
            color=str(data.get("color", "")),
            distinguishing_features=str(data.get("distinguishing_features", "")),
        )
