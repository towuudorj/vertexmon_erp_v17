# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class HhoatReportWizard(models.TransientModel):
    _name = 'hhoat.report.wizard'
    _description = "HHOAT Report Wizard"
    
    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env.user.company_id)
    start_date = fields.Date(string='Start date',required=True,default=fields.Date.context_today)
    end_date = fields.Date(string='End date',required=True,default=fields.Date.context_today)
    




    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'start_date': self.start_date,
            'end_date': self.end_date,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'hhoat.report.wizard',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Hhoat report'}
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


        sheet.write('A1', u'Татвар төлөгчийн дугаар', head)
        sheet.write('B1', u'Овог', head)
        sheet.write('C1', u'Нэр', head)
        sheet.write('D1', u'Хуулийн 7.1.1', head)
        sheet.write('E1', u'Хуулийн 7.1.2, 7.1.3, 7.1.4, 7.1.5, 7.1.7', head)
        sheet.write('F1', u'Хуулийн 7.1.6', head)
        sheet.write('G1', u'Нийт (1+2+3)', head)
        sheet.write('H1', u'ЭМД, НДШ Хувь', head)
        sheet.write('I1', u'ЭМД, НДШ Дүн', head)
        sheet.write('K1', u'Татвар ногдуулах орлого', head)
        sheet.write('L1', u'Ногдуулсан татвар', head)
        sheet.write('M1', u'Орлого хүлээн авсан сарын тоо /ажилласан сар/', head)
        sheet.write('N1', u'Хуулийн 23.1-т заасан хөнгөлөлт сард ногдох', head)
        sheet.write('O1', u'Хуулийн 23.1-т заасан хөнгөлөлт нийт', head)
        sheet.write('P1', u'Хөнгөлөлтийн дараах татварын дүн', head)
        sheet.write('Q1', u'Хуулийн 7.1.6-д заасан орлогод ногдуулсан дүн', head)
        sheet.write('R1', u'Нийт суутгуулсан албан татварын дүн', head)


        employee_obj = self.env['hr.employee']
        payslip_obj = self.env['hr.payslip']
        payslip_ids = payslip_obj.search([('date_from','>=',str(data['start_date'])),('date_to','<=',str(data['end_date'])),('state','=','done'),('company_id','=',data['company_id'])])
        employee_ids = employee_obj.search([('company_id','=',data['company_id']),"|",('active','=',True),('active','=',False)])
       
        rowx = 2

        total_salary = 0.0
        total_com_salary = 0.0
        total_ndsh = 0.0
        total_amounts = 0.0
        total_discount_hhoat = 0.0
        total_discount_amount = 0.0
        discount_amount = 0.0
        total_hhoat = 0.0
        total_hhoat_income = 0.0
        if payslip_ids:
            for line in employee_ids:
                salary = 0.0
                ndsh = 0.0
                hhoat_income = 0.0
                hhoat = 0.0
                count = 0.0
                percent = 0.0
                total_amount = 0.0
                discount_hhoat = 0.0
                total_discount = 0.0
                discount = 0.0
                for pslip in payslip_ids:
                    if line.id==pslip.employee_id.id:
                        for pline in pslip.line_ids:
                            if  pline.code=='TCDSA' or pline.code=='TCDS' or pline.code=='TCDSI' or pline.code=='TCDSMO' or pline.code=='TCDSI8' or pline.code=='TCDSIHC':
                                count +=1
                                salary += pline.total
                                
                            if pline.code == 'SI78' or pline.code =='SI10' or pline.code =='SI108' or pline.code=='SIIV11' or pline.code=='SIMO' or pline.code=='SIIV8' or pline.code=='SHI103' or pline.code=='SIIHC11.5'  or pline.code=='D2004'  or pline.code=='SHI12,5'  or pline.code=='SHI-AMP118':                                           
                            
                                ndsh +=pline.total
                            if pline.code == 'LL':
                                total_discount +=pline.total
                            if pline.code =='PIT100' or pline.code=='PIT78' or pline.code=='PIT1001' or pline.code=='PITIV' or pline.code=='PITMO' or pline.code=='TPITIV8' or pline.code=='TPIT108' or pline.code=='PIT100IHC':
                                hhoat +=pline.total

                if salary > 0.0:
                    sheet.write(rowx, 0, u'%s'%line.tdd_number, txt)
                    sheet.write(rowx, 1, u'%s'%line.last_name, txt)
                    sheet.write(rowx, 2, u'%s'%line.name, txt)

                    if ndsh >0.0 and salary >0.0:
                        percent = ndsh/salary*100.0

                    sheet.write(rowx, 3, salary, txt)
                    sheet.write(rowx, 4, 0.0, txt)
                    sheet.write(rowx, 5, 0.0, txt)
                    sheet.write(rowx, 6, salary, txt)
                    sheet.write(rowx, 7, round(percent,1), txt)
                    sheet.write(rowx, 8, ndsh, txt)
                    total_ndsh +=ndsh
                    hhoat_income = salary-ndsh
                    sheet.write(rowx, 9, hhoat_income, txt)
                    discount = hhoat-total_discount
                    total_amount = total_discount
                    total_salary +=salary
                    total_com_salary +=salary
                    sheet.write(rowx, 10, hhoat, txt)
                    sheet.write(rowx, 11, count, txt)
                    sheet.write(rowx, 12, discount, txt)
                    sheet.write(rowx, 13, total_discount, txt)
                    sheet.write(rowx, 14, discount_hhoat, txt)
                    sheet.write(rowx, 15, 0.0, txt)
                    sheet.write(rowx, 16, total_amount, txt)     
                    total_amounts +=total_amount   
                    total_discount_hhoat +=discount_hhoat
                    total_discount_amount +=total_discount
                    discount_amount +=discount
                    total_hhoat +=hhoat
                    total_hhoat_income +=hhoat_income
                    rowx +=1
        
        sheet.write_merge(rowx, rowx, 0, 2, u'Нийт', txt)
        sheet.write(rowx, 3, total_salary, txt)
        sheet.write(rowx, 4, '', txt)
        sheet.write(rowx, 5, '', txt)
        sheet.write(rowx, 6, total_com_salary, txt)
        sheet.write(rowx, 7, '', txt)
        sheet.write(rowx, 8, total_ndsh, txt)
        sheet.write(rowx, 9, total_hhoat_income, txt)
        sheet.write(rowx, 10, total_hhoat, txt)
        sheet.write(rowx, 11, '', txt)
        sheet.write(rowx, 12, discount_amount, txt)
        sheet.write(rowx, 13, total_discount_amount, txt)
        sheet.write(rowx, 14, total_discount_hhoat, txt)
        sheet.write(rowx, 15, '', txt)
        sheet.write(rowx, 16, total_amounts, txt)


 
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


