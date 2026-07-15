from pydantic import BaseModel, Field
from typing import Any

from hiddifypanel.models.custom_proxy import TemplateCore
from hiddifypanel.models.proxy_base_config import BaseConfigSide


class MessageModel(BaseModel):
    level: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class RenderErrorDetail(BaseModel):
    phase: str
    line: int | None = None
    column: int | None = None
    message: str
    source: str = ""
    excerpt: str = ""
    template_source: str | None = None
    template_excerpt: str | None = None
    label: str | None = None


class RenderSectionResult(BaseModel):
    rendered: str = ""
    parsed: Any | None = None
    skipped: bool = False
    error: str | None = None
    error_detail: RenderErrorDetail | None = None


class ConfigBuilderModel(BaseModel):
    core: TemplateCore
    side: BaseConfigSide
    config: str
    messages: list[MessageModel] = Field(default_factory=list)


class ProxyBlock(BaseModel):
    block_name: str
    content: str

    messages: list[MessageModel] = Field(default_factory=list)
    extracted_tags: list[str] = Field(default_factory=list)
