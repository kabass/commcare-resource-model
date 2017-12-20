from collections import namedtuple

import pandas as pd

from core.utils import format_date, bytes_to_gb

StorageSummary = namedtuple('StorageSummary', 'by_category by_group')
SummaryComparison = namedtuple('SummaryComparison', 'storage_by_category storage_by_group compute')


def compare_summaries(summaries_by_date):
    storage_by_cat_series = []
    storage_by_group_series = []
    compute_series = []
    dates = sorted(list(summaries_by_date))
    for date in dates:
        summary_data = summaries_by_date[date]
        storage_by_cat_series.append(summary_data.storage.by_category['Total (GB)'])
        storage_by_group_series.append(summary_data.storage.by_group['Total (GB)'])
        compute_series.append(summary_data.compute[['CPU Total', 'RAM Total', 'VMs Total']])

    first_date = list(summaries_by_date)[0]
    group_series = summaries_by_date[first_date].storage.by_category['Group']
    storage_by_cat_series.append(group_series)

    keys = [format_date(date) for date in dates] + ['Group']
    storage_by_cat = _combine_summary_data(storage_by_cat_series, keys)
    storage_by_group = _combine_summary_data(storage_by_group_series, keys, False)
    compute = _combine_summary_data(compute_series, keys)
    return SummaryComparison(storage_by_cat, storage_by_group, compute)


def _combine_summary_data(series, keys, add_total=True):
    df = pd.concat(series, axis=1, keys=keys)
    if add_total:
        total = df.sum(numeric_only=True)
        total.name = 'Total'
        df = df.append(total, ignore_index=False)
    return df


def summarize_storage_data(config, summary_date, storage_data):
    storage_snapshot = storage_data.loc[summary_date]
    storage_by_cat = pd.DataFrame({
        'Size': storage_snapshot.map(bytes_to_gb),
        'Buffer': (storage_snapshot * float(config.esitmation_buffer)).map(bytes_to_gb),
        'Total (GB)': (storage_snapshot * (1 + float(config.esitmation_buffer))).map(bytes_to_gb),
        'total_raw': (storage_snapshot * (1 + float(config.esitmation_buffer))),
        'Group': pd.Series({
            storage_key: storage_conf.group
            for storage_key, storage_conf in config.storage.items()
        })
    })

    by_type = storage_by_cat.groupby('Group')['total_raw'].sum()
    by_type.index.name = None
    storage_by_group = pd.DataFrame({
        'Total (GB)': by_type.map(bytes_to_gb),
    })

    storage_by_cat.sort_index(inplace=True)
    storage_by_group.sort_index(inplace=True)
    return StorageSummary(storage_by_cat, storage_by_group)


def summarize_compute_data(config, summary_date, compute_data):
    compute_snapshot = compute_data.loc[summary_date]
    unstacked = compute_snapshot.unstack()
    esitmation_buffer = unstacked * float(config.esitmation_buffer)
    total = unstacked.add(esitmation_buffer)

    esitmation_buffer = esitmation_buffer.rename({col: '%s Buffer' % col for col in esitmation_buffer.columns}, axis=1)
    esitmation_buffer = esitmation_buffer.astype(int)
    total = total.rename({col: '%s Total' % col for col in total.columns}, axis=1)
    total = total.astype(int)

    unstacked = unstacked.astype(int)
    combined = pd.concat([unstacked, esitmation_buffer, total], axis=1)
    combined = combined.reindex(columns=sorted(list(combined.columns)))
    combined.sort_index(inplace=True)
    return combined
