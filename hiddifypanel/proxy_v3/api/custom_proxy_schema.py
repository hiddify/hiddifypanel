from apiflask import Schema, fields
from marshmallow import EXCLUDE, ValidationError, pre_load

from hiddifypanel.models import CustomProxyMode, L7Proto, ProxyProto, TemplateCategory, TEMPLATE_CATEGORIES_ACTIVE


class StrEnumField(fields.Field):
    """Accept StrEnum members or their string values (matches model to_dict() output)."""

    def __init__(self, enum_class, **kwargs):
        self.enum_class = enum_class
        self._values = [member.value for member in enum_class]
        super().__init__(**kwargs)

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.value
        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value
        text = str(value)
        if text not in self._values:
            raise ValidationError(f'Must be one of: {", ".join(self._values)}')
        return self.enum_class(text)


class ServerConfigSchema(Schema):
    core = fields.String(metadata={'description': 'Server core: xray, hiddify-core, dnstt'})
    inbound_tcp_ports = fields.List(fields.Integer(), load_default=list)
    inbound_udp_ports = fields.List(fields.Integer(), load_default=list)
    inbound_port = fields.Integer(allow_none=True, load_default=None)
    tag = fields.String(allow_none=True)
    direct_port_access = fields.Boolean(load_default=False)
    template_slugs = fields.List(fields.String())
    inbound_template = fields.String(allow_none=True)

    @pre_load
    def _normalize_legacy_port(self, data, **kwargs):
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if not payload.get('inbound_tcp_ports') and payload.get('inbound_port') is not None:
            payload['inbound_tcp_ports'] = [payload['inbound_port']]
        return payload


class ClientCoreConfigSchema(Schema):
    core = fields.String(required=True)
    version = fields.String(allow_none=True)
    min_version = fields.String(allow_none=True)
    max_version = fields.String(allow_none=True)
    slug = fields.String(allow_none=True)
    is_builtin = fields.Boolean(load_default=False)
    outbounds_template = fields.String(allow_none=True)
    override = fields.Boolean(load_default=False)


class SublinkConfigSchema(Schema):
    core = fields.String(load_default='sublink')
    version = fields.String(allow_none=True)
    outbounds_template = fields.String(allow_none=True)


class ClientConfigSchema(Schema):
    core_configs = fields.List(fields.Nested(ClientCoreConfigSchema), load_default=list)


class CustomProxySchema(Schema):
    id = fields.Integer(dump_only=True)
    child_id = fields.Integer(dump_only=True)
    name = fields.String(required=True)
    slug = fields.String(allow_none=True)
    enable = fields.Boolean(load_default=True)
    mode = StrEnumField(CustomProxyMode, required=True)
    proto = StrEnumField(ProxyProto, allow_none=True, load_default=None)
    l7_proto = StrEnumField(L7Proto, allow_none=True, load_default=None)
    alpns = fields.List(fields.String(), load_default=list)
    download_alpns = fields.List(fields.String(), load_default=list)
    tags = fields.List(fields.String(), load_default=list)
    domain_modes = fields.List(fields.String(), load_default=list)
    custom_path = fields.String(allow_none=True, load_default='')
    domain_ids = fields.List(fields.Integer(), load_default=list)
    server_config = fields.Nested(ServerConfigSchema, load_default=dict)
    client_config = fields.Nested(ClientConfigSchema, load_default=dict)
    sort_order = fields.Integer(load_default=0)
    client_cores = fields.List(fields.String(), dump_only=True)
    server_core = fields.String(dump_only=True)
    is_builtin = fields.Boolean(dump_only=True)
    server_override = fields.Boolean(load_default=False)
    client_override = fields.Boolean(load_default=False)
    builtin = fields.Dict(dump_only=True)
    builtin_overrides = fields.Dict(keys=fields.String(), values=fields.Boolean(), dump_only=True)
    builtin_server_config = fields.String(dump_only=True)
    builtin_client_config = fields.Nested(ClientConfigSchema, dump_only=True)


class PatchCustomProxySchema(Schema):
    name = fields.String()
    slug = fields.String(allow_none=True)
    enable = fields.Boolean()
    mode = StrEnumField(CustomProxyMode)
    proto = StrEnumField(ProxyProto, allow_none=True, load_default=None)
    l7_proto = StrEnumField(L7Proto, allow_none=True, load_default=None)
    alpns = fields.List(fields.String())
    download_alpns = fields.List(fields.String())
    tags = fields.List(fields.String())
    domain_modes = fields.List(fields.String())
    custom_path = fields.String(allow_none=True)
    domain_ids = fields.List(fields.Integer())
    server_config = fields.Nested(ServerConfigSchema)
    client_config = fields.Nested(ClientConfigSchema)
    sort_order = fields.Integer()
    server_override = fields.Boolean()
    client_override = fields.Boolean()
    builtin_overrides = fields.Dict(keys=fields.String(), values=fields.Boolean(), load_default=dict)

class CustomProxyEnableSchema(Schema):
    enable = fields.Boolean(required=True)


class CustomProxyValidateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Integer(allow_none=True)
    mode = StrEnumField(CustomProxyMode, allow_none=True)
    proto = StrEnumField(ProxyProto, allow_none=True)
    slug = fields.String(allow_none=True)
    domain_ids = fields.List(fields.Integer(), load_default=list)
    domain_modes = fields.List(fields.String(), load_default=list)
    server_config = fields.Nested(ServerConfigSchema, load_default=dict)
    client_config = fields.Nested(ClientConfigSchema, load_default=dict)
    server_override = fields.Boolean(load_default=False)
    client_override = fields.Boolean(load_default=False)
    is_builtin = fields.Boolean(load_default=False)
    sections = fields.List(fields.String(), load_default=lambda: ['general', 'server', 'client'])


class RenderErrorDetailSchema(Schema):
    phase = fields.String(allow_none=True)
    line = fields.Integer(allow_none=True)
    column = fields.Integer(allow_none=True)
    message = fields.String(allow_none=True)
    source = fields.String(allow_none=True)
    excerpt = fields.String(allow_none=True)
    template_source = fields.String(allow_none=True)
    template_excerpt = fields.String(allow_none=True)
    label = fields.String(allow_none=True)


class ValidationIssueSchema(Schema):
    code = fields.String()
    message = fields.String()
    detail = fields.Nested(RenderErrorDetailSchema, allow_none=True)


class ValidationResultSchema(Schema):
    ok = fields.Boolean()
    errors = fields.List(fields.Nested(ValidationIssueSchema))
    warnings = fields.List(fields.Nested(ValidationIssueSchema))
    compiled_preview = fields.String()
    compiled_json = fields.Raw(allow_none=True)


class TemplatePreviewParamsSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    domain = fields.String(allow_none=True)
    domain_id = fields.Integer(allow_none=True)
    user_id = fields.Integer(allow_none=True)
    user_uuid = fields.String(allow_none=True)
    ip = fields.String(allow_none=True)
    user_agent = fields.String(allow_none=True)
    ignore_skip = fields.Boolean(load_default=True)


class TemplatePreviewResultSchema(Schema):
    ok = fields.Boolean()
    rendered = fields.String()
    parsed = fields.Raw(allow_none=True)
    skipped = fields.Boolean(load_default=False)
    error = fields.String(allow_none=True)
    error_detail = fields.Nested(RenderErrorDetailSchema, allow_none=True)
    warnings = fields.List(fields.Nested(ValidationIssueSchema), load_default=list)


class CustomProxyPreviewSchema(TemplatePreviewParamsSchema):
    proxy = fields.Nested(CustomProxySchema, required=True)
    proxy_id = fields.Integer(allow_none=True)
    side = fields.String(required=True)
    core = fields.String(required=True)
    template = fields.String(required=True)
    require_user = fields.Boolean(load_default=False)


class BaseConfigPreviewSchema(TemplatePreviewParamsSchema):
    side = fields.String(required=True)
    core = fields.String(required=True)
    version = fields.String(allow_none=True)
    content = fields.String(required=True)


class GeneratedSectionSchema(Schema):
    core = fields.String()
    version = fields.String(allow_none=True)
    label = fields.String(allow_none=True)
    index = fields.Integer(allow_none=True)
    rendered = fields.String()
    parsed = fields.Raw(allow_none=True)
    skipped = fields.Boolean()
    error = fields.String(allow_none=True)
    error_detail = fields.Nested(RenderErrorDetailSchema, allow_none=True)
    auto = fields.Boolean(load_default=False)
    variant_label = fields.String(allow_none=True)
    sublink_formats = fields.Raw(allow_none=True)
    clash_yaml = fields.String(allow_none=True)
    config_yaml = fields.String(allow_none=True)


GeneratedSectionSchema.configs = fields.List(fields.Nested(GeneratedSectionSchema), allow_none=True)


class CustomProxyGenerateExampleSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    custom_proxy_id = fields.Integer(allow_none=True)
    domain = fields.String(allow_none=True)
    domain_id = fields.Integer(allow_none=True)
    user_id = fields.Integer(allow_none=True)
    user_uuid = fields.String(allow_none=True)
    ip = fields.String(allow_none=True)
    user_agent = fields.String(allow_none=True)
    ignore_skip = fields.Boolean(load_default=True)

    @pre_load
    def normalize_custom_proxy_id(self, data, **kwargs):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if data.get('custom_proxy_id') is None and data.get('id') is not None:
            data['custom_proxy_id'] = data['id']
        return data


class CustomProxyGenerateExampleByIdInputSchema(CustomProxyGenerateExampleSchema):
    """Body for POST /custom-proxies/<id>/generate-example/."""

    pass


class CustomProxyGenerateExampleWithIdSchema(CustomProxyGenerateExampleSchema):
    """Body for POST /custom-proxies/generate-example/."""

    custom_proxy_id = fields.Integer(required=True)


class CustomProxyGenerateResultSchema(Schema):
    ok = fields.Boolean()
    errors = fields.List(fields.Nested(ValidationIssueSchema))
    warnings = fields.List(fields.Nested(ValidationIssueSchema))
    context = fields.Dict()
    server = fields.Nested(GeneratedSectionSchema, allow_none=True)
    clients = fields.List(fields.Nested(GeneratedSectionSchema))
    auto_client_cores = fields.List(fields.String(), load_default=list)


class CustomProxyGenerateBundleSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    domain = fields.String(allow_none=True)
    domain_id = fields.Integer(allow_none=True)
    domains = fields.List(fields.String(), allow_none=True)
    domain_ids = fields.List(fields.Integer(), allow_none=True)
    user_id = fields.Integer(allow_none=True)
    user_uuid = fields.String(allow_none=True)
    ip = fields.String(allow_none=True)
    user_agent = fields.String(allow_none=True)


class CustomProxyGenerateBundleResultSchema(Schema):
    ok = fields.Boolean()
    errors = fields.List(fields.Nested(ValidationIssueSchema))
    warnings = fields.List(fields.Nested(ValidationIssueSchema))
    context = fields.Dict()
    servers = fields.List(fields.Nested(GeneratedSectionSchema))
    clients = fields.List(fields.Nested(GeneratedSectionSchema))


class ProxyTemplateSchema(Schema):
    id = fields.Integer(dump_only=True)
    child_id = fields.Integer(dump_only=True)
    slug = fields.String(required=True)
    core = fields.String(required=True)
    category = StrEnumField(TemplateCategory, required=True)
    name = fields.String(required=True)
    description = fields.String(allow_none=True, load_default='')
    content = fields.String(allow_none=True, load_default='')
    is_builtin = fields.Boolean(dump_only=True)
    builtin_override = fields.Boolean(dump_only=True)
    builtin_content = fields.String(dump_only=True)


class PatchProxyTemplateSchema(Schema):
    slug = fields.String()
    core = fields.String()
    category = StrEnumField(TemplateCategory)
    name = fields.String()
    description = fields.String(allow_none=True)
    content = fields.String(allow_none=True)
    builtin_override = fields.Boolean()


class DomainOptionSchema(Schema):
    id = fields.Integer()
    domain = fields.String()
    alias = fields.String(allow_none=True)
    mode = fields.String()


class PostDomainSchema(Schema):
    domain = fields.String(required=True)
    alias = fields.String(allow_none=True)
    mode = fields.String(load_default='direct')


class CustomProxyMetaSchema(Schema):
    modes = fields.List(fields.String())
    protos = fields.List(fields.String())
    alpns = fields.List(fields.String())
    l7_protos = fields.List(fields.String())
    domain_modes = fields.List(fields.String())
    server_cores = fields.List(fields.String())
    client_cores = fields.List(fields.String())
    template_categories = fields.List(fields.String())
    suggested_tags = fields.List(fields.String())
    default_sublink_link = fields.String()
    example_user_agents = fields.List(fields.Dict())


class CustomProxyExportInputSchema(Schema):
    name = fields.String(allow_none=True)
    slug = fields.String(allow_none=True)
    enable = fields.Boolean(allow_none=True)
    mode = StrEnumField(CustomProxyMode, allow_none=True)
    proto = StrEnumField(ProxyProto, allow_none=True, load_default=None)
    l7_proto = StrEnumField(L7Proto, allow_none=True, load_default=None)
    alpns = fields.List(fields.String(), load_default=list)
    download_alpns = fields.List(fields.String(), load_default=list)
    tags = fields.List(fields.String(), load_default=list)
    domain_modes = fields.List(fields.String(), load_default=list)
    custom_path = fields.String(allow_none=True)
    server_config = fields.Nested(ServerConfigSchema, load_default=dict)
    client_config = fields.Nested(ClientConfigSchema, load_default=dict)
    server_override = fields.Boolean(load_default=False)
    client_override = fields.Boolean(load_default=False)
    exclude_builtin_templates = fields.Boolean(load_default=False)


class ProxyBaseConfigExportInputSchema(Schema):
    side = fields.String(allow_none=True)
    core = fields.String(allow_none=True)
    version = fields.String(allow_none=True)
    name = fields.String(allow_none=True)
    description = fields.String(allow_none=True)
    content = fields.String(allow_none=True)
    exclude_builtin_templates = fields.Boolean(load_default=False)


class CustomProxyBundleTemplateSchema(Schema):
    slug = fields.String(required=True)
    core = fields.String(required=True)
    category = StrEnumField(TemplateCategory, required=True)
    name = fields.String(required=True)
    description = fields.String(allow_none=True, load_default='')
    content = fields.String(allow_none=True, load_default='')


class ProxyBaseConfigBundleSchema(Schema):
    version = fields.Integer(load_default=1)
    base_config = fields.Nested(ProxyBaseConfigExportInputSchema, required=True)
    templates = fields.List(fields.Nested(CustomProxyBundleTemplateSchema), load_default=list)


class ProxyBaseConfigImportResultSchema(Schema):
    base_config = fields.Nested(ProxyBaseConfigExportInputSchema)
    slug_map = fields.Dict(keys=fields.String(), values=fields.String())
    templates_imported = fields.Integer()


class CustomProxyImportSchema(Schema):
    version = fields.Integer(load_default=1)
    proxy = fields.Nested(CustomProxyExportInputSchema, required=True)
    templates = fields.List(fields.Nested(CustomProxyBundleTemplateSchema), load_default=list)


class CustomProxyImportResultSchema(Schema):
    proxy = fields.Nested(CustomProxyExportInputSchema)
    slug_map = fields.Dict(keys=fields.String(), values=fields.String())
    templates_imported = fields.Integer()


class ProxyBaseConfigSchema(Schema):
    id = fields.Integer(dump_only=True)
    child_id = fields.Integer(dump_only=True)
    side = fields.String(required=True)
    core = fields.String(required=True)
    version = fields.String(load_default='1.0.0')
    name = fields.String(required=True)
    description = fields.String(allow_none=True, load_default='')
    content = fields.String(allow_none=True, load_default='')
    is_builtin = fields.Boolean(dump_only=True)
    enable = fields.Boolean(load_default=True)
    builtin_override = fields.Boolean(dump_only=True)
    builtin_content = fields.String(dump_only=True)


class PatchProxyBaseConfigSchema(Schema):
    side = fields.String()
    core = fields.String()
    version = fields.String()
    name = fields.String()
    description = fields.String(allow_none=True)
    content = fields.String(allow_none=True)
    enable = fields.Boolean()
    builtin_override = fields.Boolean()


class ProxyBaseConfigMetaSchema(Schema):
    sides = fields.List(fields.String())
    cores_by_side = fields.Dict(keys=fields.String(), values=fields.List(fields.String()))
    template_category = fields.String()


class TemplateVariableSchema(Schema):
    category = fields.String()
    category_label = fields.String(required=False)
    name = fields.String()
    access = fields.String()
    access_bracket = fields.String(required=False)
    value = fields.Raw(allow_none=True)
    label = fields.String()
    description = fields.String()


class TemplateVariableGroupSchema(Schema):
    id = fields.String()
    label = fields.String()
    variables = fields.List(fields.Nested(TemplateVariableSchema))


class TemplateVariablesSchema(Schema):
    groups = fields.List(fields.Nested(TemplateVariableGroupSchema))
    variables = fields.List(fields.Nested(TemplateVariableSchema), load_default=list)


class TemplateVariableGroupsSchema(Schema):
    groups = fields.List(fields.Nested(TemplateVariableGroupSchema))
