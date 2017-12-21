import pandas as pd

from core.models import models_by_slug, ComputeModel


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
        service_compute = ComputeModel(service_name, service_def).data_frame(usage_data)
        service_storage = _service_storage_data(config, service_def, usage_data, service_compute)
        data = pd.concat([service_compute, service_storage], keys=['Compute', 'Storage'], axis=1)
        dfs.append(data)
    return pd.concat(dfs, keys=list(config.services), axis=1)


def _service_storage_data(config, service_def, usage_data, compute_data):
    def _service_storage(storage_def, storage_size_def):
        bytes = usage_data[storage_size_def.referenced_field] * storage_size_def.unit_bytes
        with_baseline = bytes + storage_def.static_baseline
        return with_baseline * storage_def.redundancy_factor

    if service_def.storage.data_models:
        storage = pd.concat([
            _service_storage(service_def.storage, model)
            for model in service_def.storage.data_models
        ], axis=1)
        data_storage = storage.sum(axis=1)
    else:
        data_storage = pd.Series([0] * len(usage_data), index=usage_data.index)

    vm_count = compute_data['Nodes']
    vm_storage = vm_count * config.vm_os_storage_gb * (1000.0 ** 3)
    return pd.DataFrame({
        'Data Storage': data_storage,
        'OS Storage': vm_storage
    })
