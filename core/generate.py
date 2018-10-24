import numpy as np
import pandas as pd

from core.models import models_by_slug
from core.utils import byte_map


def generate_usage_data(config):
    model_classes = models_by_slug()

    models = [
        model_classes[model_def.model](name, **model_def.model_params)
        for name, model_def in config.usage.items()
    ]
    usage_df = pd.DataFrame()
    while models:
        models_len = len(models)
        for model in models:
            if model.can_run(usage_df):
                models.remove(model)
                usage_df = pd.concat([usage_df, model.data_frame(usage_df)], axis=1)
        if len(models) == models_len:
            # no models could run which means we're stuck
            models_remaining = [model.name for model in models]
            raise Exception('Unmet dependencies for models: %s' % ', '.join(models_remaining))

    return usage_df


def generate_service_data(config, usage_data):
    dfs = []
    for service_name, service_def in config.services.items():
        data_storage = _service_storage_data(service_def, usage_data)
        compute = ComputeModel(service_name, service_def).data_frame(usage_data, data_storage)
        os_storage = _service_os_storage(config, compute)
        data = pd.concat([compute, data_storage, os_storage], keys=['Compute', 'Data Storage', 'OS Storage'], axis=1)
        dfs.append(data)
    return pd.concat(dfs, keys=list(config.services), axis=1)


def _service_storage_data(service_def, usage_data):
    def _service_storage(storage_def, storage_size_def):
        bytes = usage_data[storage_size_def.referenced_field] * storage_size_def.unit_bytes
        return bytes * storage_def.redundancy_factor

    if service_def.storage.data_models:
        storage = pd.concat([
            _service_storage(service_def.storage, model)
            for model in service_def.storage.data_models
        ], axis=1)
        data_storage = storage.sum(axis=1) + service_def.storage.static_baseline_bytes
    else:
        data_storage = pd.Series([0] * len(usage_data), index=usage_data.index)

    return pd.DataFrame({
        'storage': data_storage
    })


def _service_os_storage(config, compute_data):
    vm_count = compute_data['VMs']
    vm_storage = vm_count * config.vm_os_storage_gb * (1000.0 ** 3)
    return pd.DataFrame({
        'storage': vm_storage
    })


class ComputeModel(object):
    def __init__(self, service_name, service_def):
        self.service_name = service_name
        self.service_def = service_def

    def _get_process_series(self, process_def, usage_data):
        if process_def.static_number:
            return pd.Series([process_def.static_number] * len(usage_data), index=usage_data.index)
        else:
            return (usage_data / process_def.capacity).map(np.ceil)

    def data_frame(self, current_data_frame, data_storage):
        usage = current_data_frame[self.service_def.usage_field]
        if self.service_def.process.sub_processes:
            processes = pd.concat([
                self._get_process_series(sub_process, usage)
                for sub_process in self.service_def.process.sub_processes
            ], keys=[p.name for p in self.service_def.process.sub_processes], axis=1)

            total = processes.apply(sum, axis=1)
            cores = total * float(self.service_def.process.cores_per_sub_process)
            ram = total * float(self.service_def.process.ram_per_sub_process)
            vms_by_cores = cores / self.service_def.process.cores_per_node
            vms_by_ram = ram / self.service_def.process.ram_per_node
            vms = vms_by_cores if vms_by_cores[-1] > vms_by_ram[-1] else vms_by_ram
            compute = pd.concat([cores, ram, vms.map(np.ceil)], keys=['CPU', 'RAM', 'VMs'], axis=1)
        elif self.service_def.usage_capacity_per_node:
            nodes = (usage / self.service_def.usage_capacity_per_node).map(np.ceil)
            with_min = pd.concat([
                nodes,
                pd.Series([self.service_def.min_nodes] * len(nodes), index=nodes.index)
            ], axis=1)
            nodes = with_min.max(1)
            compute = pd.concat([
                nodes * self.service_def.process.cores_per_node,
                nodes * self.service_def.process.ram_per_node,
                nodes
            ], keys=['CPU', 'RAM', 'VMs'], axis=1)
        else:
            nodes = pd.Series([0] * len(usage), index=usage.index)
            compute = pd.concat([nodes, nodes, nodes], keys=['CPU', 'RAM', 'VMs'], axis=1)

        if self.service_def.max_storage_per_node_bytes:
            # Add extra VMs to keep storage per VM within range
            max_supported = compute['VMs'] * self.service_def.max_storage_per_node_bytes
            extra = data_storage['storage'] - max_supported
            extra[extra < 0] = 0
            extra_vms = np.ceil(extra / self.service_def.max_storage_per_node_bytes)
            compute['VMs'] = compute['VMs'] + extra_vms

        return compute
