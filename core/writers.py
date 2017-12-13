from abc import ABC, abstractmethod

import pandas as pd
from collections import defaultdict
from pandas.io.formats.terminal import get_terminal_size


class BaseWriter(ABC):
    @abstractmethod
    def write_data_frame(self, data_frame, sheet_name, index_label):
        raise NotImplemented

    def save(self):
        pass


class ExcelWriter(BaseWriter):
    spacing = 2

    def __init__(self, ouput_path):
        self.writer = pd.ExcelWriter(ouput_path)
        self.sheet_positions = defaultdict(int)

    def write_data_frame(self, data_frame, sheet_name, index_label):
        sheet_position = self.sheet_positions[sheet_name]
        data_frame.to_excel(
            self.writer, sheet_name,
            index_label=index_label, startrow=sheet_position
        )
        self.sheet_positions[sheet_name] = sheet_position + len(data_frame) + self.spacing

    def save(self):
        self.writer.save()


class ConsoleWriter(BaseWriter):
    def __init__(self):
        self.sheets = set()
        pd.set_option('display.width', get_terminal_size().columns)

    def write_data_frame(self, data_frame, sheet_name, index_label):
        if sheet_name not in self.sheets:
            print('\n========== %s ==========' % sheet_name)
            self.sheets.add(sheet_name)
        if index_label:
            print('\n----- %s -----' % index_label)
        print()
        print(data_frame)
