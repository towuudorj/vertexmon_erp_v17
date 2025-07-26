# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class MultiCompanyBalanceSheet(models.TransientModel):
    """
        Санхүүгийн байдлын тайлан
    """
    _name = "multi.company.balance.sheet"
    _description = "Balance Sheet Report - Mongolia"
    
    company_id=fields.Many2one('res.company', string='Company', required=True, 
                               default=lambda self: self.env.user.company_id)
    date_from=fields.Date('Date Start',default=fields.Date.context_today)
    date_to=fields.Date("Date Stop",default=fields.Date.context_today)
    fiscalyear_id = fields.Many2one('account.fiscal.year',string='Fiscal year', required=True)
    target_move=fields.Selection([('posted', 'All Posted Entries'),
                                         ('all', 'All Entries'),
                                        ], string='State', required=True, default='posted')
    


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.date_from,
            'end_date': self.date_to,
            'target_move': self.target_move
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'multi.company.balance.sheet',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Account balance multi company report'}
        }


    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': 16
                                    })
        txt = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12
                                })

        title = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12
                                })
        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'text_wrap': True,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })
        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })


        data_bold_left = workbook.add_format({
                                    'align': 'left',
                                    'bold': True,
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })
        
        data_bold_center = workbook.add_format({
                                    'align': 'center',
                                    'bold': True,
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })

        sheet.set_column(0, 0, 10)
        sheet.set_column(1, 1, 60)
        sheet.set_column(2, 10, 20)

        sheet.merge_range('A1:D1', u'САНХҮҮ БАЙДЛЫН ТАЙЛАН', head)
        sheet.merge_range('A2:B2', u"%s" % (data['company_name']), head)
        sheet.merge_range('E2:F2', u"Ди Эл Пи ХХК", head)
        sheet.merge_range('G2:H2', u"Ви Эм Си Холдинг ХХК", head)
        sheet.merge_range('I2:J2', u"Нийт", head)

        sheet.merge_range('A3:B3', u'(Аж ахуй нэгж, байгууллагын нэр)', head)
        sheet.merge_range('C2:D2', u'%s - %s' % (data['start_date'],data['end_date']), head)
        sheet.write('D5', u'(төгрөгөөр)', head)
        rowx = 6
        sheet.write('A%s'%rowx, u'Д/д', title)
        sheet.write("B%s"%rowx, u'Үзүүлэлт', title)
        sheet.write("C%s"%rowx, u'%s'%(data['start_date']), title)
        sheet.write("D%s"%rowx, u'%s'%(data['end_date']), title)
        sheet.write("E%s"%rowx, u'%s'%(data['start_date']), title)
        sheet.write("F%s"%rowx, u'%s'%(data['end_date']), title)
        sheet.write("G%s"%rowx, u'%s'%(data['start_date']), title)
        sheet.write("H%s"%rowx, u'%s'%(data['end_date']), title)
        sheet.write("I%s"%rowx, u'%s'%(data['start_date']), title)
        sheet.write("J%s"%rowx, u'%s'%(data['end_date']), title)
        rowx += 1

        account_move_obj = self.env['account.move']
        account_move_line_obj = self.env['account.move.line']
        balance_report_obj = self.env['account.balance.type']
        journal_obj = self.env['account.journal']
        company_id_dlp = self.env['res.company'].search([('name','=','Ди Эл Пи ХХК')],limit=1)
        company_id_vmc = self.env['res.company'].search([('name','=','Ви Эм Си холдинг ХХК')],limit=1)
        f_journal_ids = journal_obj.search([('type','=','opening'),('company_id','=',data['company_id'])],limit=1)
        f_journal_ids_dlp = journal_obj.search([('type','=','opening'),('company_id','=',company_id_dlp.id)],limit=1)
        f_journal_ids_vmc = journal_obj.search([('type','=','opening'),('company_id','=',company_id_vmc.id)],limit=1)


        balance_report_id = balance_report_obj.search([('company_id','=',data['company_id'])])
        balance_report_id_dlp = balance_report_obj.search([('company_id','=',company_id_dlp.id)])
        balance_report_id_vmc = balance_report_obj.search([('company_id','=',company_id_vmc.id)])
        account_obj = self.env['account.account']
        if data['target_move'] =='posted':
            state = ['posted']
        else:
            state = ['posted','draft']
        num = 1
        print ("journal_id",f_journal_ids, company_id_dlp,company_id_vmc)
        for line in balance_report_id:
            sheet.write("A%s"%rowx, num, data_right)
            if line.level == 'level1':
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                sheet.write("B%s"%rowx, u'%s'%line.name, data_bold_left)
                if line.parent_id.id==False:
                    account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',data['company_id'])])
                    if len(account_ids)>1:
                        accounts = tuple(ac.id for ac in account_ids)
                        if len(state)==1:
                            move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                            pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','=',state)])

                        else:
                            move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',self.company_id.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                            pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',self.company_id.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','in',state)])

                    else:
                        if len(state)==1:
                            move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                            pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','<=',data['end_date']),('parent_state','=',state)])
                           
                        else:
                            move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                            pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',self.company_id.id),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','in',state)])
                    
                    if len(move_line_ids)==1:
                        for mlines in move_line_ids:
                            debit +=mlines.debit
                        for mlines in move_line_ids:
                            credit += mlines.credit
                    else:
                        for mlines in move_line_ids:
                            credit += mlines.credit
                        for mlines in move_line_ids:
                            debit +=mlines.debit
                    
                    
                    total = debit - credit
                    if len(pre_move_line_ids)==1:
                        for pmlines in pre_move_line_ids:
                            pdebit +=pmlines.debit
                        for pmlines in pre_move_line_ids:
                            pcredit += pmlines.credit
                    else:
                        for pmlines in pre_move_line_ids:
                            pcredit += pmlines.credit
                        for pmlines in pre_move_line_ids:
                            pdebit +=pmlines.debit
                    
                    
                    pre_total = pdebit - pcredit
                    
                    sheet.write("C%s"%rowx, pre_total,data_right)
                    sheet.write("D%s"%rowx, total,data_right)
                num +=1
                rowx +=1

            elif line.level == 'level2':
                sheet.write("B%s"%rowx, u'%s'%line.name,data_bold_left)
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                balance_id = balance_report_obj.search([('parent_id','=',line.id)])
                for bline in balance_id:
                    account_ids = []
                    li_account_ids = account_obj.search([('balance_id','=',bline.id),('company_id','=',data['company_id'])])
                    for acc in li_account_ids:
                        account_ids.append(acc.id)
                    line_balance_id = balance_report_obj.search([('parent_id','=',bline.id)])
                    for blines in line_balance_id:
                        line_account_ids = account_obj.search([('balance_id','=',blines.id),('company_id','=',data['company_id'])])
                        for li in line_account_ids:
                            account_ids.append(li.id)
                        fline_balance_id = balance_report_obj.search([('parent_id','=',blines.id)])
                        for flines in fline_balance_id:
                            fline_account_ids = account_obj.search([('balance_id','=',flines.id),('company_id','=',data['company_id'])])
                            for fli in fline_account_ids:
                                account_ids.append(fli.id)
                    
                    if account_ids!=[]:
                        if len(account_ids)>1:
                            if len(state)==1:
                                move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',tuple(account_ids)),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                                pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',tuple(account_ids)),('date','<=',data['start_date']),('parent_state','=',state)])
                            else:
                                move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',self.company_id.id),('account_id','in',tuple(account_ids)),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                                pre_move_line_ids = account_move_line_obj.search(('journal_id','=',f_journal_ids.id),[('company_id','=',data['company_id']),('account_id','in',tuple(account_ids)),('date','<=',data['start_date']),('parent_state','in',state)])
                        else:
                            if len(state)==1:
                                move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',self.company_id.id),('account_id','=',account_ids[0]),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                                pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','=',account_ids[0]),('date','<=',data['start_date']),('parent_state','=',state)])
                            else:
                                move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',self.company_id.id),('account_id','=',account_ids[0]),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                                pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','=',account_ids[0]),('date','<=',data['start_date']),('parent_state','in',state)])
                            
                        if len(move_line_ids)==1:
                            for mlines in move_line_ids:
                                debit +=mlines.debit
                            for mlines in move_line_ids:
                                credit += mlines.credit
                        else:
                            for mlines in move_line_ids:
                                debit +=mlines.debit
                            for mlines in move_line_ids:
                                credit += mlines.credit
                                
                        if len(pre_move_line_ids)==1:
                            for pmlines in pre_move_line_ids:
                                pdebit +=pmlines.debit
                            for pmlines in pre_move_line_ids:
                                pcredit += pmlines.credit
                        else:
                            for pmlines in pre_move_line_ids:
                                pdebit +=pmlines.debit
                            for pmlines in pre_move_line_ids:
                                pcredit += pmlines.credit
                            
                    total = debit - credit
                    pre_total = pdebit - pcredit
                
                if total < 0.0:
                    total = total*(-1)
                    
                if pre_total<0.0:
                    pre_total = pre_total*(-1)
                sheet.write("C%s"%rowx, pre_total, data_bold_center)
                sheet.write("D%s"%rowx, total, data_bold_center)
                num +=1
                rowx +=1
            elif line.level == 'level3':
                sheet.write("B%s"%rowx, u'%s'%line.name,data_left)
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',data['company_id'])])
                if len(account_ids)>1:
                    accounts = tuple(ac.id for ac in account_ids)
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','in',state)])
                else:
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','in',state)])
                    
                if len(move_line_ids)==1:
                    for mlines in move_line_ids:
                        credit +=mlines.credit
                    for mlines in move_line_ids:
                        debit +=mlines.debit
                else:
                    for mlines in move_line_ids:
                        debit += mlines.debit
                    for mlines in move_line_ids:
                        credit +=mlines.credit

                if len(pre_move_line_ids)==1:
                    for pmlines in pre_move_line_ids:
                        pcredit +=pmlines.credit
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit
                else:
                    for pmlines in pre_move_line_ids:
                        pdebit += pmlines.debit
                    for pmlines in pre_move_line_ids:
                        pcredit +=pmlines.credit
                        
                total = debit - credit
                pre_total = pdebit - pcredit
                sheet.write("C%s"%rowx, pre_total,data_right)
                sheet.write("D%s"%rowx, total,data_right)
                num +=1
                rowx +=1
            else:
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                sheet.write("B%s"%rowx, u'%s'%line.name,data_left)
                account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',data['company_id'])])
                if len(account_ids)>1:
                    accounts = tuple(ac.id for ac in account_ids)
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','in',state)])
                else:
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','in',state)])
                    
                if len(move_line_ids)==1:
                    for mlines in move_line_ids:
                        debit +=mlines.debit
                        
                    for mlines in move_line_ids:
                        credit += mlines.credit
                else:
                    for mlines in move_line_ids:
                        credit += mlines.credit
                    for mlines in move_line_ids:
                        debit +=mlines.debit
                        
                        
                
                if len(pre_move_line_ids)==1:
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit
                        
                    for mlines in pre_move_line_ids:
                        pcredit += pmlines.credit
                else:
                    for pmlines in pre_move_line_ids:
                        pcredit += pmlines.credit
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit
                                                
                total = debit - credit
                pre_total = pdebit - pcredit
                
                sheet.write("C%s"%rowx, pre_total,data_right)
                sheet.write("D%s"%rowx, total,data_right)
                num +=1
                rowx +=1
        rowxdlp = 7
        for line in balance_report_id_dlp:
            #sheet.write("E%s"%rowx, num, data_right)
            if line.level == 'level1':
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                #sheet.write("F%s"%rowx, u'%s'%line.name, data_bold_left)
                if line.parent_id.id==False:
                    account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',company_id_dlp.id)])
                    if len(account_ids)>1:
                        accounts = tuple(ac.id for ac in account_ids)
                        if len(state)==1:
                            move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                            pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','=',state)])

                        else:
                            move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                            pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','in',state)])

                    else:
                        if len(state)==1:
                            move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                            pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids.id),('date','<=',data['end_date']),('parent_state','=',state)])
                           
                        else:
                            move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                            pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','in',state)])
                    
                    if len(move_line_ids)==1:
                        for mlines in move_line_ids:
                            debit +=mlines.debit
                        for mlines in move_line_ids:
                            credit += mlines.credit
                    else:
                        for mlines in move_line_ids:
                            credit += mlines.credit
                        for mlines in move_line_ids:
                            debit +=mlines.debit
                    
                    
                    total = debit - credit
                    if len(pre_move_line_ids)==1:
                        for pmlines in pre_move_line_ids:
                            pdebit +=pmlines.debit
                        for pmlines in pre_move_line_ids:
                            pcredit += pmlines.credit
                    else:
                        for pmlines in pre_move_line_ids:
                            pcredit += pmlines.credit
                        for pmlines in pre_move_line_ids:
                            pdebit +=pmlines.debit
                    
                    
                    pre_total = pdebit - pcredit
                    
                    sheet.write("E%s"%rowxdlp, pre_total,data_right)
                    sheet.write("F%s"%rowxdlp, total,data_right)
                num +=1
                rowxdlp +=1

            elif line.level == 'level2':
                #sheet.write("B%s"%rowx, u'%s'%line.name,data_bold_left)
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                balance_id = balance_report_obj.search([('parent_id','=',line.id)])
                for bline in balance_id:
                    account_ids = []
                    li_account_ids = account_obj.search([('balance_id','=',bline.id),('company_id','=',company_id_dlp.id)])
                    for acc in li_account_ids:
                        account_ids.append(acc.id)
                    line_balance_id = balance_report_obj.search([('parent_id','=',bline.id)])
                    for blines in line_balance_id:
                        line_account_ids = account_obj.search([('balance_id','=',blines.id),('company_id','=',company_id_dlp.id)])
                        for li in line_account_ids:
                            account_ids.append(li.id)
                        fline_balance_id = balance_report_obj.search([('parent_id','=',blines.id)])
                        for flines in fline_balance_id:
                            fline_account_ids = account_obj.search([('balance_id','=',flines.id),('company_id','=',company_id_dlp.id)])
                            for fli in fline_account_ids:
                                account_ids.append(fli.id)
                    
                    if account_ids!=[]:
                        if len(account_ids)>1:
                            if len(state)==1:
                                move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',tuple(account_ids)),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                                pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',tuple(account_ids)),('date','<=',data['start_date']),('parent_state','=',state)])
                            else:
                                move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',tuple(account_ids)),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                                pre_move_line_ids = account_move_line_obj.search(('journal_id','=',f_journal_ids_dlp.id),[('company_id','=',company_id_dlp.id),('account_id','in',tuple(account_ids)),('date','<=',data['start_date']),('parent_state','in',state)])
                        else:
                            if len(state)==1:
                                move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids[0]),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                                pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids[0]),('date','<=',data['start_date']),('parent_state','=',state)])
                            else:
                                move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids[0]),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                                pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids[0]),('date','<=',data['start_date']),('parent_state','in',state)])
                            
                        if len(move_line_ids)==1:
                            for mlines in move_line_ids:
                                debit +=mlines.debit
                            for mlines in move_line_ids:
                                credit += mlines.credit
                        else:
                            for mlines in move_line_ids:
                                debit +=mlines.debit
                            for mlines in move_line_ids:
                                credit += mlines.credit
                                
                        if len(pre_move_line_ids)==1:
                            for pmlines in pre_move_line_ids:
                                pdebit +=pmlines.debit
                            for pmlines in pre_move_line_ids:
                                pcredit += pmlines.credit
                        else:
                            for pmlines in pre_move_line_ids:
                                pdebit +=pmlines.debit
                            for pmlines in pre_move_line_ids:
                                pcredit += pmlines.credit
                            
                    total = debit - credit
                    pre_total = pdebit - pcredit
                
                if total < 0.0:
                    total = total*(-1)
                    
                if pre_total<0.0:
                    pre_total = pre_total*(-1)
                sheet.write("E%s"%rowxdlp, pre_total, data_bold_center)
                sheet.write("F%s"%rowxdlp, total, data_bold_center)
                num +=1
                rowxdlp +=1
            elif line.level == 'level3':
                #sheet.write("B%s"%rowx, u'%s'%line.name,data_left)
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',company_id_dlp.id)])
                if len(account_ids)>1:
                    accounts = tuple(ac.id for ac in account_ids)
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','in',state)])
                else:
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','in',state)])
                    
                if len(move_line_ids)==1:
                    for mlines in move_line_ids:
                        credit +=mlines.credit
                    for mlines in move_line_ids:
                        debit +=mlines.debit
                else:
                    for mlines in move_line_ids:
                        debit += mlines.debit
                    for mlines in move_line_ids:
                        credit +=mlines.credit

                if len(pre_move_line_ids)==1:
                    for pmlines in pre_move_line_ids:
                        pcredit +=pmlines.credit
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit
                else:
                    for pmlines in pre_move_line_ids:
                        pdebit += pmlines.debit
                    for pmlines in pre_move_line_ids:
                        pcredit +=pmlines.credit
                        
                total = debit - credit
                pre_total = pdebit - pcredit
                sheet.write("E%s"%rowxdlp, pre_total,data_right)
                sheet.write("F%s"%rowxdlp, total,data_right)
                num +=1
                rowxdlp +=1
            else:
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                #sheet.write("B%s"%rowx, u'%s'%line.name,data_left)
                account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',company_id_dlp.id)])
                if len(account_ids)>1:
                    accounts = tuple(ac.id for ac in account_ids)
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','in',state)])
                else:
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_dlp.id),('company_id','=',company_id_dlp.id),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','in',state)])
                    
                if len(move_line_ids)==1:
                    for mlines in move_line_ids:
                        debit +=mlines.debit
                        
                    for mlines in move_line_ids:
                        credit += mlines.credit
                else:
                    for mlines in move_line_ids:
                        credit += mlines.credit
                    for mlines in move_line_ids:
                        debit +=mlines.debit
                        
                        
                
                if len(pre_move_line_ids)==1:
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit
                        
                    for mlines in pre_move_line_ids:
                        pcredit += pmlines.credit
                else:
                    for pmlines in pre_move_line_ids:
                        pcredit += pmlines.credit
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit
                                                
                total = debit - credit
                pre_total = pdebit - pcredit
                
                sheet.write("E%s"%rowxdlp, pre_total,data_right)
                sheet.write("F%s"%rowxdlp, total,data_right)
                num +=1
                rowxdlp +=1
        rowxvmc = 7
        for line in balance_report_id_vmc:
            #sheet.write("A%s"%rowx, num, data_right)
            if line.level == 'level1':
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                #sheet.write("B%s"%rowx, u'%s'%line.name, data_bold_left)
                if line.parent_id.id==False:
                    account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',company_id_vmc.id)])
                    if len(account_ids)>1:
                        accounts = tuple(ac.id for ac in account_ids)
                        if len(state)==1:
                            move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                            pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','=',state)])

                        else:
                            move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                            pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','in',state)])

                    else:
                        if len(state)==1:
                            move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                            pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids.id),('date','<=',data['end_date']),('parent_state','=',state)])
                           
                        else:
                            move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                            pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','in',state)])
                    
                    if len(move_line_ids)==1:
                        for mlines in move_line_ids:
                            debit +=mlines.debit
                        for mlines in move_line_ids:
                            credit += mlines.credit
                    else:
                        for mlines in move_line_ids:
                            credit += mlines.credit
                        for mlines in move_line_ids:
                            debit +=mlines.debit
                    
                    
                    total = debit - credit
                    if len(pre_move_line_ids)==1:
                        for pmlines in pre_move_line_ids:
                            pdebit +=pmlines.debit
                        for pmlines in pre_move_line_ids:
                            pcredit += pmlines.credit
                    else:
                        for pmlines in pre_move_line_ids:
                            pcredit += pmlines.credit
                        for pmlines in pre_move_line_ids:
                            pdebit +=pmlines.debit
                    
                    
                    pre_total = pdebit - pcredit
                    
                    sheet.write("G%s"%rowxvmc, pre_total,data_right)
                    sheet.write("H%s"%rowxvmc, total,data_right)
                num +=1
                rowxvmc +=1

            elif line.level == 'level2':
                #sheet.write("B%s"%rowx, u'%s'%line.name,data_bold_left)
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                balance_id = balance_report_obj.search([('parent_id','=',line.id)])
                for bline in balance_id:
                    account_ids = []
                    li_account_ids = account_obj.search([('balance_id','=',bline.id),('company_id','=',company_id_vmc.id)])
                    for acc in li_account_ids:
                        account_ids.append(acc.id)
                    line_balance_id = balance_report_obj.search([('parent_id','=',bline.id)])
                    for blines in line_balance_id:
                        line_account_ids = account_obj.search([('balance_id','=',blines.id),('company_id','=',company_id_vmc.id)])
                        for li in line_account_ids:
                            account_ids.append(li.id)
                        fline_balance_id = balance_report_obj.search([('parent_id','=',blines.id)])
                        for flines in fline_balance_id:
                            fline_account_ids = account_obj.search([('balance_id','=',flines.id),('company_id','=',company_id_vmc.id)])
                            for fli in fline_account_ids:
                                account_ids.append(fli.id)
                    
                    if account_ids!=[]:
                        if len(account_ids)>1:
                            if len(state)==1:
                                move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',tuple(account_ids)),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                                pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',tuple(account_ids)),('date','<=',data['start_date']),('parent_state','=',state)])
                            else:
                                move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',tuple(account_ids)),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                                pre_move_line_ids = account_move_line_obj.search(('journal_id','=',f_journal_ids_vmc.id),[('company_id','=',company_id_vmc.id),('account_id','in',tuple(account_ids)),('date','<=',data['start_date']),('parent_state','in',state)])
                        else:
                            if len(state)==1:
                                move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids[0]),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                                pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids[0]),('date','<=',data['start_date']),('parent_state','=',state)])
                            else:
                                move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids[0]),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                                pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids[0]),('date','<=',data['start_date']),('parent_state','in',state)])
                            
                        if len(move_line_ids)==1:
                            for mlines in move_line_ids:
                                debit +=mlines.debit
                            for mlines in move_line_ids:
                                credit += mlines.credit
                        else:
                            for mlines in move_line_ids:
                                debit +=mlines.debit
                            for mlines in move_line_ids:
                                credit += mlines.credit
                                
                        if len(pre_move_line_ids)==1:
                            for pmlines in pre_move_line_ids:
                                pdebit +=pmlines.debit
                            for pmlines in pre_move_line_ids:
                                pcredit += pmlines.credit
                        else:
                            for pmlines in pre_move_line_ids:
                                pdebit +=pmlines.debit
                            for pmlines in pre_move_line_ids:
                                pcredit += pmlines.credit
                            
                    total = debit - credit
                    pre_total = pdebit - pcredit
                
                if total < 0.0:
                    total = total*(-1)
                    
                if pre_total<0.0:
                    pre_total = pre_total*(-1)
                sheet.write("G%s"%rowxvmc, pre_total, data_bold_center)
                sheet.write("H%s"%rowxvmc, total, data_bold_center)
                num +=1
                rowxvmc +=1
            elif line.level == 'level3':
                #sheet.write("B%s"%rowx, u'%s'%line.name,data_left)
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',company_id_vmc.id)])
                if len(account_ids)>1:
                    accounts = tuple(ac.id for ac in account_ids)
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','in',state)])
                else:
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','in',state)])
                    
                if len(move_line_ids)==1:
                    for mlines in move_line_ids:
                        credit +=mlines.credit
                    for mlines in move_line_ids:
                        debit +=mlines.debit
                else:
                    for mlines in move_line_ids:
                        debit += mlines.debit
                    for mlines in move_line_ids:
                        credit +=mlines.credit

                if len(pre_move_line_ids)==1:
                    for pmlines in pre_move_line_ids:
                        pcredit +=pmlines.credit
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit
                else:
                    for pmlines in pre_move_line_ids:
                        pdebit += pmlines.debit
                    for pmlines in pre_move_line_ids:
                        pcredit +=pmlines.credit
                        
                total = debit - credit
                pre_total = pdebit - pcredit
                sheet.write("G%s"%rowxvmc, pre_total,data_right)
                sheet.write("H%s"%rowxvmc, total,data_right)
                num +=1
                rowxvmc +=1
            else:
                debit = 0.0
                credit = 0.0
                total = 0.0
                pdebit = 0.0
                pcredit = 0.0
                pre_total = 0.0
                #sheet.write("B%s"%rowx, u'%s'%line.name,data_left)
                account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',company_id_vmc.id)])
                if len(account_ids)>1:
                    accounts = tuple(ac.id for ac in account_ids)
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',accounts),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','in',accounts),('date','<=',data['start_date']),('parent_state','in',state)])
                else:
                    if len(state)==1:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','=',state)])
                    else:
                        move_line_ids = account_move_line_obj.search([('journal_id','!=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids_vmc.id),('company_id','=',company_id_vmc.id),('account_id','=',account_ids.id),('date','<=',data['start_date']),('parent_state','in',state)])
                    
                if len(move_line_ids)==1:
                    for mlines in move_line_ids:
                        debit +=mlines.debit
                        
                    for mlines in move_line_ids:
                        credit += mlines.credit
                else:
                    for mlines in move_line_ids:
                        credit += mlines.credit
                    for mlines in move_line_ids:
                        debit +=mlines.debit
                        
                        
                
                if len(pre_move_line_ids)==1:
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit
                        
                    for mlines in pre_move_line_ids:
                        pcredit += pmlines.credit
                else:
                    for pmlines in pre_move_line_ids:
                        pcredit += pmlines.credit
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit
                                                
                total = debit - credit
                pre_total = pdebit - pcredit
                
                sheet.write("G%s"%rowxvmc, pre_total,data_right)
                sheet.write("H%s"%rowxvmc, total,data_right)
                num +=1
                rowxvmc +=1
        sheet.write("I%s"%rowx, f"=C7+E7+G7",data_right)
        sheet.write("J%s"%rowx, f"=D8+F8+H8",data_right)
        sheet.write("I%s"%rowx, f"=C9+E9+G9",data_right)
        sheet.write("J%s"%rowx, f"=D10+F10+H10",data_right)
        sheet.write("I%s"%rowx, f"=C11+E11+G11",data_right)
        sheet.write("J%s"%rowx, f"=D12+F12+H12",data_right)
        sheet.write("I%s"%rowx, f"=C13+E13+G13",data_right)
        sheet.write("J%s"%rowx, f"=D14+F14+H14",data_right)
        sheet.write("I%s"%rowx, f"=C15+E15+G15",data_right)
        sheet.write("J%s"%rowx, f"=D16+F16+H16",data_right)
        sheet.write("I%s"%rowx, f"=C17+E17+G17",data_right)
        sheet.write("J%s"%rowx, f"=D18+F18+H18",data_right)
        sheet.write("I%s"%rowx, f"=C19+E19+G19",data_right)
        sheet.write("J%s"%rowx, f"=D20+F20+H20",data_right)
        sheet.write("I%s"%rowx, f"=C21+E21+G21",data_right)
        sheet.write("J%s"%rowx, f"=D22+F22+H22",data_right)
        sheet.write("I%s"%rowx, f"=C23+E23+G23",data_right)
        sheet.write("J%s"%rowx, f"=D24+F24+H24",data_right)
        sheet.write("I%s"%rowx, f"=C25+E25+G25",data_right)
        sheet.write("J%s"%rowx, f"=D26+F26+H26",data_right)
        sheet.write("I%s"%rowx, f"=C27+E27+G27",data_right)
        sheet.write("J%s"%rowx, f"=D28+F28+H28",data_right)
        sheet.write("I%s"%rowx, f"=C29+E29+G29",data_right)
        sheet.write("J%s"%rowx, f"=D30+F30+H30",data_right)
        sheet.write("I%s"%rowx, f"=C31+E31+G31",data_right)
        sheet.write("J%s"%rowx, f"=D32+F32+H32",data_right)
        sheet.write("I%s"%rowx, f"=C33+E33+G33",data_right)
        sheet.write("J%s"%rowx, f"=D34+F34+H34",data_right)
        sheet.write("I%s"%rowx, f"=C35+E35+G35",data_right)
        sheet.write("J%s"%rowx, f"=D36+F36+H36",data_right)
        sheet.write("I%s"%rowx, f"=C37+E37+G37",data_right)
        sheet.write("J%s"%rowx, f"=D38+F38+H38",data_right)
        sheet.write("J%s"%rowx, f"=D39+F39+H39",data_right)
        sheet.write("J%s"%rowx, f"=D40+F40+H40",data_right)
        sheet.write("J%s"%rowx, f"=D41+F41+H41",data_right)
        sheet.write("J%s"%rowx, f"=D42+F42+H42",data_right)
        sheet.write("J%s"%rowx, f"=D43+F43+H43",data_right)
        sheet.write("J%s"%rowx, f"=D44+F44+H44",data_right)
        sheet.write("J%s"%rowx, f"=D45+F45+H45",data_right)
        sheet.write("J%s"%rowx, f"=D46+F46+H46",data_right)
        sheet.write("J%s"%rowx, f"=D47+F47+H47",data_right)
        sheet.write("J%s"%rowx, f"=D48+F48+H48",data_right)
        sheet.write("J%s"%rowx, f"=D49+F49+H49",data_right)
        sheet.write("J%s"%rowx, f"=D50+F50+H50",data_right)
        sheet.write("J%s"%rowx, f"=D51+F51+H51",data_right)
        sheet.write("J%s"%rowx, f"=D52+F52+H52",data_right)
        sheet.write("J%s"%rowx, f"=D53+F53+H53",data_right)
        sheet.write("J%s"%rowx, f"=D54+F54+H54",data_right)
        sheet.write("J%s"%rowx, f"=D55+F55+H55",data_right)
        sheet.write("J%s"%rowx, f"=D56+F56+H56",data_right)
        sheet.write("J%s"%rowx, f"=D57+F57+H57",data_right)
        sheet.write("J%s"%rowx, f"=D58+F58+H58",data_right)
        sheet.write("J%s"%rowx, f"=D59+F59+H59",data_right)
        sheet.write("J%s"%rowx, f"=D60+F60+H60",data_right)
        sheet.write("J%s"%rowx, f"=D61+F61+H61",data_right)
        sheet.write("J%s"%rowx, f"=D62+F62+H62",data_right)
        sheet.write("J%s"%rowx, f"=D63+F63+H63",data_right)
        sheet.write("J%s"%rowx, f"=D64+F64+H64",data_right)
        sheet.write("J%s"%rowx, f"=D65+F65+H65",data_right)
        sheet.write("J%s"%rowx, f"=D66+F66+H66",data_right)
        sheet.write("J%s"%rowx, f"=D67+F67+H67",data_right)
        sheet.write("J%s"%rowx, f"=D68+F68+H68",data_right)





        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
