from flask import g, request
from flask.views import MethodView
from apiflask import abort
from flask import current_app as app
from sqlalchemy.exc import IntegrityError

from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models import (
    BaseConfigSide,
    BASE_CONFIG_MATRIX,
    ProxyBaseConfig,
    TemplateCategory,
    default_base_content,
    seed_proxy_base_configs,
)
from hiddifypanel.models.role import Role
from hiddifypanel.hutils.proxy.custom_proxy_validate import validate_base_config_content

from .custom_proxy_schema import (
    ProxyBaseConfigSchema,
    PatchProxyBaseConfigSchema,
    ProxyBaseConfigMetaSchema,
    ProxyBaseConfigExportInputSchema,
    ProxyBaseConfigBundleSchema,
    ProxyBaseConfigImportResultSchema,
)


def _child_id() -> int:
    return g.child.id if g.child else 0


def _get_base_config_or_404(config_id: int) -> ProxyBaseConfig:
    row = ProxyBaseConfig.query.filter(
        ProxyBaseConfig.id == config_id,
        (ProxyBaseConfig.child_id == _child_id()) | (ProxyBaseConfig.child_id == 0),
    ).first()
    if not row:
        abort(404, 'Base config not found')
    return row


def _validate_side_core(side: str, core: str) -> None:
    allowed = BASE_CONFIG_MATRIX.get(side)
    if not allowed or core not in allowed:
        abort(400, f'Invalid side/core combination: {side}/{core}')


class ProxyBaseConfigsApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(list[ProxyBaseConfigSchema])  # type: ignore
    def get(self):
        side = request.args.get('side')
        core = request.args.get('core')
        q = ProxyBaseConfig.query.filter(
            (ProxyBaseConfig.child_id == _child_id()) | (ProxyBaseConfig.child_id == 0)
        )
        if side:
            try:
                q = q.filter(ProxyBaseConfig.side == BaseConfigSide(side))
            except ValueError:
                abort(400, 'Invalid side')
        if core:
            q = q.filter(ProxyBaseConfig.core == core)
        rows = q.order_by(
            ProxyBaseConfig.side,
            ProxyBaseConfig.core,
            ProxyBaseConfig.version,
        ).all()
        return [r.to_dict() for r in rows]

    @app.input(ProxyBaseConfigSchema, arg_name='data')  # type: ignore
    @app.output(ProxyBaseConfigSchema)  # type: ignore
    def post(self, data):
        data = dict(data)
        child_id = _child_id()
        side = data['side']
        core = data['core']
        _validate_side_core(side, core)
        version = (data.get('version') or '1.0.0').strip() or '1.0.0'
        data['version'] = version
        if not (data.get('content') or '').strip():
            data['content'] = default_base_content(side, core)
        try:
            row = ProxyBaseConfig.add_or_update(child_id=child_id, **data)
        except ValueError as e:
            abort(409, str(e))
        except IntegrityError:
            db.session.rollback()
            abort(409, 'A base config with this side/core/version already exists')
        return row.to_dict()


class ProxyBaseConfigApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(ProxyBaseConfigSchema)  # type: ignore
    def get(self, config_id: int):
        return _get_base_config_or_404(config_id).to_dict()

    @app.input(PatchProxyBaseConfigSchema, arg_name='data')  # type: ignore
    @app.output(ProxyBaseConfigSchema)  # type: ignore
    def patch(self, config_id: int, data):
        row = _get_base_config_or_404(config_id)
        merged = row.to_dict()
        merged.update(data or {})
        merged['id'] = config_id
        if not row.is_builtin:
            side = merged.get('side', row.side.value)
            core = merged.get('core', row.core)
            _validate_side_core(side, core)
        try:
            updated = ProxyBaseConfig.add_or_update(child_id=row.child_id, **merged)
        except ValueError as e:
            abort(409, str(e))
        except IntegrityError:
            db.session.rollback()
            abort(409, 'A base config with this side/core/version already exists')
        return updated.to_dict()

    def delete(self, config_id: int):
        row = _get_base_config_or_404(config_id)
        if row.is_builtin:
            abort(400, 'Cannot delete built-in base config')
        db.session.delete(row)
        db.session.commit()
        return '', 204


class ProxyBaseConfigDuplicateApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(ProxyBaseConfigSchema)  # type: ignore
    def post(self, config_id: int):
        row = _get_base_config_or_404(config_id)
        try:
            dup = row.duplicate(child_id=_child_id())
        except IntegrityError:
            db.session.rollback()
            abort(409, 'Could not duplicate base config')
        return dup.to_dict()


class ProxyBaseConfigMetaApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(ProxyBaseConfigMetaSchema)  # type: ignore
    def get(self):
        seed_proxy_base_configs(_child_id(), refresh_builtin=True)
        return {
            'sides': [s.value for s in BaseConfigSide],
            'cores_by_side': BASE_CONFIG_MATRIX,
            'template_category': TemplateCategory.base_config.value,
        }


class ProxyBaseConfigValidateApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(ProxyBaseConfigSchema, arg_name='data')  # type: ignore
    def post(self, data):
        return validate_base_config_content(dict(data), child_id=_child_id())


class ProxyBaseConfigExportApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(ProxyBaseConfigExportInputSchema, arg_name='data')  # type: ignore
    def post(self, data):
        from hiddifypanel.hutils.proxy.custom_proxy_bundle import build_base_config_export_bundle
        exclude_builtin = bool(data.pop('exclude_builtin_templates', False))
        return build_base_config_export_bundle(data, _child_id(), exclude_builtin=exclude_builtin)


class ProxyBaseConfigImportApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.input(ProxyBaseConfigBundleSchema, arg_name='data')  # type: ignore
    @app.output(ProxyBaseConfigImportResultSchema)  # type: ignore
    def post(self, data):
        from hiddifypanel.hutils.proxy.custom_proxy_bundle import import_base_config_bundle
        return import_base_config_bundle(data, _child_id())
