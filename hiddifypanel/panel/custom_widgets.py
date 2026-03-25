import datetime

from flask_admin.contrib.sqla import ModelView
from flask_babel import lazy_gettext as _
from wtforms import TextAreaField
from wtforms.fields import IntegerField, SelectField, DecimalField
from wtforms.widgets import TextArea

from wtforms import Field
from wtforms.validators import ValidationError
from wtforms.widgets import TextArea
import json5

from hiddifypanel.models import *


# from gettext import gettext as _


class DaysLeftField(IntegerField):
    def process_data(self, value):
        if value is not None:
            days_left = (value - datetime.date.today()).days
            self.data = days_left
        else:
            self.data = None

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0]:
            days_left = valuelist[0]
            new_date_value = datetime.date.today() + datetime.timedelta(days=int(days_left))
            self.data = new_date_value
        else:
            self.data = None


class LastResetField(IntegerField):
    def process_data(self, value):
        if value is not None:
            days_left = (datetime.date.today() - value).days
            self.data = days_left
        else:
            self.data = None

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0]:
            days_left = valuelist[0]
            new_date_value = datetime.date.today() - datetime.timedelta(days=int(days_left))
            self.data = new_date_value
        else:
            self.data = None


class CKTextAreaWidget(TextArea):
    extra_js = ['//cdn.ckeditor.com/4.6.0/standard/ckeditor.js']

    def __call__(self, field, **kwargs):
        if kwargs.get('class'):
            kwargs['class'] += ' ckeditor'
        else:
            kwargs.setdefault('class', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)


class CKTextAreaField(TextAreaField):
    extra_js = ['//cdn.ckeditor.com/4.6.0/standard/ckeditor.js']
    widget = CKTextAreaWidget()


class MessageAdmin(ModelView):
    extra_js = ['//cdn.ckeditor.com/4.6.0/standard/ckeditor.js']

    form_overrides = {
        'body': CKTextAreaField
    }


class EnumSelectField(SelectField):
    def __init__(self, enum, *args, **kwargs):
        choices = [(str(enum_value.value), _(enum_value.name)) for enum_value in enum]
        super().__init__(*args, choices=choices, **kwargs)


class UsageField(DecimalField):
    def process_data(self, value):
        if value is not None:
            self.data = value / ONE_GIG
        else:
            self.data = None

    def process_formdata(self, valuelist):

        if valuelist and valuelist[0]:
            self.data = int(float(valuelist[0]) * ONE_GIG)
        else:
            self.data = None







class JSONWidget(TextArea):
    def __call__(self, field, **kwargs):
        if kwargs.get('class'):
            kwargs['class'] += ' ltr json-editor'
        else:
            kwargs.setdefault('class', 'ltr json-editor')
        
        kwargs.setdefault("rows",10)
        
        return super().__call__(field, **kwargs)

class JSONField(Field):
    widget = JSONWidget()

    def _value(self):
        if not self.data:
            return ''
        if isinstance(self.data, str):
            return self.data
        try:
            return json5.dumps(self.data, indent=2)
        except Exception:
            return str(self.data)

    def process_formdata(self, valuelist):
        if valuelist:
            try:    
                self.data = json5.loads(valuelist[0]) if valuelist[0] else ""
            except Exception as e:
                raise ValidationError(f'Invalid JSON: {e}')
            


from typing import Type, TypeVar,Generic
from pydantic import BaseModel
T=TypeVar("T",bound=BaseModel)
class CustomJSONField(Field, Generic[T]):
    widget = JSONWidget()

    def __init__(self, model: Type[T], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

    def _value(self):
        if not self.data:
            data_dict = {}
        else:
            try:
                if isinstance(self.data, str):
                    data_dict = json5.loads(self.data)
                else:
                    data_dict = self.data
            except Exception:
                data_dict = {}

        # Build JSON with defaults + comments
        lines = ["{"]

        for name, field in self.model.model_fields.items():
            default = field.default
            desc = field.description or ""

            value = data_dict.get(name, default)

            if isinstance(value, str):
                value_str = f'"{value}"'
            else:
                value_str = json5.dumps(value)

            if desc:
                lines.append(f' "{name}": {value_str}, // {desc}')
            else:
                lines.append(f' "{name}": {value_str},')

        if len(lines) > 1:
            lines[-1] = lines[-1].rstrip(',')

        lines.append("}")
        return "\n".join(lines)

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                raw = valuelist[0]

                if not raw:
                    self.data = ""
                    return

                parsed = json5.loads(raw)

                # Validate with Pydantic
                model_obj = self.model(**parsed)

                # Store as JSON string
                self.data = model_obj.model_dump_json()

            except Exception as e:
                raise ValidationError(f'Invalid JSON: {e}')