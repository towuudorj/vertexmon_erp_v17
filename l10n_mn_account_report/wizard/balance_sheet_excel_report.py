# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
from datetime import datetime

class balance_sheet_excel(models.TransientModel):
    """
        Санхүүгийн байдлын тайлан
    """
    _name = "balance.sheet.excel"
    _inherit = 'xls.report.base'
    _description = "Balance Sheet Report - Mongolia"
    
    company_id=fields.Many2one('res.company', string='Company', required=True, 
                               default=lambda self: self.env.user.company_id)
    date = fields.Date("Date",default=fields.Date.context_today)
    target_move=fields.Selection([('posted', 'All Posted Entries'),
                                         ('all', 'All Entries'),
                                        ], string='State', required=True, default='posted')

    def get_report_data(self):
        data = super(balance_sheet_excel, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'date': str(self.date),
            'target_move': self.target_move
        })
        return data
    

    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'balance.sheet.excel',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Account balance report'}
        }

    def get_xlsx_report(self, data, response, get_file=False):
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
        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.set_column(0, 0, 10)
        sheet.set_column(1, 1, 60)
        sheet.set_column(2, 4, 20)

        sheet.merge_range('A1:D1', u'САНХҮҮ БАЙДЛЫН ТАЙЛАН', head)
        sheet.merge_range('A2:B2', u"%s" % (data['company_name']), head)

        sheet.merge_range('A3:B3', u'(Аж ахуй нэгж, байгууллагын нэр)', head)
        sheet.merge_range('C2:D2', u'%s' % data['date'], head)
        sheet.write('D5', u'(төгрөгөөр)', head)

        last_year_date = datetime.strptime(data['date'], "%Y-%m-%d").date()
        last_year_date = str(last_year_date.replace(year=last_year_date.year - 1, month=12, day=31))

        rowx = 6
        sheet.write('A%s'%rowx, u'Д/д', title)
        sheet.write("B%s"%rowx, u'Үзүүлэлт', title)
        sheet.write("C%s"%rowx, u'%s'%last_year_date, title)
        sheet.write("D%s"%rowx, u'%s'%(data['date']), title)
        rowx += 1

        account_move_obj = self.env['account.move']
        account_move_line_obj = self.env['account.move.line']
        balance_report_obj = self.env['account.balance.type']
        journal_obj = self.env['account.journal']
        f_journal_ids = journal_obj.search([('type','=','opening'),('company_id','=',data['company_id'])],limit=1)
        journal_ids = journal_obj.search([('company_id','=',data['company_id'])])
        balance_report_id = balance_report_obj.search([('company_id','=',data['company_id'])])
        account_obj = self.env['account.account']
        if data['target_move'] =='posted':
            state = ['posted']
        else:
            state = ['posted','draft']

        num = 1
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
                if not line.parent_id:
                    account_ids = account_obj.search([('balance_id','=',line.id),('company_id','=',data['company_id'])])
                    if len(account_ids)>=1:
                        accounts = account_ids.ids
                        move_line_ids = account_move_line_obj.search([('journal_id','in',tuple(journal_ids.ids)),('company_id','=',data['company_id']),('account_id','in',accounts),('date','<=',data['date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','<=',last_year_date),('parent_state','in',state)])

                        for mlines in move_line_ids:
                            debit +=mlines.debit
                        for mlines in move_line_ids:
                            credit += mlines.credit

                        total = debit - credit

                        for pmlines in pre_move_line_ids:
                            pdebit +=pmlines.debit
                        for pmlines in pre_move_line_ids:
                            pcredit += pmlines.credit

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
                        move_line_ids = account_move_line_obj.search([('journal_id','in',tuple(journal_ids.ids)),('company_id','=',data['company_id']),('account_id','in',account_ids),('date','<=',data['date']),('parent_state','in',state)])
                        pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',account_ids),('date','<=',last_year_date),('parent_state','in',state)])

                        for mlines in move_line_ids:
                            debit +=mlines.debit
                        for mlines in move_line_ids:
                            credit += mlines.credit

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
                if len(account_ids)>=1:
                    accounts = account_ids.ids
                    move_line_ids = account_move_line_obj.search([('journal_id','in',tuple(journal_ids.ids)),('company_id','=',data['company_id']),('account_id','in',accounts),('date','<=',data['date']),('parent_state','in',state)])
                    pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','<=',last_year_date),('parent_state','in',state)])

                    for mlines in move_line_ids:
                        credit +=mlines.credit
                    for mlines in move_line_ids:
                        debit +=mlines.debit

                    for pmlines in pre_move_line_ids:
                        pcredit +=pmlines.credit
                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit

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
                if len(account_ids)>=1:
                    accounts = account_ids.ids
                    move_line_ids = account_move_line_obj.search([('journal_id','in',tuple(journal_ids.ids)),('company_id','=',data['company_id']),('account_id','in',accounts),('date','<=',data['date']),('parent_state','in',state)])
                    pre_move_line_ids = account_move_line_obj.search([('journal_id','=',f_journal_ids.id),('company_id','=',data['company_id']),('account_id','in',accounts),('date','<=',last_year_date),('parent_state','in',state)])

                    for mlines in move_line_ids:
                        debit +=mlines.debit

                    for mlines in move_line_ids:
                        credit += mlines.credit

                    for pmlines in pre_move_line_ids:
                        pdebit +=pmlines.debit

                    for pmlines in pre_move_line_ids:
                        pcredit += pmlines.credit

                    total = debit - credit
                    pre_total = pdebit - pcredit
                
                sheet.write("C%s"%rowx, pre_total,data_right)
                sheet.write("D%s"%rowx, total,data_right)
                num +=1
                rowx +=1

        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return None






        





