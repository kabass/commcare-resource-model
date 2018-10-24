from abc import ABC, abstractmethod, abstractproperty
from collections import namedtuple

import pandas as pd
import numpy as np

DateRange = namedtuple('DateRange', 'start, end')


def models_by_slug():
    df_models = [
        DateRangeValueModel,
        DateValueModel,
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


class DateValueModel(DFModel):
    slug = 'date_value'

    def __init__(self, name, values):
        self.name = name
        self.values = values

    def data_frame(self, current_data_frame):
        index = pd.DatetimeIndex([d for d, v in self.values], freq='MS')
        return pd.DataFrame({self.name: [v for d, v in self.values]}, index=index)


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
