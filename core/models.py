from abc import ABC, abstractmethod, abstractproperty
from collections import namedtuple

import pandas as pd


DateRange = namedtuple('DateRange', 'start, end')


def models_by_slug():
    df_models = [
        DateRangeValueModel,
        PerUserModel,
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
            [pd.DataFrame({'users': range_[2]}, index=pd.date_range(range_[0], range_[1], freq='MS'))
            for range_ in self.ranges]
        )


class PerUserModel(DFModel):
    slug = 'per_user'

    def __init__(self, name, items_per_user):
        self.name = name
        self.items_per_user = items_per_user

    @property
    def dependant_fields(self):
        return ['users']

    def data_frame(self, current_data_frame):
        items = current_data_frame.users * self.items_per_user
        items.name = self.name
        return items


class DerivedModel(DFModel):
    """Base class for models that are derived from other fields"""
    @property
    @abstractmethod
    def func(self):
        raise NotImplemented

    def __init__(self, name, dependant_fields):
        self.name = name
        self._dependant_fields = dependant_fields

    @property
    def dependant_fields(self):
        return self._dependant_fields

    def data_frame(self, current_data_frame):
        fields = self.dependant_fields
        if len(fields) == 1:
            fields = fields[0]
        series = current_data_frame[fields].apply(self.func, axis=1)
        series.name = self.name
        return series


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
        return cumulative


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
        return live_items


class DerivedSum(DerivedModel):
    """Sum multiple fields"""
    slug = 'derived_sum'
    func = sum


class DerivedFactor(DerivedModel):
    """Multiply a single other field by a static factor"""
    slug = 'derived_factor'

    def __init__(self, name, dependant_field, factor):
        super(DerivedFactor, self).__init__(name, [dependant_field])
        self.factor = factor

    @property
    def func(self):
        def _mul(val, **kwargs):
            return val * self.factor

        return _mul


# class  PersonCaseModel
# month 1 = 1200 cases created
# month >1 = 1
