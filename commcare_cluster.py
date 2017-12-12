import argparse

import pandas as pd

from core.config import config_from_path
from core.models import models_by_slug


def get_usage(config):
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


def get_storage(config, usage_data):
    storage_df = pd.DataFrame()
    for storage_key, storage_conf in config.storage.items():
        storage = pd.concat([
            usage_data[model.referenced_field] * model.unit_bytes
            for model in storage_conf.data_models
        ], axis=1)
        storage_df[storage_key] = storage.sum(axis=1)
    return storage_df


if __name__ == '__main__':
    parser = argparse.ArgumentParser('CommCare Cluster Model')
    parser.add_argument('config', help='Path to config file')

    args = parser.parse_args()

    config = config_from_path(args.config)
    usage = get_usage(config)
    storage = get_storage(config, usage)
