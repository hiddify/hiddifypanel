from flask.views import MethodView
from loguru import logger

from hiddifypanel import current_app as app
from hiddifypanel.auth import login_required
from hiddifypanel.models import Child

from .schema import ChildStatusInputSchema, ChildStatusOutputSchema


class StatusApi(MethodView):
    decorators = [login_required(node_auth=True)]

    @app.input(ChildStatusInputSchema, arg_name="data")
    @app.output(ChildStatusOutputSchema)
    def post(self, data: ChildStatusInputSchema):
        logger.info(f"Checking the existence of child with unique_id: {data.child_unique_id}")
        res = ChildStatusOutputSchema(existance=False)

        child = Child.query.filter(Child.unique_id == data.child_unique_id).first()
        if child:
            logger.info(f"Child with unique_id: {data.child_unique_id} exists")
            res.existance = True

        return res
