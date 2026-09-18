# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import date_utils
import base64
import io
import json
import xlsxwriter
from io import BytesIO
from PIL import Image


class AccountInvoiceTemplateReport(models.TransientModel):
    """
        Нэхэмжлэлийн хоосон загвар (Excel)
    """
    _name = "account.invoice.template.report"
    _description = "Account invoice blank template - Mongolia"

    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                 default=lambda self: self.env.company)
    line_count = fields.Integer(string=u'Хоосон мөрийн тоо', default=15, required=True)

    def action_print_xls_report(self):
        company = self.company_id
        data = {
            'company_name': company.name,
            'company_street': company.street,
            'company_phone': company.partner_id.phone or company.phone,
            'company_vat': company.vat,
            'company_bank_name': company.partner_id.bank_ids[0].bank_id.name if company.partner_id.bank_ids else '',
            'company_bank_account': company.partner_id.bank_ids[0].acc_number if company.partner_id.bank_ids else '',
            'company_logo': company.logo,
            'line_count': self.line_count,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                'model': 'account.invoice.template.report',
                'output_format': 'xlsx',
                'options': json.dumps(data, default=date_utils.json_default),
                'report_name': 'account_invoice_template_report',
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
        sheet = workbook.add_worksheet(u'Нэхэмжлэл')

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
        sheet.set_column('C:E', 13)

        sheet.set_row(0, 45)
        self._insert_logo(sheet, data.get('company_logo'), 0, 0)

        sheet.merge_range('A2:E2', u'НЭХЭМЖЛЭХ №:', title)

        row = 3
        sheet.write(row, 0, u'Нэхэмжлэгч:', section)
        sheet.write(row, 3, u'Төлөгч:', section)
        row += 1
        sheet.write(row, 0, u'Байгууллагын нэр:', label)
        sheet.write(row, 1, data.get('company_name') or '', label)
        sheet.write(row, 3, u'Байгууллагын нэр:', label)
        sheet.write(row, 4, '', blank_line)
        row += 1
        sheet.write(row, 0, u'Хаяг:', label)
        sheet.write(row, 1, data.get('company_street') or '', label)
        sheet.write(row, 3, u'Хаяг:', label)
        sheet.write(row, 4, '', blank_line)
        row += 1
        sheet.write(row, 0, u'Утас:', label)
        sheet.write(row, 1, data.get('company_phone') or '', label)
        sheet.write(row, 3, u'Утас:', label)
        sheet.write(row, 4, '', blank_line)
        row += 1
        sheet.write(row, 0, u'Регистрийн дугаар:', label)
        sheet.write(row, 1, data.get('company_vat') or '', label)
        sheet.write(row, 3, u'Регистрийн дугаар:', label)
        sheet.write(row, 4, '', blank_line)
        row += 1
        sheet.write(row, 0, u'Банкны нэр:', label)
        sheet.write(row, 1, data.get('company_bank_name') or '', label)
        sheet.write(row, 3, u'Гэрээний дугаар:', label)
        sheet.write(row, 4, '', blank_line)
        row += 1
        sheet.write(row, 0, u'Банкны данс:', label)
        sheet.write(row, 1, data.get('company_bank_account') or '', label)
        sheet.write(row, 3, u'Нэхэмжилсэн огноо:', label)
        sheet.write(row, 4, '', blank_line)
        row += 1
        sheet.write(row, 3, u'Төлбөр хийх хугацаа:', label)
        sheet.write(row, 4, '', blank_line)

        row += 2
        headers = [u'№', u'Барааны нэр', u'Тоо хэмжээ', u'Нэгж үнэ', u'Нийт үнэ']
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header)

        line_count = data.get('line_count') or 15
        for i in range(1, line_count + 1):
            row += 1
            sheet.write(row, 0, i, cell)
            sheet.write(row, 1, '', cell_left)
            for col in range(2, 5):
                sheet.write(row, col, '', cell)

        for lbl in [u'Дүн', u'НӨАТ 10%', u'Нийт дүн']:
            row += 1
            sheet.merge_range(row, 0, row, 3, lbl, total_label)
            sheet.write(row, 4, '', cell)

        row += 2
        sheet.write(row, 0, u'Мөнгөн дүн (үсгээр): ')
        row += 3
        sheet.write(row, 0, u'Ерөнхий нягтлан бодогч:', sig)
        row += 2
        sheet.write(row, 0, u'Борлуулалтын менежер:', sig)
        row += 2
        sheet.write(row, 0, u'Хүлээн авсан:', sig)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
