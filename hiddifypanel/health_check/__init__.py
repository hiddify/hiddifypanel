from __future__ import annotations

from flask import Response, g

from .service import (
    handle_domain_health_request,
    handle_ip_health_request,
    health_check_domain_url,
    health_check_ip_url,
    health_secret_path,
    is_health_secret_request,
    run_domain_health_check,
    run_ip_health_check,
)

__all__ = [
    'init_app',
    'health_secret_path',
    'is_health_secret_request',
    'health_check_domain_url',
    'health_check_ip_url',
    'run_domain_health_check',
    'run_ip_health_check',
    'handle_domain_health_request',
    'handle_ip_health_request',
]


def init_app(app) -> None:
    @app.route('/<health_path>/', methods=['GET'])
    @app.route('/<health_path>', methods=['GET'])
    def panel_health(health_path: str):
        return Response('panel', status=200, mimetype='text/plain')

    @app.route('/<health_path>/panel/', methods=['GET'])
    @app.route('/<health_path>/panel', methods=['GET'])
    def panel_health_explicit(health_path: str):
        return Response('panel', status=200, mimetype='text/plain')

    @app.route('/<health_path>/domain/<int:domain_id>/', methods=['GET'])
    @app.route('/<health_path>/domain/<int:domain_id>', methods=['GET'])
    def health_check_domain(health_path: str, domain_id: int):
        child_id = g.child.id if getattr(g, 'child', None) else 0
        body, status = handle_domain_health_request(domain_id, child_id)
        return Response(body, status=status, mimetype='text/plain')

    @app.route('/<health_path>/ip/<int:ip_id>/', methods=['GET'])
    @app.route('/<health_path>/ip/<int:ip_id>', methods=['GET'])
    def health_check_ip(health_path: str, ip_id: int):
        child_id = g.child.id if getattr(g, 'child', None) else 0
        body, status = handle_ip_health_request(ip_id, child_id)
        return Response(body, status=status, mimetype='text/plain')
