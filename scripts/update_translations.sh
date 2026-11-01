#!/bin/bash
# source .env
source /opt/hiddify-manager/scripts/common/utils.sh
activate_python_venv


PATH=/config/.local/bin:$PATH

python -c "
from hiddifypanel import models;
print(''.join([f'{{{{_(\"config.{c}.label\")}}}}\n{{{{_(\"config.{c}.description\")}}}}\n' for c in models.ConfigEnum]));print(''.join([f'{{{{_(\"config.{cat}.label\")}}}}{{{{_(\"config.{cat}.description\")}}}}\n' for cat in models.ConfigCategory]));
def print_enum(en):
  print(''.join([f'{{{{_(\"{item}\")}}}}\n' for item in en]))
print_enum(models.DomainType)
print_enum(models.UserMode)

from hiddifypanel.models import config_enum, ConfigEnum
for c in ConfigEnum:
   if isinstance(c.type, type) and issubclass(c.type,config_enum.HEnum) and c.type!=str:
       print(''.join([f'{{{{_(\"config.{c.name}.{k}\")}}}}\n' for k in c.type]))
            

" >../hiddifypanel/templates/fake.html


pybabel extract -F babel.cfg -k "_gettext lazy_gettext gettext _ __" -o messages.pot ../hiddifypanel

# Flask (Python and Jinja) reads translations.i18n/<lang>.json directly (hiddifypanel/json_translations.py): add the
# msgids found in the code to every language file. No .po / .mo files.
for lang in en fa my pt ru zh; do
    python translate_utils.py update-json ../hiddifypanel/translations.i18n/${lang}.json messages.pot || {
        echo "error in python3 translate_utils.py update-json ../hiddifypanel/translations.i18n/${lang}.json messages.pot"
        exit 1
    }
done
rm -f messages.pot
