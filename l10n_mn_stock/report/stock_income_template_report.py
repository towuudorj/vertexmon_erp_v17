# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import date_utils
import base64
import io
import json
import xlsxwriter
from io import BytesIO
from PIL import Image


class StockIncomeTemplateReport(models.TransientModel):
    """
        Орлогын баримтын хоосон загвар (Excel)
    """
    _name = "stock.income.template.report"
    _description = "Stock income blank template - Mongolia"

    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                 default=lambda self: self.env.company)
    line_count = fields.Integer(string=u'Хоосон мөрийн тоо', default=20, required=True)

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_logo': self.company_id.logo,
            'line_count': self.line_count,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                'model': 'stock.income.template.report',
                'output_format': 'xlsx',
                'options': json.dumps(data, default=date_utils.json_default),
                'report_name': 'stock_income_template_report',
            }
        }

    def _insert_logo(self, sheet, logo_b64, row=0, col=0, target_w=150, target_h=45):
        if not logo_b64:
            return
        try:
            image_bytes = base64.b64decode(logo_b64)
            img = Image.open(BytesIO(image_bytes))
            orig_w, orig_h = img.size
            sheet.insert_image(row, col, 'logo.png', {
                'image_data': BytesIO(image_bytes),
                'x_scale': target_w / orig_w if orig_w else 1,
                'y_scale': target_h / orig_h if orig_h else 1,
            })
        except Exception:
            pass

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(u'Орлогын баримт')

        small = workbook.add_format({'align': 'right', 'font_size': 9})
        title = workbook.add_format({'align': 'center', 'font_size': 14, 'bold': True})
        label = workbook.add_format({'align': 'center', 'font_size': 10})
        label_bold = workbook.add_format({'align': 'center', 'font_size': 10, 'bold': True, 'underline': True})
        hint = workbook.add_format({'align': 'center', 'font_size': 9, 'italic': True})
        header = workbook.add_format({'align': 'center', 'font_size': 11, 'bold': True, 'border': 1, 'bg_color': '#F0F0F0'})
        cell = workbook.add_format({'align': 'center', 'font_size': 11, 'border': 1})
        cell_left = workbook.add_format({'align': 'left', 'font_size': 11, 'border': 1})
        total_label = workbook.add_format({'align': 'center', 'font_size': 11, 'border': 1, 'bold': True})

        sheet.set_column('A:A', 4)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:F', 13)

        sheet.set_row(0, 45)
        self._insert_logo(sheet, data.get('company_logo'), 0, 0)

        sheet.merge_range('A2:F2', u'Сангийн сайдын 2017 оны 12 дугаар сарын 5 өдрийн 347 тоот тушаалын хавсралт', small)
        sheet.merge_range('A3:F3', u'Орлогын баримт', title)
        sheet.merge_range('A4:F4', u'№', label)

        row = 5
        sheet.write(row, 0, data.get('company_name') or '', label_bold)
        sheet.write(row, 3, '', label_bold)
        row += 1
        sheet.write(row, 0, u'( Байгууллагын нэр )', hint)
        row += 1
        sheet.write(row, 0, '', label)
        sheet.write(row, 3, u'Огноо:', label)
        row += 1
        sheet.write(row, 0, '', label_bold)
        sheet.write(row, 3, u'Дагалдах баримт №:', label)
        row += 1
        sheet.write(row, 0, u'( Бэлтгэн нийлүүлэгчийн нэр )', hint)

        row += 2
        headers = [u'Материалын үнэт зүйлийн нэр, зэрэг, дугаар', u'Код', u'Хэмжих нэгж', u'Нэгж үнэ', u'Тоо', u'Дүн']
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header)

        line_count = data.get('line_count') or 20
        for i in range(line_count):
            row += 1
            sheet.write(row, 0, '', cell_left)
            for col in range(1, 6):
                sheet.write(row, col, '', cell)

        row += 1
        sheet.merge_range(row, 0, row, 3, u'Нийт', total_label)
        sheet.write(row, 4, '', cell)
        sheet.write(row, 5, '', cell)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
