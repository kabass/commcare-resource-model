import math
from collections import namedtuple, OrderedDict

import pandas as pd

from core.utils import format_date, to_storage_display_unit, tenth_round

ServiceSummary = namedtuple('ServiceSummary', 'service_summary storage_by_group')
SummaryComparison = namedtuple('SummaryComparison', 'storage_by_category storage_by_group compute')


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
        pd.concat(storage_by_cat_series, axis=1, keys=keys + ['Group']),
        pd.concat(storage_by_group_series, axis=1, keys=keys),
        pd.concat(compute_series, axis=1, keys=keys),
    )


def summarize_service_data(config, service_data, summary_date):
    snapshot = service_data.loc[summary_date]
    storage_units = config.storage_display_unit
    to_display = to_storage_display_unit(storage_units)
    to_gb = to_storage_display_unit('GB')
    summary_df = pd.DataFrame()
    for service_name, service_def in config.services.items():
        service_snapshot = snapshot[service_name]
        compute = service_snapshot['Compute']
        data_storage = service_snapshot['Data Storage']['storage']
        os_storage = service_snapshot['OS Storage']['storage']
        ram_buffer = compute['RAM'] * float(config.estimation_buffer)
        cpu_buffer = compute['CPU'] * float(config.estimation_buffer)
        node_buffer = math.ceil(compute['VMs'] * float(config.estimation_buffer))
        vms_total = math.ceil(compute['VMs'] + node_buffer)

        data_storage_per_vm = data_storage / compute['VMs']
        data_storage_total = data_storage_per_vm * vms_total

        os_storage_buffer = node_buffer * config.vm_os_storage_gb * (1000.0 ** 3)
        data = OrderedDict([
            ('Cores Per VM', service_def.process.cores_per_node),
            ('Cores Total', math.ceil(compute['CPU'] + cpu_buffer)),
            ('Cores Buffer', cpu_buffer),
            ('RAM Per VM', service_def.process.ram_per_node),
            ('RAM Total (GB)', math.ceil(compute['RAM'] + ram_buffer)),
            ('RAM Buffer', ram_buffer),
            ('Data Storage Per VM (GB)', math.ceil(to_gb((data_storage_per_vm) if compute['VMs'] else 0))),
            ('Data Storage Total (%s)' % storage_units, to_display(data_storage_total)),
            ('Data Storage Total Rounded (%s)' % storage_units, tenth_round(to_display(math.ceil(data_storage_total)))),
            # ('Data Storage Buffer (GB)', to_gb(data_storage_buffer)),
            ('VMs Total', vms_total),
            ('VM Buffer', node_buffer),
            ('OS Storage Total (Bytes)', os_storage + os_storage_buffer),
            ('OS Storage Total (GB)', math.ceil(to_gb(os_storage + os_storage_buffer))),
            ('Storage Group', service_def.storage.group)
        ])
        combined = pd.Series(name=service_name, data=data)
        summary_df[service_name] = combined

    summary_by_service = summary_df.T
    summary_by_service.sort_index(inplace=True)

    by_type = summary_by_service.groupby('Storage Group')['Data Storage Total Rounded (%s)' % storage_units].sum()
    if config.vm_os_storage_group not in by_type:
        by_type[config.vm_os_storage_group] = 0
    by_type[config.vm_os_storage_group] += math.ceil(to_display(summary_by_service['OS Storage Total (Bytes)'].sum()))

    by_type.index.name = None
    storage_by_group = pd.DataFrame({
        'Rounded Total (%s)' % storage_units: by_type,
    })

    summary_by_service.drop('OS Storage Total (Bytes)', axis=1, inplace=True)
    total = summary_by_service.sum()
    total.name = 'Total'
    summary_by_service = summary_by_service.append(total, ignore_index=False)

    storage_by_group.sort_index(inplace=True)
    return ServiceSummary(summary_by_service, storage_by_group)


def compare_summaries(config, summaries_by_date):
    data_storage_series = []
    storage_by_group_series = []
    compute_series = []
    dates = sorted(list(summaries_by_date))
    storage_units = config.storage_display_unit
    for date in dates:
        summary_data = summaries_by_date[date]
        data_storage_series.append(summary_data.service_summary['Data Storage Total Rounded (%s)' % storage_units])
        storage_by_group_series.append(summary_data.storage_by_group['Rounded Total (%s)' % storage_units])
        compute = summary_data.service_summary[['Cores Total', 'RAM Total (GB)', 'VMs Total']]
        compute = compute.rename({'Cores Total': 'Cores', 'RAM Total (GB)': 'RAM (GB)', 'VMs Total': 'VMs'}, axis=1)
        compute_series.append(compute)

    first_date = list(summaries_by_date)[0]
    group_series = summaries_by_date[first_date].service_summary['Storage Group']
    data_storage_series.append(group_series)

    keys = [format_date(date) for date in dates]

    storage_by_cat = pd.concat(data_storage_series, axis=1, keys=keys + ['Group'])
    storage_by_cat = storage_by_cat[storage_by_cat != 0.0].dropna(how='all')
    storage_by_cat = storage_by_cat.drop('Total')

    storage_by_group = pd.concat(storage_by_group_series, axis=1, keys=keys)

    compute = pd.concat(compute_series, axis=1, keys=keys)
    compute = compute[compute > 0].dropna()
    return SummaryComparison(storage_by_cat, storage_by_group, compute)
