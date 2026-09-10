from __future__ import annotations

from pydantic import Field

from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel


class PanelInfoOutputSchema(ApiModel):
    version: str = Field("", description="The panel version")


class PongOutputSchema(ApiModel):
    msg: str = Field("", description="Pong Response")
