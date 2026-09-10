from __future__ import annotations

import traceback
from typing import TypeVar

import requests
from loguru import logger
from pydantic import BaseModel

from hiddifypanel.models import ConfigEnum, hconfig

T = TypeVar("T")


class NodeApiErrorSchema(BaseModel):
    msg: str
    stacktrace: str = ""
    code: int = 0
    reason: str = ""


def _dump_payload(payload: BaseModel) -> dict:
    return payload.model_dump(mode="json")


def _load_output(output_schema: type[T], data: object) -> T:
    if isinstance(data, BaseModel):
        return data  # type: ignore
    if isinstance(output_schema, type) and issubclass(output_schema, BaseModel):
        return output_schema.model_validate(data)  # type: ignore
    raise TypeError(f"Unsupported output schema type: {output_schema!r}")


class NodeApiClient:
    def __init__(self, base_url: str, apikey: str | None = None, max_retry: int = 3):
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.max_retry = max_retry
        self.headers = {"Hiddify-API-Key": apikey or hconfig(ConfigEnum.unique_id)}

    def __call(self, method: str, path: str, payload: BaseModel | None, output_schema: type[T]) -> T | NodeApiErrorSchema:
        retry_count = 1
        full_url = self.base_url + path.removeprefix("/")
        response: requests.Response | None = None
        while True:
            try:
                logger.trace(f"Attempting {method} request to node at {full_url}")

                if payload is not None:
                    response = requests.request(method, full_url, json=_dump_payload(payload), headers=self.headers)
                else:
                    response = requests.request(method, full_url, headers=self.headers)

                response.raise_for_status()
                resp = response.json()
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
                return _load_output(output_schema, resp)

            except requests.HTTPError as e:
                status_code = response.status_code if response is not None else 0
                reason = (response.reason or "") if response is not None else ""
                if retry_count >= self.max_retry:
                    stack_trace = traceback.format_exc()
                    err = NodeApiErrorSchema(
                        msg=str(e),
                        stacktrace=stack_trace,
                        code=status_code,
                        reason=reason,
                    )
                    with logger.contextualize(status_code=err.code, reason=err.reason, stack_trace=stack_trace, payload=payload):
                        logger.error(f"HTTP error after {self.max_retry} retries")
                        logger.exception(e)
                    return err

                logger.warning(f"Error occurred: {e} from {full_url} with method {method}, retrying... ({retry_count}/{self.max_retry})")
                retry_count += 1

    def get(self, path: str, output: type[T]) -> T | NodeApiErrorSchema:
        return self.__call("GET", path, None, output)

    def post(self, path: str, payload: BaseModel | None, output: type[T]) -> T | NodeApiErrorSchema:
        return self.__call("POST", path, payload, output)

    def put(self, path: str, payload: BaseModel | None, output: type[T]) -> T | NodeApiErrorSchema:
        return self.__call("PUT", path, payload, output)
