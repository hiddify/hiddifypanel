from apiflask import Schema, fields


class RegisterWithParentInputSchema(Schema):
    parent_panel = fields.String(required=True,  metadata={"description": "The parent panel url"})
    name = fields.String(required=True,  metadata={"description": "The child's name in the parent panel"})
    apikey = fields.String( metadata={"description": "The parent's apikey"})
