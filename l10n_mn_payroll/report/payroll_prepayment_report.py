# -*- coding: utf-8 -*-
import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
class HrPayrollPrepayment(models.Model):
    _inherit = 'hr.payroll.prepayment'

    excel_file = fields.Binary('Download report Excel', attachment=True, readonly=True)
    file_name = fields.Char('Excel File', size=64)

    def generate_excel(self):
        filename = "payroll_prepayment_report %s" % self.name
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        font_size_10 = workbook.add_format({
            'font_name': 'KacstBook',
            'font_size': 12,
            'text_wrap': True,
            'border': 1
        })
        table_header_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'bg_color': '#AAB7B8',
            'font_size': 11,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        table_cell_format = workbook.add_format({
            'border': 1,
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })

        sheet = workbook.add_worksheet('data')
        sheet.set_column(0, 10, 20)
        sheet.set_row(3, 20)
        sheet.set_row(4, 20)
        company = self.env.company
        sheet.insert_image('A1:B2', company.logo)
        sheet.write('A3', u'Компани: %s'%company.name, font_size_10)
        sheet.merge_range('A4:F4', u'УРЬДЧИЛГАА ЦАЛИН ОЛГОХ ХҮСНЭГТ', table_header_format)
        sheet.merge_range('A5:F5', u'Хугацаа: %s'%self.end_date, font_size_10)
        headers = ['Д/д', 'Ажилтны нэр', 'Банкны данс', 'Урьдчилгаа цалин', 'Бусад', 'Гарт олгох нь']
        [sheet.write(6, idx, h , table_header_format)  for idx , h in enumerate(headers)]

        row = 7
        n = 1
        payroll = 0
        other = 0
        give = 0  
        
        for line in self.line_id:
            sheet.write(row, 0, n, table_cell_format)
            sheet.write(row, 1, u'%s'%(line.name.name), table_cell_format)
            sheet.write(row, 2, u'%s'%(line.name.bank_account_id.acc_number or ''), table_cell_format)
            sheet.write(row, 3, u'%s'%(line.prepayment_payroll or u' '), table_cell_format)
            sheet.write(row, 4, u'%s'%(line.other_payment or u' '), table_cell_format)
            sheet.write(row, 5, u'%s'%(line.hand_give_amount or u' '), table_cell_format)
            payroll +=line.prepayment_payroll
            other += line.other_payment
            give += line.hand_give_amount
            row += 1
            n +=1

        sheet.merge_range('A%s:C%s'%(row+1, row+1), u'Нийт', table_cell_format)  
        sheet.write(row, 3, u'%s'%payroll, table_cell_format)
        sheet.write(row, 4, u'%s'%other, table_cell_format)
        sheet.write(row, 5, u'%s'%give, table_cell_format)

        workbook.close()
        output.seek(0)
        self.write({'file_name': filename + str(datetime.today().strftime('%Y-%m-%d')) + '.xlsx'})
        self.excel_file = base64.encodebytes(output.getvalue())
        #self.excel_file = base64.b64encode(output.read())
        return {
            'type': 'ir.actions.act_url',
            'name': filename,
            'url': '/web/content/hr.payroll.prepayment/%s/excel_file?download=true' % self.id,
            'target': 'new'
        }
    

    