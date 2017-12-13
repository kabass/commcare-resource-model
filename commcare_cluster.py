import argparse

import humanize
import pandas as pd

from core.config import config_from_path
from core.models import models_by_slug, ComputeModel
from core.writers import ConsoleWriter
from core.writers import ExcelWriter

SUMMARY_SHEET = 'Summary'


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


def write_storage_summary(config, writer, summary_date, storage_data):
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
    by_type.index.name = None
    storage_by_type = pd.DataFrame({
        'Total': by_type.map(humanize.naturalsize),
    })

    storage_by_cat.sort_index(inplace=True)
    storage_by_cat = storage_by_cat[['Size', 'Buffer', 'Total', 'Is SSD']]  # select columns
    writer.write_data_frame(storage_by_cat, SUMMARY_SHEET, 'Storage Category')

    storage_by_type.sort_index(inplace=True)
    writer.write_data_frame(storage_by_type, SUMMARY_SHEET, 'Storage Type')


def write_compute_summary(config, writer, summary_date, compute_data):
    compute_snapshot = compute_data.loc[summary_date]
    unstacked = compute_snapshot.unstack()
    buffer = unstacked * float(config.buffer)
    total = unstacked.add(buffer)

    buffer = buffer.rename({col: '%s Buffer' % col for col in buffer.columns}, axis=1)
    buffer = buffer.astype(int)
    total = total.rename({col: '%s Total' % col for col in total.columns}, axis=1)
    total = total.astype(int)

    unstacked = unstacked.astype(int)
    combined = pd.concat([unstacked, buffer, total], axis=1)
    combined = combined.reindex(columns=sorted(list(combined.columns)))
    combined.sort_index(inplace=True)
    writer.write_data_frame(combined, SUMMARY_SHEET, 'Service')


def write_raw_data(writer, usage, storage):
    writer.write_data_frame(usage, 'Usage', 'Dates')
    writer.write_data_frame(storage, 'Storage', 'Dates')


def get_storage(config, usage_data):
    def _service_storage(config, service_model):
        bytes = usage_data[service_model.referenced_field] * service_model.unit_bytes
        with_baseline = bytes + + config.static_baseline
        return with_baseline * config.redundancy_factor

    storage_df = pd.DataFrame()
    for storage_key, storage_conf in config.storage.items():
        storage = pd.concat([
            _service_storage(storage_conf, model)
            for model in storage_conf.data_models
        ], axis=1)
        storage_df[storage_key] = storage.sum(axis=1)
    return storage_df


def get_compute(config, usage_data):
    keys = list(config.compute.keys())
    return pd.concat([
        ComputeModel(key, config.compute[key]).data_frame(usage_data)
        for key in keys
    ], keys=keys, axis=1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('CommCare Cluster Model')
    parser.add_argument('config', help='Path to config file')

    args = parser.parse_args()

    config = config_from_path(args.config)
    usage = get_usage(config)
    storage = get_storage(config, usage)
    compute = get_compute(config, usage)

    summary_date = storage.iloc[-1].name  # summarize at final date
    # writer = ExcelWriter('output.xlsx')
    writer = ConsoleWriter()
    write_storage_summary(config, writer, summary_date, storage)
    write_compute_summary(config, writer, summary_date, compute)
    # write_raw_data(writer, usage, storage)
    writer.save()
