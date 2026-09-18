# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import date_utils
import base64
import io
import json
import xlsxwriter
from io import BytesIO
from PIL import Image


class SaleOrderTemplateReport(models.TransientModel):
    """
        Борлуулалтын захиалгын хоосон загвар (Excel)
    """
    _name = "sale.order.template.report"
    _description = "Sale order blank template - Mongolia"

    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                 default=lambda self: self.env.company)
    line_count = fields.Integer(string=u'Хоосон мөрийн тоо', default=15, required=True)

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_street': self.company_id.street,
            'company_logo': self.company_id.logo,
            'line_count': self.line_count,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                'model': 'sale.order.template.report',
                'output_format': 'xlsx',
                'options': json.dumps(data, default=date_utils.json_default),
                'report_name': 'sale_order_template_report',
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
        sheet = workbook.add_worksheet(u'Борлуулалтын захиалга')

        title = workbook.add_format({'align': 'center', 'font_size': 14, 'bold': True})
        label = workbook.add_format({'align': 'left', 'font_size': 10})
        blank_line = workbook.add_format({'align': 'left', 'font_size': 10, 'bottom': 1})
        header = workbook.add_format({'align': 'center', 'font_size': 11, 'bold': True, 'border': 1, 'bg_color': '#F0F0F0'})
        cell = workbook.add_format({'align': 'center', 'font_size': 11, 'border': 1})
        cell_left = workbook.add_format({'align': 'left', 'font_size': 11, 'border': 1})
        total_label = workbook.add_format({'align': 'right', 'font_size': 11, 'border': 1, 'bold': True})
        sig = workbook.add_format({'align': 'left', 'font_size': 10})

        sheet.set_column('A:A', 4)
        sheet.set_column('B:B', 26)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:G', 13)

        sheet.set_row(0, 45)
        self._insert_logo(sheet, data.get('company_logo'), 0, 0)

        sheet.merge_range('A2:G2', u'БОРЛУУЛАЛТЫН ЗАХИАЛГА №', title)

        row = 3
        sheet.write(row, 0, data.get('company_name') or '', label)
        sheet.write(row, 4, u'Захиалгын огноо:', label)
        sheet.merge_range(row, 5, row, 6, '', blank_line)
        row += 1
        sheet.write(row, 0, data.get('company_street') or '', label)
        sheet.write(row, 4, u'Компанийн нэр:', label)
        sheet.merge_range(row, 5, row, 6, '', blank_line)
        row += 1
        sheet.write(row, 4, u'Ажилтан:', label)
        sheet.merge_range(row, 5, row, 6, '', blank_line)
        row += 1
        sheet.write(row, 4, u'Утас:', label)
        sheet.merge_range(row, 5, row, 6, '', blank_line)
        row += 1
        sheet.write(row, 4, u'Имэйл:', label)
        sheet.merge_range(row, 5, row, 6, '', blank_line)

        row += 2
        headers = [u'№', u'Загвар брэнд Модел', u'Тодорхойлолт', u'Тоо', u'Нэгжийн үнэ /НӨАТ-гүй/', u'Хөнгөлөлт', u'Нийт үнэ']
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header)

        line_count = data.get('line_count') or 15
        for i in range(1, line_count + 1):
            row += 1
            sheet.write(row, 0, i, cell)
            sheet.write(row, 1, '', cell_left)
            sheet.write(row, 2, '', cell_left)
            for col in range(3, 7):
                sheet.write(row, col, '', cell)

        for lbl in [u'НӨАТ-гүй дүн', u'10% НӨАТ', u'НӨАТ орсон дүн']:
            row += 1
            sheet.merge_range(row, 0, row, 5, lbl, total_label)
            sheet.write(row, 6, '', cell)

        row += 3
        sheet.write(row, 0, u'Нийлүүлэх хугацаа:', label)
        row += 1
        sheet.write(row, 0, u'Тэмдэглэл:', label)
        row += 2
        sheet.write(row, 0, u'Гарын үсэг: ____________________ /___________________/', sig)
        row += 2
        sheet.write(row, 0, u'Тамга:', sig)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
