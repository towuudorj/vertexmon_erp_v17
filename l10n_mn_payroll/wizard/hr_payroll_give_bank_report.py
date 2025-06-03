# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class HrPayrollGiveBankReport(models.TransientModel):
    _name = 'hr.payroll.give.bank.report'
    _description = 'hr payroll give bank report'
    
        
    start_date = fields.Date(string='Start date',required=True)
    end_date = fields.Date(string='End date',required=True)
    company_id = fields.Many2one('res.company',string='Company',required=True,default=lambda self: self.env.user.company_id)
    bank_id = fields.Many2one('res.bank',string='Bank',required=True)
    type = fields.Integer(string='Transaction type',default=10,required=True)
    value = fields.Char(string='Transaction',required=True)
    check_value = fields.Integer(string='Important amount',required=True,default=1)
    
    
    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'type': self.type,
            'value': self.value,
            'check_value': self.check_value,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'currency_name': self.company_id.currency_id.name,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'hr.payroll.give.bank.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Payroll give report'}
        }

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': '20px'
                                    })
        txt = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12
                                })
        sheet.set_column(0, 8, 24)
        
        sheet.write('A1', u'Гүйлгээний төрөл', txt)
        sheet.write('B1', u'Хүлээн авах банк', txt)
        sheet.write('C1', u'Хүлээн авах данс', txt)
        sheet.write('D1', u'Хүлээн авагчийн нэр', txt)
        sheet.write('E1', u'Хүлээн авах дансны валют', txt)
        sheet.write('F1', u'Гүйлгээний утга', txt)
        sheet.write('G1', u'Чухал дүн', txt)
        sheet.write('H1', u'Гүйлгээний дүн', txt)

        rowx = 2
        payroll_data = self.env['hr.employee'].search([])
        payslip_obj = self.env['hr.payslip']
        for emp in payroll_data:
            payslip_ids = payslip_obj.search([('date_from','=',data['start_date']),('date_to','=',data['end_date']),('employee_id','=',emp.id),('state','=','done')])
            for pl in payslip_ids:
                account_number = 0
                acc_num = 0
                salary = 0.0
                for list in emp.user_id.partner_id.bank_ids:
                    if list.is_salary == True and self.bank_id.id == list.bank_id.id:
                        account_number = int(list.acc_number)
                        acc_num = int(str(list.acc_number)[:3])
                nname = ''
                names = emp.name.split(".")
                if len(names)==1:
                    nname = names[0]
                else:
                    nname = names[1]
                if account_number >0:
                    sheet.write(rowx, 0, data['type'], txt)
                    sheet.write(rowx, 1, acc_num, txt)
                    sheet.write(rowx, 2, account_number, txt)
                    sheet.write(rowx, 3,  u'%s'%(nname), txt)            
                    sheet.write(rowx, 4, u'%s'%(data['currency_name'] or u' '), txt)
                    sheet.write(rowx, 5, u'%s'%(data['value']), txt)       
                    sheet.write(rowx, 6, data['check_value'], txt)
                    for pli in pl.line_ids:
                        if pli.code == 'GIVE':
                            salary = pli.total
                    sheet.write(rowx, 7, salary or 0.0, txt)         
                    rowx +=1  
 
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


    


        
           

            
