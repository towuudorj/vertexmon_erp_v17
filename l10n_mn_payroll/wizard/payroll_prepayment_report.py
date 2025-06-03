# -*- coding: utf-8 -*-

import xlrd, base64, xlwt
from io import StringIO
from odoo import api, fields, models

class payroll_prepayment_report(models.TransientModel):
    _inherit = 'abstract.report.excel'
    _name = 'payroll.prepayment.report'
    _description = 'Payroll Prepayment Report'
    
    

    def get_export_data(self):
        context = self._context
        ezxf = xlwt.easyxf
        styledict = self.get_easyxf_styles()
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet('Hr payroll prepayment is bank')
        header = ezxf('font: bold on; align: wrap off, vert centre, horiz centre;font: height 220')
        header1 = ezxf('font: bold off; align: wrap on, vert centre, horiz left;font: height 200')
        print_dateL = ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 200')
        print_dateR = ezxf('font: bold off; align: wrap off, vert centre, horiz right;font: height 200')
        line = ezxf('font: bold off; align: wrap on, vert centre, horiz left;font: height 200; borders: left thin, right thin, top thin, bottom thin;')
        line_data = ezxf('font: bold off; align: wrap on, vert centre, horiz right;font: height 200; borders: left thin, right thin, top thin, bottom thin;')
        line_center = ezxf('font: bold on; align: wrap on, vert centre, horiz center;font: height 200; borders: left thin, right thin, top thin, bottom thin;')
        nonline = ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 200;')

        
        payroll_data = self.env['hr.payroll.prepayment'].browse(context.get('active_ids', []))

        sheet.write_merge(3, 3, 0, 6, u'УРЬДЧИЛГАА ЦАЛИН ОЛГОХ ХҮСНЭГТ', header)
        sheet.write_merge(5, 5, 0, 3, u"Хамрах хугацаа: %s - %s" % (payroll_data.start_date,payroll_data.end_date), print_dateL)
        rowx = 7
        sheet.write(rowx, 0, u'Д/д', line_center)
        sheet.write(rowx, 1, u'Ажилтны нэр', line_center)
        sheet.write(rowx, 2, u'Банкны данс', line_center)
        sheet.write(rowx, 3, u'Урьдчилгаа цалин', line_center)
        sheet.write(rowx, 4, u'Бусад', line_center)
        sheet.write(rowx, 5, u'Гарт олгох нь', line_center)
        count = 0
        i=0
        sum = 0
        n = 1
        payroll = 0
        phone = 0
        loan = 0
        other = 0
        give = 0
        rowx += 1
    

        for l in payroll_data.line_id:
            sheet.write(rowx, 0, u'%s'%n, line)
            sheet.write(rowx, 1, u'%s'%(l.name.name), line)
            sheet.write(rowx, 2, u'%s'%(l.name.bank_account_id.acc_number or ''), line)
            sheet.write(rowx, 3, u'%s'%(l.prepayment_payroll or u' '), line_data)            
            sheet.write(rowx, 4, u'%s'%(l.other_payment or u' '), line_data)
            sheet.write(rowx, 5, u'%s'%(l.hand_give_amount or u' '), line_data)            
            payroll +=l.prepayment_payroll
            other += l.other_payment
            give += l.hand_give_amount
            n +=1
            rowx +=1      
        sheet.write_merge(rowx, rowx, 0, 2, u'Нийт', line_center)  
        sheet.write(rowx, 3, u'%s'%payroll, line_center)
        sheet.write(rowx, 4, u'%s'%other, line_center)
        sheet.write(rowx, 5, u'%s'%give, line_center)
            
        
        rowx += 2
        sheet.write(rowx, 2, u'Тооцоолсон Ня-бо: ......................................./ /', nonline)
        sheet.write(rowx+1, 2, u'Хянасан Ерөнхий ня-бо:................................/               /', nonline)
        inch = 1000
        sheet.col(0).width = 1*inch
        sheet.col(1).width = 6*inch
        sheet.col(2).width = 3*inch
        sheet.col(3).width = 3*inch
        sheet.col(4).width = 3*inch
        sheet.col(5).width = 3*inch
        sheet.col(6).width = 3*inch
        sheet.row(7).height = 600   



        return {'data':book,'directory_name':u'Санхүү байдлын тайлан',
                'attache_name':'Санхүү байдлын тайлан'} 
    