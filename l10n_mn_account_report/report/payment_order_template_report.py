# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools import date_utils
import io
import json
import xlsxwriter


class PaymentOrderTemplateReport(models.TransientModel):
    """
        Төлбөрийн даалгаврын хоосон загвар (Excel)
    """
    _name = "payment.order.template.report"
    _description = "Payment order blank template - Mongolia"

    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                 default=lambda self: self.env.company)

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                'model': 'payment.order.template.report',
                'output_format': 'xlsx',
                'options': json.dumps(data, default=date_utils.json_default),
                'report_name': 'payment_order_template_report',
            }
        }

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(u'Төлбөрийн даалгавар')

        small = workbook.add_format({'align': 'right', 'font_size': 9})
        title = workbook.add_format({'align': 'right', 'font_size': 11})
        header = workbook.add_format({'align': 'left', 'font_size': 10, 'border': 1})
        header_center = workbook.add_format({'align': 'center', 'font_size': 10, 'border': 1})
        cell = workbook.add_format({'align': 'center', 'font_size': 10, 'border': 1})
        cell_left = workbook.add_format({'align': 'left', 'font_size': 10, 'border': 1})
        sig = workbook.add_format({'align': 'left', 'font_size': 10})

        sheet.set_column('A:A', 22)
        sheet.set_column('B:B', 26)
        sheet.set_column('C:C', 16)
        sheet.set_column('D:D', 18)

        sheet.merge_range('A1:D1', u'Маягт N: TC-7', small)
        sheet.merge_range('A2:D2', u'Санхүү эдийн засгийн сайдын 2002 оны', small)
        sheet.write('A3', u'Төлбөрийн даалгавар', title)
        sheet.merge_range('B3:D3', u'06 дугаар сарын 28 ны өдрийн 182 тоот тушаалаар батлав.', small)
        sheet.write('A4', u'Огноо:', header)

        row = 5
        sheet.write(row, 0, u'Төлөгч', header)
        sheet.merge_range(row, 1, row, 2, u'ДАНС', header_center)
        sheet.write(row, 3, u'ДҮН', header_center)
        row += 1
        sheet.write(row, 0, u'Код', header)
        sheet.write(row, 1, data.get('company_name') or '', header_center)
        sheet.write(row, 2, u'Дебет/Кредит', header_center)
        sheet.write(row, 3, '', cell)
        row += 1
        sheet.write(row, 0, u'Төлөгчийн банк', header)
        sheet.write(row, 1, '', cell_left)
        sheet.write(row, 2, '', cell)
        sheet.write(row, 3, '', cell)
        row += 1
        sheet.write(row, 0, u'Код (Хүлээн авагч)', header)
        sheet.write(row, 1, '', cell_left)
        sheet.write(row, 2, u'Дебет/Кредит', header_center)
        sheet.write(row, 3, '', cell)
        row += 1
        sheet.write(row, 0, u'Хүлээн авагч:', header)
        sheet.write(row, 1, '', cell_left)
        sheet.write(row, 2, '', cell)
        sheet.write(row, 3, '', cell)
        row += 1
        sheet.merge_range(row, 0, row, 2, u'Мөнгөн дүн (үсгээр):', header)
        sheet.write(row, 3, '', cell)
        row += 1
        sheet.merge_range(row, 0, row, 2, u'Барааг хүлээн авсан буюу ажил үйлчилгээг гүйцэтгэсэн огноо', header)
        sheet.write(row, 3, '', cell)
        row += 1
        sheet.merge_range(row, 0, row, 2, '', cell)
        sheet.write(row, 3, '', cell)
        row += 1
        sheet.write(row, 0, u'Төлбөрийн зориулалт', header)
        sheet.write(row, 1, u'Гүйлгээний утга', header_center)
        sheet.merge_range(row, 2, row, 3, '', cell)

        row += 2
        sheet.write(row, 0, u'Захирал: ____________________ /___________________/', sig)
        row += 1
        sheet.write(row, 0, u'Банкинд гүйлгээ хийсэн: .... оны ... сарын ... өдөр', sig)
        row += 1
        sheet.write(row, 0, u'Тамга, гарын үсэг', sig)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
