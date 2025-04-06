from typing import Optional
from sqlalchemy.orm import  sessionmaker
from sqlalchemy.orm import as_declarative, declared_attr,relationship
import sqlalchemy.orm as sa_orm

# from sqlalchemy_utils import UUIDType
import re
import os
from sqlalchemy import Row, create_engine, text, Sequence
import sqlalchemy as sa


# class SQLAlchemy:
    
#     def __init__(self):
#         self.engine = create_engine(os.environ.get("SQLALCHEMY_DATABASE_URI"))
#         self.session_maker = sessionmaker(bind=self.engine)
#         self.session=self.session_maker()
#         @as_declarative()
#         class Base:
#             @declared_attr
#             def __tablename__(cls):
#                 return cls.__name__.lower()

#             @classmethod
#             @property
#             def query(cls):
#                 return self.session.query(cls)
            
    
#         self.Query=sa_orm.Query
#         self.Model=Base
#         self.Table=sa.Table
#         self.Column=sa.Column
#         self.Integer=sa.Integer
#         self.ForeignKey=sa.ForeignKey

    # def _set_rel_query(self, kwargs) -> None:
    #         """Apply the extension's :attr:`Query` class as the default for relationships
    #         and backrefs.

    #         :meta private:
    #         """
    #         kwargs.setdefault("query_class", self.Query)

    #         if "backref" in kwargs:
    #             backref = kwargs["backref"]

    #             if isinstance(backref, str):
    #                 backref = (backref, {})

    #             backref[1].setdefault("query_class", self.Query)

        
    # def relationship(
    #         self, *args, **kwargs
    #     ) :
          
    #         self._set_rel_query(kwargs)
    #         return sa_orm.relationship(*args, **kwargs)
from flask_sqlalchemy import SQLAlchemy
    

db = SQLAlchemy()
# db.UUID = UUIDType  # type: ignore

def init_no_flask():
    engine = create_engine(os.environ.get("SQLALCHEMY_DATABASE_URI"))
    db.session = sessionmaker(bind=engine)()

def init_app(app):
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    db.init_app(app)
    with app.app_context():
        from hiddifypanel.panel.init_db import init_db
        init_db()
        


def db_execute(query: str, return_val: bool = False, commit: bool = False, **params: dict):
    q = db.session.execute(text(query), params)
    if commit:
        db.session.commit()
    if return_val:
        return q.fetchall()

    # with db.engine.connect() as connection:
    #     res = connection.execute(text(query), params)
    #     connection.commit()s
    # return res

