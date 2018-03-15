from abc import ABC, abstractmethod, abstractproperty
from collections import namedtuple

import pandas as pd
import numpy as np

DateRange = namedtuple('DateRange', 'start, end')


def models_by_slug():
    df_models = [
        DateRangeValueModel,
        CumulativeModel,
        LimitedLifetimeModel,
        DerivedSum,
        DerivedFactor,
    ]

    return {
        model.slug: model for model in df_models
    }


class DFModel(ABC):
    @property
    @abstractmethod
    def slug(self):
        raise NotImplemented

    @abstractmethod
    def data_frame(self, current_data_frame):
        raise NotImplemented

    @property
    def dependant_fields(self):
        return []

    def can_run(self, current_data_frame):
        if not self.dependant_fields:
            return True

        columns = set(current_data_frame.columns)
        return not bool(set(self.dependant_fields) - columns)


class DateRangeValueModel(DFModel):
    slug = 'date_range_value'

    def __init__(self, name, ranges):
        self.name = name
        self.ranges = ranges

    def data_frame(self, current_data_frame):
        return pd.concat(
            [pd.DataFrame({self.name: range_[2]}, index=pd.date_range(range_[0], range_[1], freq='MS'))
            for range_ in self.ranges]
        )


class CumulativeModel(DFModel):
    """Items that accumulate over time.
    For example form submissions."""
    slug = 'cumulative'

    def __init__(self, name, dependant_field):
        self.name = name
        self.dependant_field = dependant_field

    @property
    def dependant_fields(self):
        return [self.dependant_field]

    def data_frame(self, current_data_frame):
        cumulative = current_data_frame[self.dependant_field].cumsum()
        cumulative.name = self.name
        return pd.DataFrame([cumulative]).T


class LimitedLifetimeModel(CumulativeModel):
    """Extends the cumulative model by giving items a finite lifespan"""
    slug = 'cumulative_limited_lifespan'

    def __init__(self, name, dependant_field, lifespan):
        super(LimitedLifetimeModel, self).__init__(name, dependant_field)
        self.lifespan = lifespan

    def data_frame(self, current_data_frame):
        cum_data = super(LimitedLifetimeModel, self).data_frame(current_data_frame)
        live_items = cum_data - cum_data.shift(self.lifespan)
        live_items = live_items.fillna(cum_data[0:self.lifespan])
        live_items.name = self.name
        return live_items.astype(int)


class DerivedModel(DFModel):
    """Base class for models that are derived from other fields"""
    @property
    @abstractmethod
    def func(self):
        raise NotImplemented

    def __init__(self, name, dependant_fields, start_with=None):
        self.name = name
        self._dependant_fields = dependant_fields
        self.start_with = start_with

    @property
    def dependant_fields(self):
        return self._dependant_fields

    def data_frame(self, current_data_frame):
        fields = self.dependant_fields
        if len(fields) == 1:
            fields = fields[0]
        series = current_data_frame[fields].apply(self.func, axis=1)
        series.name = self.name
        if self.start_with:
            series[0] += self.start_with
        return pd.DataFrame([series]).T


class DerivedSum(DerivedModel):
    """Sum multiple fields"""
    slug = 'derived_sum'
    func = sum


class DerivedFactor(DerivedModel):
    """Multiply a single other field by a static factor"""
    slug = 'derived_factor'

    def __init__(self, name, dependant_field, factor, start_with=0):
        super(DerivedFactor, self).__init__(name, [dependant_field], start_with)
        self.factor = factor

    @property
    def func(self):
        def _mul(val, **kwargs):
            return val * self.factor

        return _mul


class ComputeModel(object):
    def __init__(self, service_name, service_def):
        self.service_name = service_name
        self.service_def = service_def

    def _get_process_series(self, process_def, usage_data):
        if process_def.static_number:
            return pd.Series([process_def.static_number] * len(usage_data), index=usage_data.index)
        else:
            return (usage_data / process_def.capacity).map(np.ceil)

    def data_frame(self, current_data_frame):
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
            return pd.concat([cores, ram, vms.map(np.ceil)], keys=['CPU', 'RAM', 'VMs'], axis=1)
        elif self.service_def.usage_capacity_per_node:
            nodes = (usage / self.service_def.usage_capacity_per_node).map(np.ceil)
            with_min = pd.concat([
                nodes,
                pd.Series([self.service_def.min_nodes] * len(nodes), index=nodes.index)
            ], axis=1)
            nodes = with_min.max(1)
            return pd.concat([
                nodes * self.service_def.process.cores_per_node,
                nodes * self.service_def.process.ram_per_node,
                nodes
            ], keys=['CPU', 'RAM', 'VMs'], axis=1)
        else:
            nodes = pd.Series([0] * len(usage), index=usage.index)
            return pd.concat([nodes, nodes, nodes], keys=['CPU', 'RAM', 'VMs'], axis=1)
