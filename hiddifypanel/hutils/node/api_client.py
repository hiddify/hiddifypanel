from __future__ import annotations

import time
import traceback
from typing import TypeVar
from urllib.parse import urlparse

import requests
from loguru import logger
from pydantic import BaseModel

from hiddifypanel.models import ConfigEnum, hconfig

from . import endpoints

T = TypeVar("T")


class NodeApiErrorSchema(BaseModel):
    msg: str
    stacktrace: str = ""
    code: int = 0
    reason: str = ""


#: A web server or CDN in front of the panel answers these when the panel behind it is not there for a moment (it restarts after applying
#: configs, a worker is replaced, ...): "origin web server returned an invalid or incomplete response" is Cloudflare's 520. Asking again a
#: little later works; asking another domain of the same panel works at once. (504 and 524 are not here: the panel may still be doing it.)
GATEWAY_STATUSES = frozenset({502, 503, 520, 521, 522, 523, 525, 526, 527, 530})
GATEWAY_RETRIES = 5
#: In the message of an answer that is a page of a CDN or proxy (a challenge, an error page) and not the panel's JSON.
NOT_THE_PANEL = "not JSON"


def _dump_payload(payload: BaseModel) -> dict:
    return payload.model_dump(mode="json")


def _load_output(output_schema: type[T], data: object) -> T:
    if isinstance(data, BaseModel):
        return data  # type: ignore
    if output_schema in (dict, list):
        # Plain JSON objects/arrays (e.g. {"status": 200, "msg": "ok"} from node actions).
        if isinstance(data, output_schema):
            return data  # type: ignore
        raise ValueError(f"expected a JSON {output_schema.__name__}, got {type(data).__name__}")
    if isinstance(output_schema, type) and issubclass(output_schema, BaseModel):
        return output_schema.model_validate(data)  # type: ignore
    raise TypeError(f"Unsupported output schema type: {output_schema!r}")


class NodeApiClient:
    def __init__(self, base_url: str, apikey: str | None = None, max_retry: int = 3, timeout: float = 8, retry_on_timeout: bool = True, extra_headers: dict[str, str] | None = None):
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        # The panel may have several domains: direct first, then relay, then CDN (see endpoints.py).
        self.bases = endpoints.alternates(self.base_url)
        self.max_retry = max_retry
        self.timeout = timeout
        # False for a call that may still be running on the other side when it times out: asking again would run it twice, at once.
        self.retry_on_timeout = retry_on_timeout
        self.headers = {"Hiddify-API-Key": apikey or hconfig(ConfigEnum.unique_id), **(extra_headers or {})}

    def __call(self, method: str, path: str, payload: BaseModel | None, output_schema: type[T]) -> T | NodeApiErrorSchema:
        """Call the panel on its best address; when that address cannot be connected to, on the next one (direct, relay, CDN)."""
        bases = endpoints.live_first(self.bases)
        result: T | NodeApiErrorSchema | None = None
        for i, base in enumerate(bases):
            last = i == len(bases) - 1
            # An address that is not the last one is tried once: another address is faster than asking a dead one again.
            result = self.__call_base(base, method, path, payload, output_schema, self.max_retry if last else 1)
            # Not reachable: no answer at all (a read timeout may still be running there, so it is not this), or a gateway's "the panel is not there".
            unreachable = isinstance(result, NodeApiErrorSchema) and ((result.code == 0 and result.reason != "ReadTimeout") or result.code in GATEWAY_STATUSES or NOT_THE_PANEL in result.msg)
            if not unreachable:
                endpoints.mark_up(base)
                return result
            endpoints.mark_down(base)
            if not last:
                logger.warning(f"{urlparse(base).netloc} could not be connected to ({result.reason}): trying {urlparse(bases[i + 1]).netloc}")  # type: ignore[union-attr]
        assert result is not None
        return result

    def __call_base(self, base: str, method: str, path: str, payload: BaseModel | None, output_schema: type[T], max_retry: int) -> T | NodeApiErrorSchema:
        retry_count = 1
        full_url = base + path.removeprefix("/")
        response: requests.Response | None = None
        while True:
            attempt_started = time.monotonic()
            try:
                logger.trace(f"Attempting {method} request to node at {full_url}")

                if payload is not None:
                    response = requests.request(method, full_url, json=_dump_payload(payload), headers=self.headers, timeout=self.timeout)
                else:
                    response = requests.request(method, full_url, headers=self.headers, timeout=self.timeout)

                response.raise_for_status()
                try:
                    resp = response.json()
                except ValueError:  # a page of the CDN or a proxy instead of the panel's answer
                    logger.warning(f"{urlparse(full_url).netloc} answered {response.status_code} with something that is not JSON")
                    return NodeApiErrorSchema(msg=f"Unexpected response: {NOT_THE_PANEL} ({(response.text or '')[:200]!r})", code=response.status_code, reason="bad_response")
                if not resp:
                    err = NodeApiErrorSchema(
                        msg="Empty response",
                        stacktrace="",
                        code=response.status_code,
                        reason=response.reason or "",
                    )
                    with logger.contextualize(payload=payload):
                        logger.warning(f"Received empty response from {full_url} with method {method}")
                    return err

                logger.trace(f"Successfully received response from {full_url}")
                try:
                    return _load_output(output_schema, resp)
                except (ValueError, TypeError) as e:  # pydantic's ValidationError is a ValueError
                    # A reply of an unexpected shape (e.g. an older node) is an API error, not a crash.
                    logger.error(f"Unexpected response from {full_url}: {e}")
                    return NodeApiErrorSchema(msg=f"Unexpected response: {e}", stacktrace=traceback.format_exc(), code=response.status_code, reason="bad_response")

            except requests.HTTPError as e:
                status_code = response.status_code if response is not None else 0
                reason = (response.reason or "") if response is not None else ""
                body = ""
                if response is not None:
                    try:
                        body = (response.text or "")[:2000]
                    except Exception:
                        body = ""
                gateway = status_code in GATEWAY_STATUSES
                if retry_count >= (max(max_retry, GATEWAY_RETRIES) if gateway and max_retry > 1 else max_retry):
                    stack_trace = traceback.format_exc()
                    msg = str(e)
                    if body:
                        msg = f"{msg} | body={body}"
                    err = NodeApiErrorSchema(
                        msg=msg,
                        stacktrace=stack_trace,
                        code=status_code,
                        reason=reason,
                    )
                    with logger.contextualize(status_code=err.code, reason=err.reason, stack_trace=stack_trace, payload=payload, body=body):
                        logger.error(f"HTTP error after {max_retry} retries")
                        logger.exception(e)
                    return err

                logger.warning(f"Error occurred: {e} from {full_url} with method {method}, retrying... ({retry_count}/{max_retry})")
                if gateway:
                    time.sleep(min(2.0 * retry_count, 10))  # the panel behind the gateway is restarting: give it a moment
                retry_count += 1

            except (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError, requests.exceptions.ContentDecodingError) as e:
                if retry_count >= max_retry or (isinstance(e, requests.ReadTimeout) and not self.retry_on_timeout):
                    err = NodeApiErrorSchema(msg=str(e), stacktrace=traceback.format_exc(), code=0, reason=type(e).__name__)
                    logger.error(f"Node request to {urlparse(full_url).netloc} failed ({type(e).__name__}) after {time.monotonic() - attempt_started:.1f}s on try {retry_count}/{max_retry}: {e}")
                    return err
                logger.warning(f"Timeout/connection error ({type(e).__name__}) after {time.monotonic() - attempt_started:.1f}s from {urlparse(full_url).netloc}, retrying... ({retry_count}/{max_retry})")
                time.sleep(min(1.5 * retry_count, 6))  # a reload of the other side's web server takes a moment
                retry_count += 1

    def get(self, path: str, output: type[T]) -> T | NodeApiErrorSchema:
        return self.__call("GET", path, None, output)

    def post(self, path: str, payload: BaseModel | None, output: type[T]) -> T | NodeApiErrorSchema:
        return self.__call("POST", path, payload, output)

    def put(self, path: str, payload: BaseModel | None, output: type[T]) -> T | NodeApiErrorSchema:
        return self.__call("PUT", path, payload, output)
