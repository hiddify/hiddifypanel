from flask import g
from flask.views import MethodView
from apiflask import abort
from flask import current_app as app
from sqlalchemy.exc import IntegrityError

from hiddifypanel.auth import login_required
from hiddifypanel.models import ProxyTemplate, TemplateCategory
from hiddifypanel.models.role import Role
from hiddifypanel.database import db

from .custom_proxy_schema import ProxyTemplateSchema, PatchProxyTemplateSchema


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


class ProxyTemplatesApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(list[ProxyTemplateSchema])  # type: ignore
    def get(self):
        from hiddifypanel.models.custom_proxy import seed_proxy_templates
        seed_proxy_templates(_child_id())
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
        return [t.to_dict() for t in templates]

    @app.input(ProxyTemplateSchema, arg_name='data')  # type: ignore
    @app.output(ProxyTemplateSchema)  # type: ignore
    def post(self, data):
        data = dict(data)
        child_id = _child_id()
        slug = (data.get('slug') or '').strip()
        if not slug:
            slug = _slug_from_name(data['core'], data['category'], data.get('name') or '')

        existing = ProxyTemplate.query.filter(
            ProxyTemplate.slug == slug,
            ProxyTemplate.child_id == child_id,
        ).first()
        if existing and existing.is_builtin:
            slug = _allocate_unique_slug(slug, child_id)
        elif existing and not existing.is_builtin:
            data.pop('slug', None)
            try:
                tpl = ProxyTemplate.add_or_update(child_id=child_id, id=existing.id, slug=slug, **data)
                return tpl.to_dict()
            except ValueError as e:
                abort(409, str(e))

        slug = _allocate_unique_slug(slug, child_id)
        data.pop('slug', None)

        try:
            tpl = ProxyTemplate.add_or_update(child_id=child_id, slug=slug, **data)
        except ValueError as e:
            abort(409, str(e))
        except IntegrityError:
            db.session.rollback()
            abort(409, f'A template with slug "{slug}" already exists')
        return tpl.to_dict()


class ProxyTemplateApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(ProxyTemplateSchema)  # type: ignore
    def get(self, template_id: int):
        return _get_template_or_404(template_id).to_dict()

    @app.input(PatchProxyTemplateSchema, arg_name='data')  # type: ignore
    @app.output(ProxyTemplateSchema)  # type: ignore
    def patch(self, template_id: int, data):
        tpl = _get_template_or_404(template_id)
        if 'slug' in data and not tpl.is_builtin:
            new_slug = (data['slug'] or '').strip()
            if new_slug and new_slug != tpl.slug:
                if _slug_taken(new_slug, tpl.child_id, exclude_id=template_id):
                    abort(409, f'A template with slug "{new_slug}" already exists for this panel')
        merged = tpl.to_dict()
        merged.update(data)
        merged['id'] = template_id
        merged.pop('is_builtin', None)
        merged.pop('builtin_content', None)
        merged.pop('child_id', None)
        slug = (merged.pop('slug', None) or tpl.slug).strip() if not tpl.is_builtin else tpl.slug
        try:
            updated = ProxyTemplate.add_or_update(child_id=tpl.child_id, slug=slug, **merged)
        except ValueError as e:
            abort(409, str(e))
        except IntegrityError:
            db.session.rollback()
            abort(409, 'A template with this slug already exists')
        return updated.to_dict()

    def delete(self, template_id: int):
        tpl = _get_template_or_404(template_id)
        if tpl.is_builtin and tpl.child_id == 0:
            abort(400, 'Cannot delete builtin system template')
        db.session.delete(tpl)
        db.session.commit()
        return '', 204


class ProxyTemplateDuplicateApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    @app.output(ProxyTemplateSchema)  # type: ignore
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
        return new_tpl.to_dict()
