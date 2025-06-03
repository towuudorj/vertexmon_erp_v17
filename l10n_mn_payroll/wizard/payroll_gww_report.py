# -*- coding: utf-8 -*-

import xlrd, base64, xlwt
from io import StringIO
from odoo import api, fields, models


class payroll_gww_excel_report(models.TransientModel):
    _inherit = 'abstract.report.excel'
    _name = 'payroll.gww.excel.report'
    
    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env.user.company_id)
    department_id = fields.Many2one('hr.department',string='Department')
    start_date = fields.Date(string='Start date',required=True,default=fields.Date.context_today)
    end_date = fields.Date(string='End date',required=True,default=fields.Date.context_today)
    
    
    def get_export_data(self):
        context = self._context
        ezxf = xlwt.easyxf
        styledict = self.get_easyxf_styles()
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet('Hr payroll report')
        header = ezxf('font: bold on; align: wrap off, vert centre, horiz centre;font: height 220')
        header1 = ezxf('font: bold off; align: wrap on, vert centre, horiz left;font: height 200')
        print_dateL = ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 200')
        print_dateR = ezxf('font: bold off; align: wrap off, vert centre, horiz right;font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        line = ezxf('font: bold off; align: wrap on, vert centre, horiz left;font: height 200; borders: left thin, right thin, top thin, bottom thin;')
        line_data = ezxf('font: bold off; align: wrap on, vert centre, horiz right;font: height 200; borders: left thin, right thin, top thin, bottom thin;')
        line_center = ezxf('font: bold on; align: wrap on, vert centre, horiz center;font: height 200; borders: left thin, right thin, top thin, bottom thin;')
        nonline = ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 200;')

        employee_obj = self.env['hr.employee']
        payslip_obj = self.env['hr.payslip']
        category_obj = self.env['hr.salary.rule.category']
        self._cr.execute("select name,code from hr_salary_rule_category")
        categ_ids = self._cr.dictfetchall()
        resource_obj = self.env['resource.resource']
        resource_ids = resource_obj.search([('active','in',(True,False))])
        employee_ids = []
        if self.department_id.id !=None and self.department_id.id !=False:
            self._cr.execute("select id, last_name from hr_employee where department_id = %s and  id != 2 and company_id = %s order by last_name"%(self.department_id.id,self.company_id.id))
            employee = self._cr.fetchall()
            for line in employee:
                employee_ids.append(line[0])
        else:
            self._cr.execute("select id,last_name from hr_employee where id != 2 and company_id = %s order by last_name"%(self.company_id.id))
            employee = self._cr.fetchall()
            for line in employee:
                employee_ids.append(line[0])
        
        
        
        rowx = 2
        col = 3
        num = 1
        sheet.write(rowx, 0, u'№', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx, 1, 2, u'Ажилтны нэр', styledict['heading_xf'])
        sheet.write(rowx, 3, u'Хэлтэс', styledict['heading_xf'])
        sheet.write(rowx, 4, u'Үндсэн цалин', styledict['heading_xf'])
        sheet.write(rowx, 5, u'Ажиллах цаг', styledict['heading_xf'])
        sheet.write(rowx, 6, u'Ажилласан цаг', styledict['heading_xf'])
        sheet.write(rowx, 7, u'Ажиллах ёстой өдөр', styledict['heading_xf'])
        sheet.write(rowx, 8, u'Ажилласан өдөр', styledict['heading_xf'])
        sheet.write(rowx, 9, u'Бодогдсон цалин', styledict['heading_xf'])
        sheet.write(rowx, 10, u'Урамшуулал', styledict['heading_xf'])
        sheet.write(rowx, 11, u'Амралтын мөнгө', styledict['heading_xf'])
        sheet.write(rowx, 12, u'Хоол унааны нэмэгдэл', styledict['heading_xf'])
        sheet.write(rowx, 13, u'Нийт бодогдсон цалин', styledict['heading_xf'])
        sheet.write(rowx, 14, u'ЭМНДШ Хувь', styledict['heading_xf'])
        sheet.write(rowx, 15, u'ЭМНДШ Байгууллага', styledict['heading_xf'])
        sheet.write(rowx, 16, u'ХХОАТ', styledict['heading_xf'])
        sheet.write(rowx, 17, u'Гар утас суутгал', styledict['heading_xf'])
        sheet.write(rowx, 18, u'Ажилтнаас авах авлага', styledict['heading_xf'])
        sheet.write(rowx, 19, u'Зөрчлийн суутгал', styledict['heading_xf'])
        sheet.write(rowx, 20, u'Нийт суутгал', styledict['heading_xf'])
        sheet.write(rowx, 21, u'Урьдчилгаа цалин', styledict['heading_xf'])
        sheet.write(rowx, 22, u'Гарт олгох', styledict['heading_xf'])
        sheet.write(rowx, 23, u'Дансны дугаар',styledict['heading_xf'])
        rowx +=1
        name = ''
        bs = 0.0
        work_time_wdt = 0.0
        total_salary = 0.0
        total_work_time = 0.0
        work_day_mwd = 0.0
        total_cs = 0.0
        total_fdd = 0.0
        work_total_day_wdd = 0.0
        total_ll = 0.0
        total_si11 = 0.0
        total_adv = 0.0
        total_tcs = 0.0
        total_rs = 0.0
        total_kpi = 0.0
        total_ph = 0.0
        total_pay = 0.0
        total_te = 0.0
        total_give = 0.0
        total_fault = 0.0
        total_ndsh = 0.0
        for emp in employee_obj.browse(employee_ids):
            col = 2
            wdt = 0.0
            MWT = 0.0
            mwd = 0.0
            wdd = 0.0
            fdd = 0.0
            cs = 0.0
            rs = 0.0
            tcs = 0.0
            adv = 0.0
            si11 = 0.0
            kpi = 0.0
            ll = 0.0
            ph = 0.0
            pay = 0.0
            te = 0.0
            give = 0.0
            fault = 0.0
            ndsh = 0.0
            payslip_id = payslip_obj.search([('date_from','>=',self.start_date),('date_to','<=',self.end_date),('employee_id','=',emp.id),('state','=','done'),('is_return','=',False)])
            if payslip_id:
                sheet.write(rowx, 0, u'%s'%num, print_dateR)
                sheet.write_merge(rowx, rowx, 1, 2, u'%s'%(emp.name or ''), print_dateR)
                sheet.write(rowx, 3, u'%s'%(emp.department_id.name), print_dateR)
                for li in payslip_id:
                    for line in li.line_ids:
                        if line.code == 'BS':
                            bs = line.total
                            total_salary +=line.total
                        
                        if line.code == 'WDT':
                            wdt = line.total
                            work_time_wdt +=line.total
                            
                        elif line.code == 'MWT':
                            MWT = line.total
                            total_work_time +=line.total
                             
                        elif line.code == 'MWD':
                            mwd = line.total
                            work_day_mwd +=line.total    
                             
                        elif line.code == 'WDD':
                            wdd = line.total
                            work_total_day_wdd +=line.total
                              
                              
                        elif line.code == 'FDD':
                            fdd = line.total
                            total_fdd +=line.total
                              
                        elif line.code == 'CS':
                            cs = line.total
                            total_cs +=line.total
                              
                        elif line.code == 'RS':
                            rs = line.total
                            total_rs +=line.total
                           
                        elif line.code == 'TCS':
                            tcs = line.total
                            total_tcs +=line.total
                               
                        elif line.code == 'ADV':
                            adv = line.total
                            total_adv +=line.total
                               
                        elif line.code == 'SI11' or line.code =='SI15' or line.code == 'SI10':
                            si11 = line.total
                            total_si11 +=line.total
                        elif line.code == 'NDSH':
                            ndsh = line.total
                            total_ndsh +=line.total
                               
                        elif line.code == 'LL':
                            ll = line.total
                            total_ll +=line.total    
                                                
                        elif line.code == 'KPI':
                            kpi = line.total
                            total_kpi +=line.total 
                        
                        elif line.code == 'KPI':
                            kpi = line.total
                            total_kpi +=line.total   
                        
                        elif line.code == 'PH':
                            ph = line.total
                            total_ph +=line.total   
                        
                        elif line.code == 'PAY':
                            pay = line.total
                            total_pay +=line.total   
                        
                        elif line.code == 'TE':
                            te = line.total
                            total_te +=line.total  
                            
                        
                        elif line.code == 'GIVE':
                            give = line.total
                            total_give +=line.total  
                        
                        elif line.code == 'FAULT':
                            fault = line.total
                            total_fault +=line.total
                            
                    
                    
                    if bs > 0.0:
                        sheet.write(rowx, 4, bs, print_dateR)
                    else:
                        sheet.write(rowx, 4, 0.0, print_dateR)

                    if wdt > 0.0:
                        sheet.write(rowx, 5, wdt, print_dateR)
                    else:
                        sheet.write(rowx, 5, 0.0, print_dateR)
                        
                    if MWT > 0.0:
                        sheet.write(rowx, 6, MWT, print_dateR)
                    else:
                        sheet.write(rowx, 6, 0.0, print_dateR)
                        
                    if mwd > 0.0:
                        sheet.write(rowx, 7, mwd, print_dateR)
                    else:
                        sheet.write(rowx, 7, 0.0, print_dateR)
                        
                    if wdd > 0.0:
                        sheet.write(rowx, 8, wdd, print_dateR)
                    else:
                        sheet.write(rowx, 8, 0.0, print_dateR)
                        
                    if cs > 0.0:
                        sheet.write(rowx, 9, cs, print_dateR)
                    else:
                        sheet.write(rowx, 9, 0.0, print_dateR)
                        
                    if kpi > 0.0:
                        sheet.write(rowx, 10, kpi, print_dateR)
                    else:
                        sheet.write(rowx, 10, 0.0, print_dateR)
                    
                    if rs > 0.0:
                        sheet.write(rowx, 11, rs, print_dateR)
                    else:
                        sheet.write(rowx, 11, 0.0, print_dateR)
                    
                    if fdd > 0.0:
                        sheet.write(rowx, 12, fdd, print_dateR)
                    else:
                        sheet.write(rowx, 12, 0.0, print_dateR)
                        
                    
                    if tcs > 0.0:
                        sheet.write(rowx, 13, tcs, print_dateR)
                    else:
                        sheet.write(rowx, 13, 0.0, print_dateR)

                    
                    if si11 > 0.0:
                        sheet.write(rowx, 14, si11, print_dateR)
                    else:
                        sheet.write(rowx, 14, 0.0, print_dateR)
                                    
                    if ndsh > 0.0:
                        sheet.write(rowx, 15, ndsh, print_dateR)
                    else:
                        sheet.write(rowx, 15, 0.0, print_dateR)
                        
                    if ll > 0.0:
                        sheet.write(rowx, 16, ll, print_dateR)
                    else:
                        sheet.write(rowx, 16, 0.0, print_dateR)
                    
                    if ph > 0.0:
                        sheet.write(rowx, 17, ph, print_dateR)
                    else:
                        sheet.write(rowx, 17, 0.0, print_dateR)
                        
                    
                    if pay > 0.0:
                        sheet.write(rowx, 18, pay, print_dateR)
                    else:
                        sheet.write(rowx, 18, 0.0, print_dateR)
                    
                    if fault > 0.0:
                        sheet.write(rowx, 19, fault, print_dateR)
                    else:
                        sheet.write(rowx, 19, 0.0, print_dateR)
                        
                    if te > 0.0:
                        sheet.write(rowx, 20, te, print_dateR)
                    else:
                        sheet.write(rowx, 20, 0.0, print_dateR)
                    
                    if adv > 0.0:
                        sheet.write(rowx, 21, adv, print_dateR)
                    else:
                        sheet.write(rowx, 21, 0.0, print_dateR)
                    
                    if give > 0.0:
                        sheet.write(rowx, 22, give, print_dateR)
                    else:
                        sheet.write(rowx, 22, 0.0, print_dateR)
                    
                    if emp.bank_account_id:
                        sheet.write(rowx, 23, emp.bank_account_id.acc_number, print_dateR)
                    else:
                        sheet.write(rowx, 23, '', print_dateR)
                    
                        
                    

                        
                        
                    rowx +=1
                num +=1
                
        sheet.write_merge(rowx, rowx, 0, 3, u'Нийт', line_center)
        sheet.write(rowx, 4, total_salary, print_dateR)
        sheet.write(rowx, 5, work_time_wdt, print_dateR)
        sheet.write(rowx, 6, total_work_time, print_dateR)
        sheet.write(rowx, 7, work_day_mwd, print_dateR)
        sheet.write(rowx, 8, work_total_day_wdd, print_dateR)
        sheet.write(rowx, 9, total_cs, print_dateR)
        sheet.write(rowx, 10, total_kpi, print_dateR)
        sheet.write(rowx, 11, total_rs, print_dateR)
        sheet.write(rowx, 12, total_fdd, print_dateR)
        sheet.write(rowx, 13, total_tcs, print_dateR)
        sheet.write(rowx, 14, total_si11, print_dateR)
        sheet.write(rowx, 15, total_ndsh, print_dateR)
        sheet.write(rowx, 16, total_ll, print_dateR)
        sheet.write(rowx, 17, total_ph, print_dateR)
        sheet.write(rowx, 18, total_pay, print_dateR)
        sheet.write(rowx, 19, total_fault, print_dateR)
        sheet.write(rowx, 20, total_te, print_dateR)
        sheet.write(rowx, 21, total_adv, print_dateR)
        sheet.write(rowx, 22, total_give, print_dateR)
        sheet.write(rowx, 23, '', print_dateR)


        
        rowx += 2
        sheet.write(rowx, 2, u'Тооцоолсон Ня-бо: ......................................./ /', nonline)
        sheet.write(rowx+1, 2, u'Хянасан Ерөнхий ня-бо:................................/               /', nonline)
        inch = 1000
        sheet.col(0).width = 1*inch
        sheet.col(1).width = 3*inch
        sheet.col(2).width = 4*inch
        sheet.col(3).width = 6*inch
        sheet.col(4).width = 3*inch
        sheet.col(5).width = 6*inch
        sheet.col(6).width = 3*inch
        sheet.row(2).height = 800   



        return {'data':book,'directory_name':u'Цалингийн тайлан',
                'attache_name':u'Цалингийн тайлан'} 
    