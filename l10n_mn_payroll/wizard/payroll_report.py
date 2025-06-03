# -*- coding: utf-8 -*-

import xlrd, base64, xlwt
from io import StringIO
from odoo import api, fields, models

class PayrollExcelReport(models.TransientModel):
    _name = 'payroll.excel.report'
    _inherit = 'abstract.report.excel'
    _description = 'Payroll Excel Report'
    

    dep_id = fields.Many2one('hr.department',string='Department')
    employee_id = fields.Many2one('hr.employee',string='Employee')
    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    company_id = fields.Many2one('res.company','Company')
 
    

    
    
     
    def get_export_data(self):
        context = self._context
        ezxf = xlwt.easyxf
        styledict = self.get_easyxf_styles()
        book = xlwt.Workbook(encoding='utf8')
        header = ezxf('font: bold on; align: wrap off, vert centre, horiz centre;font: height 220')
        header1 = ezxf('font: bold off; align: wrap on, vert centre, horiz left;font: height 200')
        print_dateL = ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 200; borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        print_dateR = ezxf('font: bold off; align: wrap off, vert centre, horiz right;font: height 200; borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        line = ezxf('font: bold off; align: wrap on, vert centre, horiz left;font: height 200; borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        line_data = ezxf('font: bold on; align: wrap on, vert centre, horiz right;font: height 200; borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        line_center = ezxf('font: bold on; align: wrap on, vert centre, horiz center;font: height 200; borders: left thin, right thin, top thin, bottom thin;')
        nonline = ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 200;')
        sheet = book.add_sheet('Hr salary report')
        
        employee_obj = self.env['hr.employee']
        payslip_obj = self.env['hr.payslip']
        category_obj = self.env['hr.salary.rule.category']
        self._cr.execute("select name,code from hr_salary_rule_category")
        categ_ids = self._cr.dictfetchall()
        resource_obj = self.env['resource.resource']
        resource_ids = resource_obj.search([('active','in',(True,False))])
        employee_ids = []
        if self.dep_id.id !=None and self.dep_id.id !=False:
            self._cr.execute("select id, last_name from hr_employee where department_id = %s order by last_name"%self.dep_id.id)
            employee = self._cr.fetchall()
            for line in employee:
                employee_ids.append(line[0])
        else:
            self._cr.execute("select id,last_name from hr_employee order by last_name")
            employee = self._cr.fetchall()
            for line in employee:
                employee_ids.append(line[0])
        
        
        
        rowx = 2
        col = 3
        num = 1
        #sheet.write(rowx, 0, u'Хүйс', styledict['heading_xf'])
        sheet.write(rowx, 0, u'№', styledict['heading_xf'])
        sheet.write(rowx, 1, u'Овог', styledict['heading_xf'])
        sheet.write(rowx, 2, u'Ажилтны нэр', styledict['heading_xf'])
        sheet.write(rowx, 3, u'Хэлтэс', styledict['heading_xf'])
        sheet.write(rowx, 4, u'Регистрийн дугаар', styledict['heading_xf'])
        sheet.write(rowx, 5, u'НД-ын дэвтрийн дугаар', styledict['heading_xf'])
        sheet.write(rowx, 6, u'ЭМД-ын дэвтрийн дугаар', styledict['heading_xf'])
        sheet.write(rowx, 7, u'Үндсэн цалин', styledict['heading_xf'])
        sheet.write(rowx, 8, u'Цалингийн нэмэгдэл', styledict['heading_xf'])
        sheet.write(rowx, 9, u'Цалингийн бууралт', styledict['heading_xf'])
        sheet.write(rowx, 10, u'Ажиллах цаг', styledict['heading_xf'])
        sheet.write(rowx, 11, u'Ажилласан цаг /өдөр/', styledict['heading_xf'])
        sheet.write(rowx, 12, u'Ажилласан цаг /шөнө/', styledict['heading_xf'])
        sheet.write(rowx, 13, u'Ажилласан цаг нийт', styledict['heading_xf'])
        sheet.write(rowx, 14, u'Бодогдсон цалин /өдөр/', styledict['heading_xf'])
        sheet.write(rowx, 15, u'Бодогдсон цалин /шөнө/', styledict['heading_xf'])
        sheet.write(rowx, 16, u'Шөнийн цагийн нэмэгдэл цалин', styledict['heading_xf'])
        sheet.write(rowx, 17, u'Бодогдсон нийт цалин', styledict['heading_xf'])
        sheet.write(rowx, 18, u'Амралтын мөнгө', styledict['heading_xf'])
        sheet.write(rowx, 19, u'Гар утас нэмэгдэл', styledict['heading_xf'])
        sheet.write(rowx, 20, u'Хоол унааны нэмэгдэл', styledict['heading_xf'])
        sheet.write(rowx, 21, u'Сарын бонус', styledict['heading_xf'])
        sheet.write(rowx, 22, u'Жилийн бонус', styledict['heading_xf'])
        sheet.write(rowx, 23, u'Нийт бонус', styledict['heading_xf'])
        sheet.write(rowx, 24, u'Олговол зохих', styledict['heading_xf'])
        sheet.write(rowx, 25, u'ЭМНДШ', styledict['heading_xf'])
        sheet.write(rowx, 26, u'ХХОАТ', styledict['heading_xf'])
        sheet.write(rowx, 27, u'Гар утас суутгал', styledict['heading_xf'])
        sheet.write(rowx, 28, u'Суутгал ТШ', styledict['heading_xf'])
        sheet.write(rowx, 29, u'Зөрчлийн суутгал', styledict['heading_xf'])
        sheet.write(rowx, 30, u'Амралтын мөнгөний олголт',styledict['heading_xf'])
        sheet.write(rowx, 31, u'Нийт суутгал', styledict['heading_xf'])
        sheet.write(rowx, 32, u'Урьдчилгаа цалин', styledict['heading_xf'])
        sheet.write(rowx, 33, u'Гарт олгох', styledict['heading_xf'])
        sheet.write(rowx, 34, u'Дансны дугаар',styledict['heading_xf'])
        sheet.write(rowx, 35, u'НДШ,ХХОАТ хөнгөлөлт',styledict['heading_xf'])
        sheet.write(rowx, 36, u'Даатгуулагчийн төрлийн код',styledict['heading_xf'])
        sheet.write(rowx, 37, u'Ажил мэргэжлийн дугаар',styledict['heading_xf'])
        rowx +=1
        name = ''
        total_amount = 0.0
        give_total = 0.0
        total_salary = 0.0
        salary_add = 0.0
        salary_ded = 0.0
        total_work_time = 0.0
        work_time = 0.0
        night_time = 0.0
        total_time = 0.0
        vs_total = 0.0
        tcs_total = 0.0
        adv_total = 0.0
        phone_total = 0.0
        food_total = 0.0
        si_total = 0.0
        pit_total = 0.0
        tded_total = 0.0
        fault_total = 0.0
        pud_total = 0.0
        cns_total = 0.0
        ph_total = 0.0
        bonus_total = 0.0
        bonus_year = 0.0
        bonus_month = 0.0
        cs_total = 0.0
        bs = 0.0
        
        ded = 0.0
        TWT = 0.0
        ad = 0.0
        ad_cs_total = 0.0
        cs = 0.0
        cns = 0.0
        wt = 0.0
        nt = 0.0
        tcs = 0.0
        vs = 0.0
        pha = 0.0
        bonusm = 0.0
        fd = 0.0
        bonusy = 0.0
        bonus = 0.0
        tcds = 0.0
        si = 0.0
        
        ph = 0.0
        
        fault = 0.0
        tded = 0.0
        soh = 0.0
        adv = 0.0
        vsh = 0.0
        vsh_total = 0.0
        ndsh_discount = 0.0
        ndsh_discount_total = 0.0
        for emp in employee_obj.browse(employee_ids):
            col = 2
            zod20 = 0.0
            pit = 0.0
            pud = 0.0
            payslip_id = payslip_obj.search([('date_from','>=',self.start_date),('date_to','<=',self.end_date),('employee_id','=',emp.id)])
            if payslip_id:

                    
                sheet.write(rowx, 0, u'%s'%num, print_dateL)
                sheet.write(rowx, 1, u'%s'%(emp.last_name), print_dateL)
                sheet.write(rowx, 2, u'%s'%(emp.name), print_dateL)
                sheet.write(rowx, 3, u'%s'%(emp.department_id.name), print_dateL)
                sheet.write(rowx, 4, u'%s'%(emp.register_number), print_dateR)
                sheet.write(rowx, 5, u'%s'%(emp.identification_id), print_dateR)
                sheet.write(rowx, 6, u'%s'%(emp.passport_id),print_dateR)
                sheet.write(rowx, 36, u'%s'%(emp.inshurance_id.code), print_dateR)
                sheet.write(rowx, 37, u'%s'%(emp.job_id.code), print_dateR)
                
                
                for li in payslip_id:
                  #  sheet.write(rowx, 0, u'%s'%emp.gender, styledict['heading_xf'])
                    
                    for line in li.line_ids:
                        if line.code == 'BS':
                            bs = line.total
                            #sheet.write(rowx, 2, u'%s'%line.total, styledict['heading_xf'])
                            total_salary +=line.total
                        #else:
                        #    sheet.write(rowx, col, 0.0, styledict['heading_xf'])
                        
                        if line.code == 'ZOD20' or line.code=='ZAD30' or line.code=='ZAD10' or line.code == 'ZAD15':
                            zod20 = line.total
                            #sheet.write(rowx, 3, u'%s'%line.total, styledict['heading_xf'])
                            salary_add +=line.total
                        #else:
                        #    sheet.write(rowx, col+1, 0.0, styledict['heading_xf'])
                        
                        if line.code == 'DED':
                            ded = line.total
                            #sheet.write(rowx, 4, u'%s'%line.total, styledict['heading_xf'])
                            salary_ded +=line.total
                        elif line.code == 'TWT':
                            TWT = line.total
                            #sheet.write(rowx, 5, u'%s'%line.total, styledict['heading_xf'])
                            total_work_time +=line.total
                        elif line.code == 'WT':
                            wt = line.total
                            #sheet.write(rowx, 6, u'%s'%line.total, styledict['heading_xf'])
                            work_time +=line.total    
                        elif line.code == 'NT':
                            nt = line.total
                            #sheet.write(rowx, 7, u'%s'%line.total, styledict['heading_xf'])
                            night_time +=line.total
                        elif line.code == 'TWDT':
                            TWDT = line.total
                            #sheet.write(rowx, 8, u'%s'%line.total, styledict['heading_xf'])
                            total_time +=line.total
                        elif line.code == 'AD':
                            ad = line.total
                            #sheet.write(rowx, 9, u'%s'%line.total, styledict['heading_xf'])
                            ad_cs_total +=line.total
                        elif line.code == 'CS':
                            cs = line.total
                           # sheet.write(rowx, 10, u'%s'%line.total, styledict['heading_xf'])
                            cs_total +=line.total
                        elif line.code == 'CNS':
                            cns = line.total
                            #sheet.write(rowx, 11, u'%s'%line.total, styledict['heading_xf'])
                            cns_total +=line.total
                        elif line.code == 'TCS' or line.code == 'TCSI' or line.code == 'TCSI8' or line.code == 'TCSMO' or line.code == 'TCDSIHC' or line.code =='TCSZAD10' or line.code=='TCSZAD15' or line.code=='TCSZOD20' or line.code=='TCSZOD30':
                            tcs = line.total
                            #sheet.write(rowx, 12, u'%s'%line.total, styledict['heading_xf'])
                            tcs_total +=line.total
                        
                        elif line.code == 'VS':
                            vs = line.total
                            #sheet.write(rowx, 13, u'%s'%line.total, styledict['heading_xf'])
                            vs_total +=line.total
                        elif line.code == 'VSH':
                            vsh = line.total
                            vsh_total +=line.total
                        elif line.code == 'PHA':
                            pha = line.total
                            #sheet.write(rowx, 14, u'%s'%line.total, styledict['heading_xf'])
                            phone_total +=line.total
                        elif line.code == 'FD' or line.code == 'FDIHC':
                            fd = line.total
                            #sheet.write(rowx, 15, u'%s'%line.total, styledict['heading_xf'])
                            food_total +=line.total
                        elif line.code == 'BONUSM':
                            bonusm = line.total
                           # sheet.write(rowx, 16, u'%s'%line.total, styledict['heading_xf'])
                            bonus_month +=line.total
                        elif line.code == 'BONUSY':
                            bonusy = line.total
                            #sheet.write(rowx, 17, u'%s'%line.total, styledict['heading_xf'])
                            bonus_year +=line.total
                        elif line.code == 'BONUS':
                            bonus = line.total
                            #sheet.write(rowx, 18, u'%s'%line.total, styledict['heading_xf'])
                            bonus_total +=line.total
                        elif line.code == 'TCDSS' or line.code == 'TCDS' or line.code == 'TCDSA' or line.code == 'TCDSI' or line.code == 'TCDSI8' or line.code == 'TCDSMO':
                            tcds = line.total
                            #sheet.write(rowx, 19, u'%s'%line.total, styledict['heading_xf'])
                            give_total +=line.total
                        elif line.code == 'SI78' or line.code == 'SI10' or line.code == 'SI' or line.code == 'SI108' or line.code == 'SIIV11' or line.code=='SIIV8' or line.code == 'SIMO' or line.code == 'SIIHC11.5':
                            si = line.total
                            #sheet.write(rowx, 20, u'%s'%line.total, styledict['heading_xf'])
                            si_total +=line.total
                        elif line.code == 'PIT' or line.code == 'PIT78' or line.code == 'PIT10' or line.code =='PIT108' or line.code == 'PIT10IV' or line.code =='PIT10MO' or line.code == 'PITIV8' or line.code =='PIT10IHC':
                            pit = line.total
                            #sheet.write(rowx, 21, u'%s'%line.total, styledict['heading_xf'])
                            pit_total +=line.total
                        elif line.code == 'PHD':
                            ph = line.total
                            #sheet.write(rowx, 22, u'%s'%line.total, styledict['heading_xf'])
                            ph_total +=line.total
                        elif line.code == 'PuD' or line.code == 'PHDIHC' or line.code == 'PuDIHC':
                            pud = line.total
                            #sheet.write(rowx, 23, u'%s'%line.total, styledict['heading_xf'])
                            pud_total +=line.total
                        elif line.code == 'FAULT':
                            fault = line.total
                            #sheet.write(rowx, 24, u'%s'%line.total, styledict['heading_xf'])
                            fault_total +=line.total
                        elif line.code == 'TDED' or line.code == 'TDED78' or line.code == 'TDED10' or line.code == 'TDED108' or line.code == 'TDEDIV' or line.code == 'TDEDIV8' or line.code == 'TDEDMO':
                            tded = line.total
                            #sheet.write(rowx, 25, u'%s'%line.total, styledict['heading_xf'])
                            tded_total +=line.total
                        elif line.code == 'D2004':
                            ndsh_discount = line.total
                            ndsh_discount_total +=line.total
                        elif line.code == 'ADV':
                            adv = line.total
                            #sheet.write(rowx, 26, u'%s'%line.total, styledict['heading_xf'])
                            adv_total +=line.total
                        
                        elif line.code == 'SOH11' or line.code =='SOH8.8' or line.code == 'SOH' or line.code == 'SOH108' or line.code =='SOHIV' or line.code == 'SOHIV8' or line.code == 'SOHMO' or line.code =='SOH11IHC':
                            soh = line.total
                            #sheet.write(rowx, 27, u'%s'%line.total, styledict['heading_xf'])
                            total_amount +=line.total
                    
                    
                    if bs > 0.0:
                        sheet.write(rowx, 7, bs, print_dateR)
                    else:
                        sheet.write(rowx, 7, 0.0, print_dateR)
                    if zod20 > 0.0:
                        sheet.write(rowx, 8, zod20, print_dateR)
                    else:
                        sheet.write(rowx, 8, 0.0, print_dateR)
                    if ded > 0.0:
                        sheet.write(rowx, 9, ded, print_dateR)
                    else:
                        sheet.write(rowx, 9, 0.0, print_dateR)
                    if TWT > 0.0:
                        sheet.write(rowx, 10, TWT, print_dateR)
                    else:
                        sheet.write(rowx, 10, 0.0, print_dateR)
                    if wt > 0.0:
                        sheet.write(rowx, 11, wt, print_dateR)
                    else:
                        sheet.write(rowx, 11, 0.0, print_dateR)
                
                    if nt > 0.0:
                        sheet.write(rowx, 12, nt, print_dateR)
                    else:
                        sheet.write(rowx, 12, 0.0, print_dateR)
                
                
                    if TWDT >0.0:
                        sheet.write(rowx, 13, TWDT, print_dateR)
                    else:
                        sheet.write(rowx, 13, 0.0, print_dateR)
                    if ad >0.0:
                        sheet.write(rowx, 14, ad, print_dateR)
                    else:
                        sheet.write(rowx, 14, 0.0, print_dateR)
                    if cs >0.0:
                        sheet.write(rowx, 15, cs, print_dateR)
                    else:
                        sheet.write(rowx, 15, 0.0, print_dateR)
                    if cns > 0.0:
                        sheet.write(rowx, 16, cns, print_dateR)
                    else:
                        sheet.write(rowx, 16, 0.0, print_dateR)
                    if tcs > 0.0:
                        sheet.write(rowx, 17, tcs, print_dateR)
                    else:
                        sheet.write(rowx, 17, 0.0, print_dateR)
                        
                    if vs > 0.0:
                        sheet.write(rowx, 18, vs, print_dateR)
                    else:
                        sheet.write(rowx, 18, 0.0, print_dateR)
                    if pha > 0.0:
                        sheet.write(rowx, 19, pha, print_dateR)
                    else:
                        sheet.write(rowx, 19, 0.0, print_dateR)
                    if fd > 0.0:
                        sheet.write(rowx, 20, fd, print_dateR)
                    else:
                        sheet.write(rowx, 20, 0.0, print_dateR)
                    if bonusm > 0.0:
                        sheet.write(rowx, 21, bonusm, print_dateR)
                    else:
                        sheet.write(rowx, 21, 0.0, print_dateR)
                    if bonusy > 0.0:
                        sheet.write(rowx, 22, bonusy, print_dateR)
                    else:
                        sheet.write(rowx, 22, 0.0, print_dateR)
                    if bonus > 0.0:
                        sheet.write(rowx, 23, bonus, print_dateR)
                    else:
                        sheet.write(rowx, 23, 0.0, print_dateR)
                    if tcds > 0.0:
                        sheet.write(rowx, 24, tcds, print_dateR)
                    else:
                        sheet.write(rowx, 24, 0.0, print_dateR)
                    if si > 0.0:
                        sheet.write(rowx, 25, si, print_dateR)
                    else:
                        sheet.write(rowx, 25, 0.0, print_dateR)
                    if pit > 0.0:
                        sheet.write(rowx, 26, pit, print_dateR)
                    else:
                        sheet.write(rowx, 26, 0.0, print_dateR)
                    if ph > 0.0:
                        sheet.write(rowx, 27, ph, print_dateR)
                    else:
                        sheet.write(rowx, 27, 0.0, print_dateR)
                    if pud > 0.0:
                        sheet.write(rowx, 28, pud, print_dateR)
                    else:
                        sheet.write(rowx, 28, 0.0, print_dateR)
                    if fault > 0.0:
                        sheet.write(rowx, 29, fault, print_dateR)
                    else:
                        sheet.write(rowx, 29, 0.0, print_dateR)
                    if vsh > 0.0:
                        sheet.write(rowx, 30, vsh, print_dateR)
                    else:
                        sheet.write(rowx, 30, 0.0, print_dateR)
                    if tded > 0.0:
                        sheet.write(rowx, 31, tded, print_dateR)
                    else:
                        sheet.write(rowx, 31, 0.0, print_dateR)
                    if adv > 0.0:
                        sheet.write(rowx, 32, adv, print_dateR)
                    else:
                        sheet.write(rowx, 32, 0.0, print_dateR)
                    if soh > 0.0:
                        sheet.write(rowx, 33, soh, print_dateR)
                    else:
                        sheet.write(rowx, 33, 0.0, print_dateR)
                    
                    if ndsh_discount > 0.0:
                        sheet.write(rowx, 35, ndsh_discount, print_dateR)
                    else:
                        sheet.write(rowx, 35, 0.0, print_dateR)
                    
                    if emp.bank_account_id.id:
                        sheet.write(rowx, 34, u'%s'%emp.bank_account_id.acc_number, print_dateR)
                    else:
                        sheet.write(rowx, 34, 0.0, print_dateR)
                        
                        
                    rowx +=1
                num +=1
                
        sheet.write_merge(rowx, rowx, 0, 6, u'Нийт', line_data)
        sheet.write(rowx, 7, total_salary, line_data)
        sheet.write(rowx, 8, salary_add, line_data)
        sheet.write(rowx, 9, salary_ded, line_data)
        sheet.write(rowx, 10, total_work_time, line_data)
        sheet.write(rowx, 11, work_time, line_data)
        sheet.write(rowx, 12, night_time, line_data)
        sheet.write(rowx, 13, total_time, line_data)
        sheet.write(rowx, 14, ad_cs_total, line_data)
        sheet.write(rowx, 15, cs_total, line_data)
        sheet.write(rowx, 16, cns_total, line_data)
        sheet.write(rowx, 17, tcs_total, line_data)
        sheet.write(rowx, 18, vs_total, line_data)
        sheet.write(rowx, 19, phone_total, line_data)
        sheet.write(rowx, 20, food_total, line_data)
        sheet.write(rowx, 21, bonus_month, line_data)
        sheet.write(rowx, 22, bonus_year, line_data)
        sheet.write(rowx, 23, bonus_total, line_data)
        sheet.write(rowx, 24, give_total, line_data)
        sheet.write(rowx, 25, si_total, line_data)
        sheet.write(rowx, 26, pit_total, line_data)
        sheet.write(rowx, 27, ph_total, line_data)
        sheet.write(rowx, 28, pud_total, line_data)
        sheet.write(rowx, 29, fault_total, line_data)
        sheet.write(rowx, 30, vsh_total, line_data)
        sheet.write(rowx, 31, tded_total, line_data)
        sheet.write(rowx, 32, adv_total, line_data)
        sheet.write(rowx, 33, total_amount, line_data)
        sheet.write(rowx, 34, u'', line_data)
        sheet.write(rowx, 35, ndsh_discount_total, line_data)
        
        
        inch = 1000
        sheet.col(0).width = 1*inch
        sheet.col(1).width = 6*inch
        sheet.col(2).width = 7*inch
        sheet.col(3).width = 6*inch
        sheet.col(4).width = 4*inch
        sheet.col(5).width = 4*inch
        sheet.col(6).width = 4*inch
        sheet.col(7).width = 4*inch
        sheet.col(8).width = 4*inch
        sheet.col(9).width = 4*inch
        sheet.col(10).width = 4*inch
        sheet.col(11).width = 4*inch
        sheet.col(12).width = 4*inch
        sheet.col(13).width = 4*inch
        sheet.col(14).width = 4*inch
        sheet.col(15).width = 4*inch
        sheet.col(16).width = 4*inch
        sheet.col(17).width = 4*inch
        sheet.col(18).width = 4*inch
        sheet.col(19).width = 4*inch
        sheet.col(20).width = 4*inch
        sheet.col(21).width = 4*inch
        sheet.col(22).width = 4*inch
        sheet.col(23).width = 4*inch
        sheet.col(24).width = 4*inch
        sheet.col(25).width = 4*inch
        sheet.col(26).width = 4*inch
        sheet.col(27).width = 4*inch
        sheet.col(28).width = 4*inch
        sheet.col(29).width = 4*inch
        sheet.col(30).width = 4*inch
        sheet.col(31).width = 4*inch
        sheet.col(32).width = 4*inch
        sheet.col(33).width = 4*inch
        sheet.col(34).width = 4*inch
        sheet.col(35).width = 4*inch
        sheet.col(36).width = 4*inch
        sheet.col(37).width = 4*inch
        sheet.row(2).height = 800  
        

        
        
        
        
        
        
        return {'data':book, 'directory_name':u'Хүний нөөцийн цалин', 
                'attache_name':u'Хүний нөөцийн цалин'}
