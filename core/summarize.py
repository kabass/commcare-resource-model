import humanize
import pandas as pd

SUMMARY_SHEET = 'Summary'


def summarize_storage_data(config, summary_date, storage_data):
    storage_snapshot = storage_data.loc[summary_date]
    storage_by_cat = pd.DataFrame({
        'Size': storage_snapshot.map(humanize.naturalsize),
        'Buffer': (storage_snapshot * float(config.buffer)).map(humanize.naturalsize),
        'Total': (storage_snapshot * (1 + float(config.buffer))).map(humanize.naturalsize),
        'total_raw': (storage_snapshot * (1 + float(config.buffer))),
        'Group': pd.Series({
            storage_key: storage_conf.group
            for storage_key, storage_conf in config.storage.items()
        })
    })

    by_type = storage_by_cat.groupby('Group')['total_raw'].sum()
    by_type.index.name = None
    storage_by_type = pd.DataFrame({
        'Total': by_type.map(humanize.naturalsize),
    })

    storage_by_cat.sort_index(inplace=True)
    storage_by_type.sort_index(inplace=True)
    return storage_by_cat, storage_by_type


def summarize_compute_data(config, summary_date, compute_data):
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
    return combined
