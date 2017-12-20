from collections import namedtuple

import pandas as pd

from core.utils import format_date, to_storage_display_unit, tenth_round

StorageSummary = namedtuple('StorageSummary', 'by_category by_group')
SummaryComparison = namedtuple('SummaryComparison', 'storage_by_category storage_by_group compute')


def compare_summaries(summaries_by_date):
    storage_by_cat_series = []
    storage_by_group_series = []
    compute_series = []
    dates = sorted(list(summaries_by_date))
    for date in dates:
        summary_data = summaries_by_date[date]
        storage_by_cat_series.append(summary_data.storage.by_category['Rounded Total'])
        storage_by_group_series.append(summary_data.storage.by_group['Rounded Total'])
        compute_series.append(summary_data.compute[['CPU Total', 'RAM Total', 'VMs Total']])

    first_date = list(summaries_by_date)[0]
    group_series = summaries_by_date[first_date].storage.by_category['Group']
    storage_by_cat_series.append(group_series)

    keys = [format_date(date) for date in dates]
    storage_by_cat = _combine_summary_data(storage_by_cat_series, keys + ['Group'])
    storage_by_group = _combine_summary_data(storage_by_group_series, keys, False)
    compute = _combine_summary_data(compute_series, keys)
    return SummaryComparison(storage_by_cat, storage_by_group, compute)


def incremental_summaries(summary_comparisons, summary_dates):
    storage_by_cat_series = []
    storage_by_group_series = []
    compute_series = []
    keys = [format_date(date) for date in summary_dates]

    def _get_incremental(loop_count, keys, data):
        key = keys[loop_count]
        if loop_count == 0:
            return data[key]
        else:
            previous_key = keys[loop_count - 1]
            return data[key] - data[previous_key]

    for i, key in enumerate(keys):
        storage_by_cat_series.append(_get_incremental(i, keys, summary_comparisons.storage_by_category))
        storage_by_group_series.append(_get_incremental(i, keys, summary_comparisons.storage_by_group))
        compute_series.append(_get_incremental(i, keys, summary_comparisons.compute))

    storage_by_cat_series.append(summary_comparisons.storage_by_category['Group'])
    return SummaryComparison(
        _combine_summary_data(storage_by_cat_series, keys + ['Group'], False),
        _combine_summary_data(storage_by_group_series, keys, False),
        _combine_summary_data(compute_series, keys, False),
    )


def _combine_summary_data(series, keys, add_total=True):
    df = pd.concat(series, axis=1, keys=keys)
    if add_total:
        total = df.sum(numeric_only=True)
        total.name = 'Total'
        df = df.append(total, ignore_index=False)
    return df


def summarize_storage_data(config, summary_date, storage_data):
    storage_snapshot = storage_data.loc[summary_date]
    esitmation_buffer = storage_snapshot * float(config.esitmation_buffer)
    storage_buffer = storage_snapshot * float(config.storage_buffer)
    total_raw = storage_snapshot + storage_buffer + esitmation_buffer
    storage_units = config.storage_display_unit
    to_display = to_storage_display_unit(storage_units)

    storage_groups = {storage_key: storage_conf.group for storage_key, storage_conf in config.storage.items()}
    storage_groups['VM OS'] = config.vm_os_storage_group

    storage_by_cat = pd.DataFrame({
        'Size': storage_snapshot.map(to_display),
        'Estimation Buffer': esitmation_buffer.map(to_display),
        'Storage Buffer': storage_buffer.map(to_display),
        'Total': total_raw.map(to_display),
        'Rounded Total': total_raw.map(to_display).map(tenth_round),
        'total_raw': total_raw,
        'Group': pd.Series(storage_groups)
    })

    by_type = storage_by_cat.groupby('Group')['Rounded Total'].sum()
    by_type.index.name = None
    storage_by_group = pd.DataFrame({
        'Rounded Total': by_type,
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
