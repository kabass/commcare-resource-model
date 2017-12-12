import jsonobject
import yaml
from jsonobject.base import get_dynamic_properties


class UsageModelDef(jsonobject.JsonObject):
    _allow_dynamic_properties = True
    model = jsonobject.StringProperty(required=True)

    @property
    def model_params(self):
        return get_dynamic_properties(self)


class StorageSizeDef(jsonobject.JsonObject):
    referenced_field = jsonobject.StringProperty(required=True)
    unit_bytes = jsonobject.IntegerProperty(required=True)


class StorageDef(jsonobject.JsonObject):
    _allow_dynamic_properties = True
    data_models = jsonobject.ListProperty(StorageSizeDef)


class ClusterConfig(jsonobject.JsonObject):
    usage = jsonobject.DictProperty(UsageModelDef)
    storage = jsonobject.DictProperty(StorageDef)


def config_from_path(config_path):
    with open(config_path, 'r') as f:
        return ClusterConfig(yaml.load(f))
