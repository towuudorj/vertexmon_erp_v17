# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import date_utils
import base64
import io
import json
import xlsxwriter
from io import BytesIO
from PIL import Image


class StockExpenseTemplateReport(models.TransientModel):
    """
        Зарлагын баримтын хоосон загвар (Excel)
    """
    _name = "stock.expense.template.report"
    _description = "Stock expense blank template - Mongolia"

    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                 default=lambda self: self.env.company)
    line_count = fields.Integer(string=u'Хоосон мөрийн тоо', default=20, required=True)

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_vat': self.company_id.vat,
            'company_logo': self.company_id.logo,
            'line_count': self.line_count,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                'model': 'stock.expense.template.report',
                'output_format': 'xlsx',
                'options': json.dumps(data, default=date_utils.json_default),
                'report_name': 'stock_expense_template_report',
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
        sheet = workbook.add_worksheet(u'Зарлагын баримт')

        title = workbook.add_format({'align': 'center', 'font_size': 14, 'bold': True})
        small = workbook.add_format({'align': 'left', 'font_size': 9})
        label = workbook.add_format({'align': 'center', 'font_size': 10})
        label_bold = workbook.add_format({'align': 'center', 'font_size': 10, 'bold': True, 'underline': True})
        hint = workbook.add_format({'align': 'center', 'font_size': 9, 'italic': True})
        header = workbook.add_format({'align': 'center', 'font_size': 11, 'bold': True, 'border': 1, 'bg_color': '#F0F0F0'})
        cell = workbook.add_format({'align': 'center', 'font_size': 11, 'border': 1})
        cell_left = workbook.add_format({'align': 'left', 'font_size': 11, 'border': 1})
        total_label = workbook.add_format({'align': 'center', 'font_size': 11, 'border': 1, 'bold': True})
        sig = workbook.add_format({'align': 'right', 'font_size': 10})

        sheet.set_column('A:A', 4)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:F', 13)

        sheet.set_row(0, 45)
        self._insert_logo(sheet, data.get('company_logo'), 0, 0)

        sheet.write('A2', u'НХМаягт БТ-2', small)
        sheet.merge_range('A3:F3', u'ЗАРЛАГЫН БАРИМТ', title)
        sheet.merge_range('A4:F4', u'№', label)

        row = 5
        sheet.write(row, 0, data.get('company_name') or '', label_bold)
        sheet.write(row, 3, '', label_bold)
        row += 1
        sheet.write(row, 0, u'( Байгууллагын нэр )', hint)
        sheet.write(row, 3, u'( Байгууллагын нэр )', hint)
        row += 1
        sheet.write(row, 0, u'Регистрийн №: %s' % (data.get('company_vat') or ''), label)
        sheet.write(row, 3, u'Регистрийн №:', label)
        row += 1
        sheet.write(row, 0, u'Огноо:', label)

        row += 2
        headers = [u'№', u'Барааны нэр', u'Х/Нэгж', u'Тоо хэмжээ', u'Нэгж үнэ', u'Нийт дүн']
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header)

        line_count = data.get('line_count') or 20
        for i in range(1, line_count + 1):
            row += 1
            sheet.write(row, 0, i, cell)
            sheet.write(row, 1, '', cell_left)
            for col in range(2, 6):
                sheet.write(row, col, '', cell)

        for lbl in [u'Дүн', u'НӨАТ', u'Нийт дүн /НӨАТ орсон/']:
            row += 1
            sheet.merge_range(row, 0, row, 4, lbl, total_label)
            sheet.write(row, 5, '', cell)

        row += 3
        sig_lines = [
            u'Хариуцсан борлуулалтын менежер: ____________________ /___________________/',
            u'Шалгасан нягтлан бодогч: ____________________ /___________________/',
            u'Хүлээлгэн өгсөн эд хариуцагч: ____________________ /___________________/',
            u'Хүлээн авсан: ____________________ /___________________/',
        ]
        for line in sig_lines:
            sheet.merge_range(row, 1, row, 5, line, sig)
            row += 2

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
