# from flask_simplelogin import login_required

from apiflask import abort
from flask import jsonify, request
from flask_restful import Resource

from hiddifypanel.auth import login_required
from hiddifypanel.drivers import user_driver
from hiddifypanel.models import *
from hiddifypanel.panel import hiddify


class UserResource(Resource):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        uuid = request.args.get("uuid")
        if uuid:
            user = User.by_uuid(uuid) or abort(404, "user not found")
            return jsonify(user.to_dict())

        users = User.query.all() or abort(502, "WTF!")
        return jsonify([user.to_dict() for user in users])

    def post(self):
        data = request.json
        uuid = data.get("uuid") or abort(422, "Parameter issue: 'uuid'")
        User.add_or_update(**data)
        user = User.by_uuid(uuid) or abort(502, "unknown issue! user is not added")
        user_driver.add_client(user)
        hiddify.quick_apply_users()
        return jsonify({"status": 200, "msg": "ok"})

    def delete(self):
        uuid = request.args.get("uuid") or abort(422, "Parameter issue: 'uuid'")
        user = User.by_uuid(uuid) or abort(404, "user not found")
        user.remove()
        hiddify.quick_apply_users()
        return jsonify({"status": 200, "msg": "ok"})


class AdminUserResource(Resource):
    decorators = [login_required({Role.super_admin})]

    def get(self, uuid=None):
        uuid = request.args.get("uuid")
        if uuid:
            admin = AdminUser.by_uuid(uuid) or abort(404, "user not found")
            return jsonify(admin.to_dict())

        admins = AdminUser.query.all() or abort(502, "WTF!")
        return jsonify([admin.to_dict() for admin in admins])

    def post(self):
        data = request.json
        uuid = data.get("uuid") or abort(422, "Parameter issue: 'uuid'")
        AdminUser.add_or_update(**data)

        return jsonify({"status": 200, "msg": "ok"})

    def delete(self):
        uuid = request.args.get("uuid") or abort(422, "Parameter issue: 'uuid'")
        admin = AdminUser.by_uuid(uuid) or abort(404, "admin not found")
        admin.remove()
        return jsonify({"status": 200, "msg": "ok"})


# class DomainResource(Resource):
#     def get(self,domain=None):
#         if domain:
#             product = Domain.query.filter(Domain.domain==domain).first() or abort(204)
#             return jsonify(hiddify.domain_dict(product))
#         products = Domain.query.all() or abort(204)
#         return jsonify(
#             [hiddify.domain_dict(product) for product in products]
#         )
#     def post(self):
#         hiddify.add_or_update_domain(**request.json)
#         return jsonify({'status':200,'msg':'ok'})

# class ParentDomainResource(Resource):
#     def get(self,parent_domain=None):
#         if domain:
#             product = ParentDomain.query.filter(ParentDomain.domain==domain).first() or abort(204)
#             return jsonify(hiddify.parent_domain_dict(product))
#         products = ParentDomain.query.all() or abort(204)
#         return jsonify(
#             [hiddify.parent_domain_dict(product) for product in products]
#         )
#     def post(self):
#         hiddify.add_or_update_parent_domain(**request.json)
#         return jsonify({'status':200,'msg':'ok'})

# class ConfigResource(Resource):
#     def get(self,key=None,child_id=0):
#         if key:
#             return jsonify(hconfig(key,child_id))
#         return jsonify(get_hconfigs(child_id))

#     def post(self):
#         hiddify.add_or_update_config(**request.json)
#         return jsonify({'status':200,'msg':'ok'})


class HelloResource(Resource):
    def get(self):
        return jsonify({"status": 200, "msg": "ok"})


# class UpdateUsageResource(Resource):
#     def get(self):
#         return jsonify({"status": 200, "msg": "ok"})
