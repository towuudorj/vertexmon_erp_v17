# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import date_utils
import base64
import io
import json
import xlsxwriter
from io import BytesIO
from PIL import Image


class StockWorkwearTemplateReport(models.TransientModel):
    """
        Ажлын хувцас картын хоосон загвар (Excel)
    """
    _name = "stock.workwear.template.report"
    _description = "Stock workwear card blank template - Mongolia"

    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                 default=lambda self: self.env.company)
    line_count = fields.Integer(string=u'Хоосон мөрийн тоо', default=10, required=True)

    def action_print_xls_report(self):
        data = {
            'company_logo': self.company_id.logo,
            'line_count': self.line_count,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                'model': 'stock.workwear.template.report',
                'output_format': 'xlsx',
                'options': json.dumps(data, default=date_utils.json_default),
                'report_name': 'stock_workwear_template_report',
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
        sheet = workbook.add_worksheet(u'Ажлын хувцас карт')

        title = workbook.add_format({'align': 'center', 'font_size': 14, 'bold': True})
        label = workbook.add_format({'align': 'left', 'font_size': 11, 'bold': True, 'border': 2})
        blank = workbook.add_format({'align': 'left', 'font_size': 11, 'border': 2})
        header = workbook.add_format({'align': 'center', 'font_size': 11, 'bold': True, 'border': 2, 'bg_color': '#F0F0F0'})
        cell = workbook.add_format({'align': 'center', 'font_size': 11, 'border': 2})
        cell_left = workbook.add_format({'align': 'left', 'font_size': 11, 'border': 2})

        sheet.set_column('A:A', 30)
        sheet.set_column('B:D', 18)

        sheet.set_row(0, 45)
        self._insert_logo(sheet, data.get('company_logo'), 0, 0)

        sheet.merge_range('A2:D2', u'Хамгаалах хэрэгсэл эзэмшигчийн карт', title)

        row = 3
        fields_labels = [u'Ажилтны овог:', u'Ажилтны нэр:', u'Ажилтны РД:', u'Харьяалагдах алба:', u'Албан тушаал:']
        for lbl in fields_labels:
            sheet.merge_range(row, 0, row, 1, lbl, label)
            sheet.merge_range(row, 2, row, 3, '', blank)
            row += 1

        row += 1
        headers = [u'Ажлын хувцас', u'Тоо', u'Хүлээлгэн өгсөн', u'Хүлээн авсан']
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header)

        line_count = data.get('line_count') or 10
        for i in range(line_count):
            row += 1
            sheet.write(row, 0, '', cell_left)
            for col in range(1, 4):
                sheet.write(row, col, '', cell)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
