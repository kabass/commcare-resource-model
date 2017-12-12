import re
from collections import OrderedDict

import jsonobject
import yaml
from jsonobject.base import get_dynamic_properties


class UserRange(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    start_date = jsonobject.StringProperty()
    end_date = jsonobject.StringProperty()
    user_count = jsonobject.IntegerProperty()

    def __init__(self, obj):
        if isinstance(obj, list):
            obj = {
                'start_date': obj[0],
                'end_date': obj[1],
                'user_count': obj[2],
            }
        super(UserRange, self).__init__(obj)


class UsageModelDef(jsonobject.JsonObject):
    _allow_dynamic_properties = True
    model = jsonobject.StringProperty()

    @property
    def model_params(self):
        return get_dynamic_properties(self)


class StorageSizeDef(jsonobject.JsonObject):
    field = jsonobject.StringProperty()
    bytes = jsonobject.IntegerProperty()


class StorageDef(jsonobject.JsonObject):
    _allow_dynamic_properties = True
    sql_primary = jsonobject.ListProperty(StorageSizeDef)


class ClusterConfig(jsonobject.JsonObject):
    users = jsonobject.ListProperty(UserRange)
    usage = jsonobject.DictProperty(UsageModelDef)
    storage = jsonobject.ObjectProperty(StorageDef)


def config_from_path(config_path):
    with open(config_path, 'r') as f:
        return ClusterConfig(yaml.load(f))
