from apiflask import Schema, fields
# region info


class PanelInfoOutputSchema(Schema):
    version = fields.String( metadata={"description": "The panel version"})
# endregion


class PongOutputSchema(Schema):
    msg = fields.String( metadata={"description": "Pong Response"})
# endregion
