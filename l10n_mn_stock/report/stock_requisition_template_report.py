# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import date_utils
import base64
import io
import json
import xlsxwriter
from io import BytesIO
from PIL import Image


class StockRequisitionTemplateReport(models.TransientModel):
    """
        Шаардах хуудасны хоосон загвар (Excel)
    """
    _name = "stock.requisition.template.report"
    _description = "Stock requisition blank template - Mongolia"

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
                'model': 'stock.requisition.template.report',
                'output_format': 'xlsx',
                'options': json.dumps(data, default=date_utils.json_default),
                'report_name': 'stock_requisition_template_report',
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
        sheet = workbook.add_worksheet(u'Шаардах хуудас')

        title = workbook.add_format({'align': 'center', 'font_size': 14, 'bold': True})
        label = workbook.add_format({'align': 'left', 'font_size': 11, 'bold': True})
        blank_line = workbook.add_format({'align': 'left', 'font_size': 11, 'bottom': 1})
        hint = workbook.add_format({'align': 'center', 'font_size': 9, 'italic': True, 'font_color': '#666666'})
        header = workbook.add_format({'align': 'center', 'font_size': 11, 'bold': True, 'border': 1, 'bg_color': '#F0F0F0'})
        cell = workbook.add_format({'align': 'center', 'font_size': 11, 'border': 1})
        cell_left = workbook.add_format({'align': 'left', 'font_size': 11, 'border': 1})
        sig = workbook.add_format({'align': 'left', 'font_size': 10})

        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:G', 14)

        sheet.set_row(0, 45)
        self._insert_logo(sheet, data.get('company_logo'), 0, 0)

        sheet.merge_range('A2:G2', data.get('company_name') or '', title)
        sheet.merge_range('A3:G3', u'ШААРДАХ ХУУДАС №', title)

        row = 5
        sheet.write(row, 0, u'Он, сар, өдөр:', label)
        row += 1
        sheet.write(row, 0, u'Хэнээс:', label)
        sheet.merge_range(row, 1, row, 6, '', blank_line)
        row += 1
        sheet.merge_range(row, 1, row, 6, u'(овог, нэр, албан тушаал)', hint)
        row += 1
        sheet.write(row, 0, u'Хаана:', label)
        sheet.merge_range(row, 1, row, 6, '', blank_line)
        row += 1
        sheet.merge_range(row, 1, row, 6, u'(овог, нэр, албан тушаал)', hint)
        row += 1
        sheet.write(row, 0, u'Зориулалт:', label)
        sheet.merge_range(row, 1, row, 6, '', blank_line)

        row += 2
        sheet.write(row, 0, u'Харилцагчийн нэр:', label)
        sheet.merge_range(row, 1, row, 3, '', blank_line)
        sheet.write(row, 4, u'Буцаж ирэх огноо:', label)
        sheet.merge_range(row, 5, row, 6, '', blank_line)

        row += 2
        headers = [u'№', u'Барааны нэр', u'Код', u'Хэмжих нэгж', u'Хүссэн', u'Зөвшөөрсөн', u'Олгосон']
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header)

        line_count = data.get('line_count') or 20
        for i in range(1, line_count + 1):
            row += 1
            sheet.write(row, 0, i, cell)
            sheet.write(row, 1, '', cell_left)
            for col in range(2, 7):
                sheet.write(row, col, '', cell)

        row += 3
        signatures = [
            (u'Зөвшөөрсөн:', u'Олгосон нярав:'),
            (u'Санхүү эрхэлсэн захирал:', u'Хүлээн авсан:'),
            (u'Нягтлан бодогч:', u'Шаардах хуудас бичсэн:'),
            (u'Санхүүгийн шинжээч:', None),
        ]
        for left_label, right_label in signatures:
            sheet.write(row, 0, left_label, label)
            sheet.merge_range(row, 1, row, 2, u'____________________ / ___________________ /', sig)
            if right_label:
                sheet.write(row, 4, right_label, label)
                sheet.merge_range(row, 5, row, 6, u'____________________ / ___________________ /', sig)
            row += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
