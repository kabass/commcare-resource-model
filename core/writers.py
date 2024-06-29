import os
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from itertools import zip_longest
from numbers import Number

import pandas as pd

from core.utils import format_date


class BaseWriter(ABC):
    @abstractmethod
    def write_data_frame(self, data_frame, sheet_name, index_label, header=None, has_total_row=False):
        raise NotImplemented

    def write_user_counts_horizontal(self, sheet_name, user_count_table):
        pass

    def write_user_counts_vertical(self, sheet_name, user_count_table):
        pass

    def write_config_string(self, config_string):
        pass

    def save(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.save()


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
        self.sub_header_format = self.workbook.add_format({'bold': 1, 'border': 1, 'align': 'center'})
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

    def get_sheet(self, sheet_name):
        sheet = self.workbook.get_worksheet_by_name(sheet_name)
        if sheet is None:
            sheet = self.workbook.add_worksheet(sheet_name)
            self.writer.sheets[sheet_name] = sheet
        return sheet

    def write_user_counts_vertical(self, sheet_name, user_count_table):
        """
        :param user_count_table: list of tuples (date, count)
        :return:
        """
        sheet_position = self.sheet_positions[sheet_name]
        sheet = self.get_sheet(sheet_name)
        sheet.merge_range(sheet_position, 0, sheet_position, 1, 'User counts', self.heading_format)
        sheet_position += 1
        for date, count in user_count_table:
            sheet.write_string(sheet_position, 0, date)
            sheet.write_number(sheet_position, 1, count)
            sheet_position += 1
        self.sheet_positions[sheet_name] = sheet_position + 1

    def write_user_counts_horizontal(self, sheet_name, user_count_table):
        """
        :param user_count_table: list of tuples (date, count)
        :return:
        """
        sheet_position = self.sheet_positions[sheet_name]
        sheet = self.get_sheet(sheet_name)
        sheet.merge_range(sheet_position, 0, sheet_position, len(user_count_table), 'User counts', self.heading_format)
        sheet_position += 1

        sheet.write_string(sheet_position + 1, 0, 'User count', self.index_format)

        col = 1
        for date, count in user_count_table:
            sheet.write_string(sheet_position, col, date, cell_format=self.sub_header_format)
            sheet.write_number(sheet_position + 1, col, count)
            col += 1
        self.sheet_positions[sheet_name] = sheet_position + 3

    def write_data_frame(self, data_frame, sheet_name, index_label, header=None, has_total_row=False):
        sheet_position = self.sheet_positions[sheet_name]
        sheet = self.get_sheet(sheet_name)
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
                val = pd.options.display.float_format(val) if pd.notna(val) and isinstance(val, Number) else ''
                sheet.write_string(total_row_pos, col + 1, val, self.total_row_format)

        self.update_col_widths(data_frame, sheet_name)
        self.sheet_positions[sheet_name] = sheet_position + len(data_frame) + self.spacing

    def update_col_widths(self, data_frame, sheet_name):
        def get_col_widths(dataframe):
            idx_max = max([len(str(s)) for s in dataframe.index.values] + [len(str(dataframe.index.name))])
            columns = list(dataframe.columns)
            if isinstance(columns[0], tuple):
                lengths = [
                    max([len(str(s)) for s in dataframe[col[0]][col[1]].values] + [len(col[0]), len(col[1])])
                    for col in columns
                ]
            else:
                lengths = [
                    max([len(str(s)) for s in dataframe[col].values] + [len(col)])
                    for col in columns
                ]
            return [idx_max] + lengths

        current_col_widths = self.sheet_col_widths[sheet_name]
        col_widths = get_col_widths(data_frame)
        if not current_col_widths:
            self.sheet_col_widths[sheet_name] = col_widths
        else:
            new_widths = [max(cw) for cw in zip_longest(current_col_widths, col_widths, fillvalue=0)]
            self.sheet_col_widths[sheet_name] = new_widths

    def write_config_string(self, config_string):
        sheet = self.get_sheet('Config')
        width = 0
        lines = config_string.split('\n')
        for i, line in enumerate(lines):
            sheet.write_string(i, 0, line)
            width = max(width, len(line))
        sheet.set_column(0, 0, width)

    def save(self):
        self.write_col_widths()
        self.writer._save()

    def write_col_widths(self):
        for sheet_name, widths in self.sheet_col_widths.items():
            sheet = self.get_sheet(sheet_name)
            for i, width in enumerate(widths):
                sheet.set_column(i, i, width)


class ConsoleWriter(BaseWriter):
    def __init__(self):
        self.sheets = set()
        pd.set_option('display.width', int(os.getenv('COLUMNS', '80')))

    def write_data_frame(self, data_frame, sheet_name, index_label, header=None, has_total_row=False):
        if sheet_name not in self.sheets:
            header1 = '=' * 20
            print('\n%s %s %s' % (header1, sheet_name, header1))
            self.sheets.add(sheet_name)
        if index_label or header:
            header2 = '-' * 10
            print('\n%s %s %s' % (header2, header or index_label, header2))
        print()
        print(data_frame)
