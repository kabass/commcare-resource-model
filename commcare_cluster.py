import argparse

import humanize
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


def write_summary(config, output_path, summary_date, storage_data):
    storage_snapshot = storage_data.loc[summary_date]
    storage_by_cat = pd.DataFrame({
        'Size': storage_snapshot.map(humanize.naturalsize),
        'Buffer': (storage_snapshot * float(config.buffer)).map(humanize.naturalsize),
        'Total': (storage_snapshot * (1 + float(config.buffer))).map(humanize.naturalsize),
        'total_raw': (storage_snapshot * (1 + float(config.buffer))),
        'Is SSD': pd.Series({
            storage_key: storage_conf.ssd
            for storage_key, storage_conf in config.storage.items()
        })
    })

    by_type = storage_by_cat.groupby('Is SSD')['total_raw'].sum()
    by_type.index = by_type.index.map(lambda i: 'SSD' if i else 'SAS')
    storage_by_type = pd.DataFrame({
        'Total': by_type.map(humanize.naturalsize),
    })

    writer = pd.ExcelWriter(output_path)
    storage_by_cat[['Size', 'Buffer', 'Total', 'Is SSD']].to_excel(writer, 'Storage Summary', index_label='Storage Category')
    storage_by_type.to_excel(writer, 'Storage Summary', index_label='Storage Type', startrow=len(config.storage) + 2)
    writer.save()


def write_raw_data(ouput_path, usage, storage):
    writer = pd.ExcelWriter(ouput_path)
    usage.to_excel(writer, 'Usage', index_label='Dates')
    storage.to_excel(writer, 'Storage', index_label='Dates')
    writer.save()


def get_storage(config, usage_data):
    storage_df = pd.DataFrame()
    for storage_key, storage_conf in config.storage.items():
        storage = pd.concat([
            usage_data[model.referenced_field] * model.unit_bytes * storage_conf.redundancy_factor
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

    # summarize at final date
    summary_date = storage.iloc[-1].name
    write_summary(config, 'output.xlsx', summary_date, storage)
    write_raw_data('raw.xlsx', usage, storage)
