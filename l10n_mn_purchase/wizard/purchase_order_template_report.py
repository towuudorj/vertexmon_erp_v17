# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import date_utils
import base64
import io
import json
import xlsxwriter
from io import BytesIO
from PIL import Image


class PurchaseOrderTemplateReport(models.TransientModel):
    """
        Худалдан авалтын захиалгын хоосон загвар (Excel)
    """
    _name = "purchase.order.template.report"
    _description = "Purchase order blank template - Mongolia"

    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                 default=lambda self: self.env.company)
    line_count = fields.Integer(string=u'Хоосон мөрийн тоо', default=20, required=True)

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_street': self.company_id.street,
            'company_phone': self.company_id.partner_id.phone or self.company_id.phone,
            'company_vat': self.company_id.vat,
            'company_logo': self.company_id.logo,
            'line_count': self.line_count,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                'model': 'purchase.order.template.report',
                'output_format': 'xlsx',
                'options': json.dumps(data, default=date_utils.json_default),
                'report_name': 'purchase_order_template_report',
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
        sheet = workbook.add_worksheet(u'Худалдан авалтын захиалга')

        title = workbook.add_format({'align': 'center', 'font_size': 14, 'bold': True})
        section = workbook.add_format({'align': 'left', 'font_size': 11, 'bold': True})
        label = workbook.add_format({'align': 'left', 'font_size': 10})
        blank_line = workbook.add_format({'align': 'left', 'font_size': 10, 'bottom': 1})
        header = workbook.add_format({'align': 'center', 'font_size': 11, 'bold': True, 'border': 1, 'bg_color': '#F0F0F0'})
        cell = workbook.add_format({'align': 'center', 'font_size': 11, 'border': 1})
        cell_left = workbook.add_format({'align': 'left', 'font_size': 11, 'border': 1})
        total_label = workbook.add_format({'align': 'right', 'font_size': 11, 'border': 1, 'bold': True})
        sig = workbook.add_format({'align': 'left', 'font_size': 10})

        sheet.set_column('A:A', 4)
        sheet.set_column('B:B', 32)
        sheet.set_column('C:H', 13)

        sheet.set_row(0, 45)
        self._insert_logo(sheet, data.get('company_logo'), 0, 0)

        sheet.merge_range('A2:H2', u'ХУДАЛДАН АВАЛТЫН ЗАХИАЛГА №', title)

        row = 3
        sheet.write(row, 0, u'Захиалагч:', section)
        sheet.write(row, 4, u'Нийлүүлэгч:', section)
        row += 1
        sheet.write(row, 0, u'Байгууллагын нэр:', label)
        sheet.write(row, 1, data.get('company_name') or '', label)
        sheet.write(row, 4, u'Байгууллагын нэр:', label)
        sheet.merge_range(row, 5, row, 7, '', blank_line)
        row += 1
        sheet.write(row, 0, u'Хаяг:', label)
        sheet.write(row, 1, data.get('company_street') or '', label)
        sheet.write(row, 4, u'Хаяг:', label)
        sheet.merge_range(row, 5, row, 7, '', blank_line)
        row += 1
        sheet.write(row, 0, u'Утас:', label)
        sheet.write(row, 1, data.get('company_phone') or '', label)
        sheet.write(row, 4, u'Утас:', label)
        sheet.merge_range(row, 5, row, 7, '', blank_line)
        row += 1
        sheet.write(row, 0, u'Регистрийн дугаар:', label)
        sheet.write(row, 1, data.get('company_vat') or '', label)
        sheet.write(row, 4, u'Регистрийн дугаар:', label)
        sheet.merge_range(row, 5, row, 7, '', blank_line)
        row += 1
        sheet.write(row, 4, u'Огноо:', label)
        sheet.merge_range(row, 5, row, 7, '', blank_line)

        row += 2
        headers = [u'№', u'Барааны нэр', u'Тодорхойлолт', u'Хэмжих нэгж', u'Тоо хэмжээ', u'Нэгж үнэ', u'Татвар', u'Дүн']
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header)

        line_count = data.get('line_count') or 20
        for i in range(1, line_count + 1):
            row += 1
            sheet.write(row, 0, i, cell)
            sheet.write(row, 1, '', cell_left)
            sheet.write(row, 2, '', cell_left)
            for col in range(3, 8):
                sheet.write(row, col, '', cell)

        for lbl in [u'Дүн', u'Татвар', u'Нийт дүн']:
            row += 1
            sheet.merge_range(row, 0, row, 6, lbl, total_label)
            sheet.write(row, 7, '', cell)

        row += 3
        sig_lines = [
            u'Захиалга үйлдсэн: ____________________ /___________________/',
            u'Баталсан: ____________________ /___________________/',
            u'Нийлүүлэгч хүлээн зөвшөөрсөн: ____________________ /___________________/',
        ]
        for line in sig_lines:
            sheet.merge_range(row, 0, row, 5, line, sig)
            row += 2

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
