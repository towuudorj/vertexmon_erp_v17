# -*- coding: utf-8 -*-

import xlrd, base64, xlwt
from io import StringIO
from odoo import api, fields, models

class NdshReportImport(models.TransientModel):
    _inherit = 'abstract.report.excel'
    _name = 'ndsh.report.import'
    _description = 'Ndsh report'
    
    start_date = fields.Date(string='Start date',required=True)
    end_date = fields.Date(string='End date',required=True)
    company_id = fields.Many2one('res.company',string='Company',required=True,default=lambda self: self.env.user.company_id)
    
    
    
    def get_export_data(self):
        context = self._context
        ezxf = xlwt.easyxf
        styledict = self.get_easyxf_styles()
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet('Sheet1')
        header = ezxf('font: bold on; align: wrap off, vert centre, horiz centre;font: height 180')
        header1 = ezxf('font: bold off; align: wrap on, vert centre, horiz left;font: height 180')
        print_dateL = ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 180')
        print_dateR = ezxf('font: bold off; align: wrap off, vert centre, horiz right;font: height 180','#,##0.00_);(#,##0.00)')
        print_dateC = ezxf('font: bold off; align: wrap off, vert centre, horiz center;font: height 180')
        line = ezxf('font: bold off; align: wrap on, vert centre, horiz left;font: height 180; borders: left thin, right thin, top thin, bottom thin;')
        line_data = ezxf('font: bold off; align: wrap on, vert centre, horiz right;font: height 180; borders: left thin, right thin, top thin, bottom thin;')
        line_center = ezxf('font: bold on; align: wrap on, vert centre, horiz center;font: height 180; borders: left thin, right thin, top thin, bottom thin;')
        line_left= ezxf('font: bold off; align: wrap on, vert centre, horiz left;font: height 180; borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        line_right= ezxf('font: bold off; align: wrap on, vert centre, horiz right;font: height 180; borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        nonline = ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 180;')
        
        sheet.write(0, 0, 'Регистрийн дугаар', print_dateR)
        sheet.write(0, 1, 'Ургийн овог', print_dateR)
        sheet.write(0, 2, 'Эцэг/эхийн нэр', print_dateR)
        sheet.write(0, 3, 'Нэр', print_dateR)
        sheet.write(0, 4, 'Даатгуулагчийн төрөл', print_dateR)
        sheet.write(0, 5, 'Ажил мэргэжлийн ангилал', print_dateR)
        sheet.write(0, 6, 'Хөдөлмөрийн хөлс түүнтэй адилтгах орлого', print_dateR)
        sheet.write(0, 7, 'Үндсэн ба нэмэгдэл цалин', print_dateR)
        sheet.write(0, 8, 'Шагналт цалин', print_dateR)
        sheet.write(0, 9, 'Бусад нэмэгдэл цалин', print_dateR)
        sheet.write(0, 10, 'Хоол унааны хөлс', print_dateR)
        sheet.write(0, 11, 'Түлээ нүүрсний үнийн хөнгөлөлт', print_dateR)
        sheet.write(0, 12, 'Иргэншил', print_dateR)
        sheet.write(0, 13, 'Харилцах утасны дугаар', print_dateR)
        sheet.write(0, 14, 'Цахим шуудангийн хаяг', print_dateR)

        
        payslip_obj = self.env['hr.payslip']
        employee_obj = self.env['hr.employee']
        employee = []
        employee_id = employee_obj.search([('company_id','=',self.company_id.id),('active','in',(True, False))],order='name asc')
        rowx = 1
        for emp in employee_id:
            payslip_id = payslip_obj.search([('company_id','=',self.company_id.id),('employee_id','=',emp.id),('state','=','done'),('date_from','>=',self.start_date),('date_to','<=',self.end_date)])
            if payslip_id:
                for line in payslip_id:
                    names = line.employee_id.name.split(".")
                    if len(names)==1:
                        nname = names[0]
                    else:
                        nname = names[1]
                    sheet.write(rowx, 0, u'%s'%(line.employee_id.identification_id).upper(), print_dateR)
                    sheet.write(rowx, 1, u'%s'%(line.employee_id.surname) or '', print_dateR)
                    sheet.write(rowx, 2, u'%s'%(line.employee_id.last_name) or '', print_dateR)
                    sheet.write(rowx, 3, u'%s'%nname, print_dateR)
                    sheet.write(rowx, 4, u'%s'%line.employee_id.ndd_type_id.code, print_dateR)
                    sheet.write(rowx, 5, u'%s'%(line.employee_id.job_id.category_id.code), print_dateR)
                    
                    food_total = 0
                    tcs_total = 0
                    od_total = 0.0
                    hyzgaar = 0
                    bs_total = 0
                    rb_total = 0
                    od_total = 0
                    for line_data in line.line_ids:
                        if line_data.code =='CS':
                            bs_total += line_data.total
                        elif line_data.code =='MORT':
                            bs_total += line_data.total
                        elif line_data.code == 'RB':
                            rb_total += line_data.total
                        elif line_data.code == 'KPIAMO':
                            rb_total += line_data.total
                        elif line_data.code == 'OD':
                            od_total +=line_data.total
                        elif line_data.code == 'SEK':
                            od_total +=line_data.total
                        elif line_data.code == 'PHA':
                            od_total +=line_data.total
                        elif line_data.code == 'FD':
                            food_total += line_data.total
                        elif line_data.code == 'TA':
                            food_total += line_data.total
                        elif line_data.code == 'TCS':
                            tcs_total += line_data.total
                        elif line_data.code =='OD':
                            od_total +=line_data.total
                            
                    #if bs_total==0:
                    com_total = tcs_total-rb_total-od_total-food_total
                    sheet.write(rowx, 6, tcs_total, print_dateR)
                    sheet.write(rowx, 7, com_total, print_dateR)
                    #else:
                    #    sheet.write(rowx, 6, bs_total, print_dateR)
                    #    sheet.write(rowx, 7, bs_total, print_dateR)
                    sheet.write(rowx, 8, rb_total, print_dateR)
                    sheet.write(rowx, 9, od_total, print_dateR)
                    sheet.write(rowx, 10, food_total, print_dateR)
                    sheet.write(rowx, 11, 0, print_dateR)
                    sheet.write(rowx, 12, u'%s'%line.employee_id.country_id.name, print_dateR)
                    sheet.write(rowx, 13, line.employee_id.mobile_phone or 0, print_dateR)
                    sheet.write(rowx, 14, line.employee_id.work_email or 0, print_dateR)
                    rowx +=1
                    
        return {'data':book,'directory_name':u'Санхүү байдлын тайлан',
                'attache_name':'Санхүү байдлын тайлан'} 
        

        