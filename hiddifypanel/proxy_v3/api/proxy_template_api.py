from flask import g
from flask.views import MethodView
from apiflask import abort
from flask import current_app as app
from sqlalchemy.exc import IntegrityError

from hiddifypanel.auth import login_required
from hiddifypanel.models import ProxyTemplate, TemplateCategory
from hiddifypanel.models.role import Role
from hiddifypanel.database import db

from .schemas import PatchProxyTemplateIn, ProxyTemplateIn, ProxyTemplateOut


def _child_id() -> int:
    return g.child.id if g.child else 0


def _slug_taken(slug: str, child_id: int, exclude_id: int | None = None) -> bool:
    q = ProxyTemplate.query.filter(
        ProxyTemplate.slug == slug,
        ProxyTemplate.child_id == child_id,
    )
    if exclude_id is not None:
        q = q.filter(ProxyTemplate.id != exclude_id)
    return q.first() is not None


def _allocate_unique_slug(base_slug: str, child_id: int, exclude_id: int | None = None) -> str:
    if not _slug_taken(base_slug, child_id, exclude_id):
        return base_slug
    i = 2
    while _slug_taken(f'{base_slug}-{i}', child_id, exclude_id):
        i += 1
    return f'{base_slug}-{i}'


def _category_server_part(category) -> str:
    value = category.value if isinstance(category, TemplateCategory) else str(category)
    return value.replace('server_', '', 1).replace('client_', '', 1)


def _slug_from_name(core: str, category, name: str) -> str:
    import re
    value = category.value if isinstance(category, TemplateCategory) else str(category)
    tail = re.sub(r'[^a-zA-Z0-9_-]+', '-', (name or '').strip().lower()).strip('-') or 'template'
    if value == TemplateCategory.base_config.value:
        return f'base/{core}/{tail}'
    server = _category_server_part(category)
    return f'{core}/{server}/{tail}'


def _get_template_or_404(template_id: int) -> ProxyTemplate:
    tpl = ProxyTemplate.query.filter(
        ProxyTemplate.id == template_id,
        (ProxyTemplate.child_id == _child_id()) | (ProxyTemplate.child_id == 0),
    ).first()
    if not tpl:
        abort(404, 'Template not found')
    return tpl


def _template_out(row: ProxyTemplate) -> ProxyTemplateOut:
    return ProxyTemplateOut.model_validate(row.to_dict())


class ProxyTemplatesApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(list[ProxyTemplateOut])  # type: ignore
    def get(self):
        from hiddifypanel.proxy_v3.builtin_proxy_sync import sync_templates

        sync_templates(_child_id())
        from flask import request
        core = request.args.get('core')
        category = request.args.get('category')
        q = ProxyTemplate.query.filter(
            (ProxyTemplate.child_id == _child_id()) | (ProxyTemplate.child_id == 0)
        )
        if core:
            q = q.filter(ProxyTemplate.core == core)
        if category:
            try:
                q = q.filter(ProxyTemplate.category == TemplateCategory(category))
            except ValueError:
                abort(400, 'Invalid category')
        templates = q.order_by(ProxyTemplate.core, ProxyTemplate.slug).all()
        return [_template_out(t) for t in templates]

    @app.input(ProxyTemplateIn, arg_name='data')  # type: ignore
    @app.output(ProxyTemplateOut)  # type: ignore
    def post(self, data: ProxyTemplateIn):
        payload = data.model_dump()
        child_id = _child_id()
        slug = (payload.get('slug') or '').strip()
        if not slug:
            slug = _slug_from_name(payload['core'], payload['category'], payload.get('name') or '')

        existing = ProxyTemplate.query.filter(
            ProxyTemplate.slug == slug,
            ProxyTemplate.child_id == child_id,
        ).first()
        if existing and existing.is_builtin:
            slug = _allocate_unique_slug(slug, child_id)
        elif existing and not existing.is_builtin:
            payload.pop('slug', None)
            try:
                tpl = ProxyTemplate.add_or_update(child_id=child_id, id=existing.id, slug=slug, **payload)
                return _template_out(tpl)
            except ValueError as e:
                abort(409, str(e))

        slug = _allocate_unique_slug(slug, child_id)
        payload.pop('slug', None)

        try:
            tpl = ProxyTemplate.add_or_update(child_id=child_id, slug=slug, **payload)
        except ValueError as e:
            abort(409, str(e))
        except IntegrityError:
            db.session.rollback()
            abort(409, f'A template with slug "{slug}" already exists')
        return _template_out(tpl)


class ProxyTemplateApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(ProxyTemplateOut)  # type: ignore
    def get(self, template_id: int):
        return _template_out(_get_template_or_404(template_id))

    @app.input(PatchProxyTemplateIn, arg_name='data')  # type: ignore
    @app.output(ProxyTemplateOut)  # type: ignore
    def patch(self, template_id: int, data: PatchProxyTemplateIn):
        tpl = _get_template_or_404(template_id)
        patch = data.model_dump(exclude_unset=True)
        if tpl.is_builtin:
            update_kwargs: dict = {'id': template_id}
            for key in ('name', 'description', 'builtin_override', 'content'):
                if key in patch:
                    update_kwargs[key] = patch[key]
            try:
                updated = ProxyTemplate.add_or_update(child_id=tpl.child_id, slug=tpl.slug, **update_kwargs)
            except ValueError as e:
                abort(409, str(e))
            return _template_out(updated)

        if 'slug' in patch and not tpl.is_builtin:
            new_slug = (patch['slug'] or '').strip()
            if new_slug and new_slug != tpl.slug:
                if _slug_taken(new_slug, tpl.child_id, exclude_id=template_id):
                    abort(409, f'A template with slug "{new_slug}" already exists for this panel')
        merged = tpl.to_dict()
        merged.update(patch)
        merged['id'] = template_id
        merged.pop('is_builtin', None)
        merged.pop('builtin_content', None)
        merged.pop('child_id', None)
        incoming_slug = merged.pop('slug', None)
        slug = (incoming_slug or tpl.slug).strip()
        try:
            updated = ProxyTemplate.add_or_update(child_id=tpl.child_id, slug=slug, **merged)
        except ValueError as e:
            abort(409, str(e))
        except IntegrityError:
            db.session.rollback()
            abort(409, 'A template with this slug already exists')
        return _template_out(updated)

    def delete(self, template_id: int):
        tpl = _get_template_or_404(template_id)
        if tpl.is_builtin and tpl.child_id == 0:
            abort(400, 'Cannot delete builtin system template')
        db.session.delete(tpl)
        db.session.commit()
        return '', 204


class ProxyTemplateDuplicateApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(ProxyTemplateOut)  # type: ignore
    def post(self, template_id: int):
        tpl = _get_template_or_404(template_id)
        child_id = _child_id()
        base_name = f'{tpl.name} (copy)'
        base_slug = _slug_from_name(tpl.core, tpl.category, base_name)
        slug = _allocate_unique_slug(base_slug, child_id)
        new_tpl = ProxyTemplate(
            child_id=child_id,
            slug=slug,
            core=tpl.core,
            category=tpl.category,
            name=base_name,
            description=tpl.description,
            content=tpl.effective_content(),
            builtin_content='',
            builtin_override=False,
            is_builtin=False,
        )
        db.session.add(new_tpl)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, 'Could not duplicate template; try a different name')
        return _template_out(new_tpl)
