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
    _allow_dynamic_properties = False
    referenced_field = jsonobject.StringProperty(required=True)
    unit_bytes = jsonobject.IntegerProperty(required=True)


class StorageDef(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    group = jsonobject.StringProperty(required=True)
    redundancy_factor = jsonobject.IntegerProperty(required=True)
    static_baseline = jsonobject.IntegerProperty(default=0)
    data_models = jsonobject.ListProperty(StorageSizeDef, required=True)


class ProcessDef(jsonobject.JsonObject):
    name = jsonobject.StringProperty()
    user_capacity = jsonobject.IntegerProperty(required=True)


class ComputeDef(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    cores_per_vm = jsonobject.IntegerProperty(required=True)
    ram_per_vm = jsonobject.IntegerProperty(required=True)
    cores_per_process = jsonobject.DecimalProperty()
    ram_per_process = jsonobject.DecimalProperty()
    processes = jsonobject.ListProperty(ProcessDef, required=True)

    def validate(self, required=True):
        if len(self.processes) > 1:
            assert self.cores_per_process, 'cores_per_process required if more than one process listed'
            assert self.ram_per_process, 'ram_per_process required if more than one process listed'

    @property
    def process_cores(self):
        return float(self.cores_per_process or self.cores_per_vm)

    @property
    def process_ram(self):
        return float(self.ram_per_process or self.ram_per_vm)


class ClusterConfig(jsonobject.JsonObject):
    buffer = jsonobject.DecimalProperty(required=True)
    usage = jsonobject.DictProperty(UsageModelDef, required=True)
    storage = jsonobject.DictProperty(StorageDef, required=True)
    compute = jsonobject.DictProperty(ComputeDef, required=True)


def config_from_path(config_path):
    with open(config_path, 'r') as f:
        return ClusterConfig(yaml.load(f))
