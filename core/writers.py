from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from itertools import zip_longest

import pandas as pd
from numpy import nan
from pandas.io.formats.terminal import get_terminal_size

from core.utils import format_date


class BaseWriter(ABC):
    @abstractmethod
    def write_data_frame(self, data_frame, sheet_name, index_label, header=None, has_total_row=False):
        raise NotImplemented

    def save(self):
        pass


class ExcelWriter(BaseWriter):
    spacing = 2

    def __init__(self, ouput_path):
        self.writer = pd.ExcelWriter(ouput_path, engine='xlsxwriter')
        self.workbook = self.writer.book
        self.heading_format = self.workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#CCFFFF',
        })
        self.index_format = self.workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
        })
        self.total_row_format = self.workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'right',
        })
        self.sheet_positions = defaultdict(int)
        self.sheet_col_widths = defaultdict(list)

    def _workbook(self, sheet_name):
        sheet = self.workbook.get_worksheet_by_name(sheet_name)
        if sheet is None:
            sheet = self.workbook.add_worksheet(sheet_name)
            self.writer.sheets[sheet_name] = sheet
        return sheet

    def write_data_frame(self, data_frame, sheet_name, index_label, header=None, has_total_row=False):
        sheet_position = self.sheet_positions[sheet_name]
        sheet = self._workbook(sheet_name)
        if header:
            cols = len(data_frame.columns)
            sheet.merge_range(sheet_position, 0, sheet_position, cols, header, self.heading_format)
            sheet_position += 1

        data_frame.to_excel(
            self.writer, sheet_name,
            index_label=index_label if not header else None, startrow=sheet_position
        )

        self.sheet_positions[sheet_name] = sheet_position + len(data_frame) + self.spacing

        sheet_position += 3 if isinstance(data_frame.columns, pd.MultiIndex) else 1

        for i, index_label in enumerate(data_frame.index):
            if isinstance(index_label, datetime):
                index_label = format_date(index_label)
            sheet.write_string(sheet_position + i, 0, index_label, self.index_format)

        if has_total_row:
            total_row = data_frame.tail(1).values[0]
            total_row_pos = sheet_position + len(data_frame) - 1
            for col, val in enumerate(total_row):
                val = pd.options.display.float_format(val) if val is not nan else ''
                sheet.write_string(total_row_pos, col + 1, val, self.total_row_format)

        self.update_col_widths(data_frame, sheet_name)
        self.sheet_positions[sheet_name] = sheet_position + len(data_frame) + self.spacing

    def update_col_widths(self, data_frame, sheet_name):
        def get_col_widths(dataframe):
            idx_max = max([len(str(s)) for s in dataframe.index.values] + [len(str(dataframe.index.name))])
            columns = list(dataframe.columns)
            if isinstance(dataframe.columns[0], tuple):
                # for multi-indexes get the longest column text
                columns = [
                    sorted(cols, key=lambda c: len(c), reverse=True)[0]
                    for cols in columns
                ]
            return (
                    [idx_max] +
                    [max([len(str(s)) for s in dataframe[col].values] +
                         [len(col)]) for col in columns]
            )

        current_col_widths = self.sheet_col_widths[sheet_name]
        col_widths = get_col_widths(data_frame)
        if not current_col_widths:
            self.sheet_col_widths[sheet_name] = col_widths
        else:
            new_widths = [max(cw) for cw in zip_longest(current_col_widths, col_widths, fillvalue=0)]
            self.sheet_col_widths[sheet_name] = new_widths

    def save(self):
        self.write_col_widths()
        self.writer.save()

    def write_col_widths(self):
        for sheet_name, widths in self.sheet_col_widths.items():
            sheet = self._workbook(sheet_name)
            for i, width in enumerate(widths):
                sheet.set_column(i, i, width)


class ConsoleWriter(BaseWriter):
    def __init__(self):
        self.sheets = set()
        pd.set_option('display.width', get_terminal_size().columns)

    def write_data_frame(self, data_frame, sheet_name, index_label, header=None, has_total_row=False):
        if sheet_name not in self.sheets:
            header1 = '=' * 20
            print('\n%s %s %s' % (header1, sheet_name, header1))
            self.sheets.add(sheet_name)
        if index_label:
            header2 = '-' * 10
            print('\n%s %s %s' % (header2, index_label, header2))
        print()
        print(data_frame)
