# -*- coding: utf-8 -*-
"""
xlsxwriter-ээр үүсгэсэн бүх Excel тайланд тоон баганыг агуулгадаа тааруулна:
тоо багтахгүй "###" болохоос сэргийлж өргөсгөнө, хэт өргөн бол нарийсгана.

Тоон нүд бүрийн харагдах уртыг (тоон формат, фонтын хэмжээгээр) тэмдэглэж, workbook хадгалах үед
тоо агуулсан баганын өргөнийг = max(хамгийн урт тоо, тухайн баганын бичвэр (гарчиг)) болгоно.
Бичвэр нь баганыг тайлангийн тохируулснаас өргөсгөхгүй. Цэвэр бичвэр багана, нэгтгэсэн (merge) нүд,
нуусан баганад хүрэхгүй.
"""
import logging
import re

from xlsxwriter.workbook import Workbook
from xlsxwriter.worksheet import Worksheet

_logger = logging.getLogger(__name__)

DEFAULT_COL_WIDTH = 8.43
DEFAULT_FONT_SIZE = 11
# Томъёоны бодсон утга хадгалагдаагүй (0) үед нийлбэр нь баганын бусад тооноос том байдаг тул нэмэх тэмдэгт
FORMULA_EXTRA_CHARS = 3
MIN_NUMERIC_COL_WIDTH = 6


def _literal_chars(section):
    """Тоон форматын тэмдэгт бус (₮, %, хаалт, хоосон зай гэх мэт) хэсгийн урт."""
    quoted = sum(len(q) for q in re.findall(r'"([^"]*)"', section))
    section = re.sub(r'"[^"]*"', '', section)
    section = re.sub(r'\[[^\]]*\]', '', section)
    # _x, *x нь зай/дүүргэлт; \x нь шууд тэмдэгт
    section = re.sub(r'[_*]\S', ' ', section)
    section = re.sub(r'\\(\S)', r'\1', section)
    return quoted + len([c for c in section if c not in '#0?,.'])


def _number_text_length(number, cell_format):
    """Тухайн форматаар харагдах тооны тэмдэгтийн ойролцоо урт."""
    num_format = cell_format.num_format if cell_format is not None else 0
    if not isinstance(num_format, str) or num_format.lower() == 'general' or not num_format:
        # General формат 11 тэмдэгтээс урт тоог товчилдог
        return min(len(repr(number)), 11)
    sections = num_format.split(';')
    section = sections[1] if number < 0 and len(sections) > 1 else sections[0]
    decimals = 0
    if '.' in section:
        decimals = len(re.findall(r'[0#?]', section.split('.', 1)[1].split('"')[0]))
    text = '{:,.{}f}'.format(abs(number), decimals) if ',' in section else '{:.{}f}'.format(abs(number), decimals)
    sign = 1 if number < 0 and len(sections) == 1 else 0
    return len(text) + sign + _literal_chars(section)


def _required_width(length, cell_format):
    font_size = DEFAULT_FONT_SIZE
    bold = False
    if cell_format is not None:
        font_size = cell_format.font_size or DEFAULT_FONT_SIZE
        bold = bool(cell_format.bold)
    scale = font_size / DEFAULT_FONT_SIZE * (1.1 if bold else 1.0)
    return length * scale + 1.5


def _is_multi_column_merge(worksheet, row, col):
    """merge_range() нь нэгтгэлийг бүртгээд дараа нь утгаа бичдэг тул сүүлийн нэгтгэлийг шалгахад хангалттай."""
    merges = getattr(worksheet, 'merge', None)
    if not merges:
        return False
    first_row, first_col, last_row, last_col = merges[-1]
    return first_row == row and first_col == col and last_col != first_col


def _record(worksheet, row, col, width, key='_numeric_widths'):
    if _is_multi_column_merge(worksheet, row, col):
        return
    widths = worksheet.__dict__.setdefault(key, {})
    if width > widths.get(col, 0.0):
        widths[col] = width


def _text_length(string, cell_format):
    lines = str(string).split('\n')
    if cell_format is not None and cell_format.text_wrap:
        # Мөр шилждэг бичвэр хамгийн урт үгэндээ л багтах шаардлагатай
        return max((len(word) for line in lines for word in line.split()), default=0)
    return max((len(line) for line in lines), default=0)


_orig_write_number = Worksheet._write_number
_orig_write_formula = Worksheet._write_formula
_orig_write_string = Worksheet._write_string


def _write_string(self, row, col, string, cell_format=None):
    result = _orig_write_string(self, row, col, string, cell_format)
    try:
        _record(self, row, col, _required_width(_text_length(string, cell_format), cell_format), '_text_widths')
    except Exception:
        _logger.debug('xlsx numeric autofit failed', exc_info=True)
    return result


def _write_number(self, row, col, number, cell_format=None):
    result = _orig_write_number(self, row, col, number, cell_format)
    try:
        _record(self, row, col, _required_width(_number_text_length(number, cell_format), cell_format))
    except Exception:  # Өргөн тооцоолол тайланг хэзээ ч эвдэх ёсгүй
        _logger.debug('xlsx numeric autofit failed', exc_info=True)
    return result


def _write_formula(self, row, col, formula, cell_format=None, value=0):
    result = _orig_write_formula(self, row, col, formula, cell_format, value)
    try:
        if isinstance(value, (int, float)) and value:
            width = _required_width(_number_text_length(value, cell_format), cell_format)
            _record(self, row, col, width)
        elif not _is_multi_column_merge(self, row, col):
            # Утга нь мэдэгдэхгүй: баганын хамгийн өргөн фонттой томъёог л хадгална
            formulas = self.__dict__.setdefault('_numeric_formula_scale', {})
            formulas[col] = max(formulas.get(col, 0.0), _required_width(1, cell_format) - 1.5)
    except Exception:
        _logger.debug('xlsx numeric autofit failed', exc_info=True)
    return result


def _fit_numeric_columns(worksheet):
    widths = dict(worksheet.__dict__.get('_numeric_widths', {}))
    # Утгагүй томъёо (ихэвчлэн нийлбэр): баганын хамгийн урт тооноос FORMULA_EXTRA_CHARS-аар урт гэж үзнэ
    for col, scale in worksheet.__dict__.get('_numeric_formula_scale', {}).items():
        if widths.get(col):
            widths[col] += FORMULA_EXTRA_CHARS * scale
    text_widths = worksheet.__dict__.get('_text_widths', {})
    # Зөвхөн тоо агуулсан баганыг тааруулна; цэвэр бичвэр баганын тохиргоо хэвээр
    for col, number_width in widths.items():
        info = worksheet.col_info.get(col)
        current = info[0] if info and info[0] is not None else DEFAULT_COL_WIDTH
        if info and (info[2] or current == 0):
            continue  # нуусан багана
        # Гарчиг зэрэг бичвэр тасрахгүй ч баганыг тайлангийн тохируулснаас өргөсгөхгүй
        text_width = min(text_widths.get(col, 0.0), current)
        width = round(max(number_width, text_width, MIN_NUMERIC_COL_WIDTH), 2)
        if width == current:
            continue
        if info:
            info[0] = width
        else:
            worksheet.col_info[col] = [width, None, False, 0, False, False]


_orig_store_workbook = Workbook._store_workbook


def _store_workbook(self):
    for worksheet in self.worksheets():
        try:
            if not worksheet.constant_memory:
                _fit_numeric_columns(worksheet)
        except Exception:
            _logger.debug('xlsx numeric autofit failed', exc_info=True)
    return _orig_store_workbook(self)


Worksheet._write_number = _write_number
Worksheet._write_formula = _write_formula
Worksheet._write_string = _write_string
Workbook._store_workbook = _store_workbook
