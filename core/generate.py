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


def generate_storage_data(config, usage_data):
    def _service_storage(storage_conf, service_model):
        bytes = usage_data[service_model.referenced_field] * service_model.unit_bytes
        with_baseline = bytes + + storage_conf.static_baseline
        return with_baseline * storage_conf.redundancy_factor

    storage_df = pd.DataFrame()
    for storage_key, storage_conf in config.storage.items():
        storage = pd.concat([
            _service_storage(storage_conf, model)
            for model in storage_conf.data_models
        ], axis=1)
        storage_df[storage_key] = storage.sum(axis=1)
    return storage_df


def generate_compute_data(config, usage_data):
    keys = list(config.compute.keys())
    return pd.concat([
        ComputeModel(key, config.compute[key]).data_frame(usage_data)
        for key in keys
    ], keys=keys, axis=1)
