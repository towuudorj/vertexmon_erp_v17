# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
from xlwt import Workbook, Formula

class MultiCompanyProfitExcelReport(models.TransientModel):
    """
        Татварын албанд зориулсан Орлогын тайлан
    """
    _name = "multi.company.profit.excel.report"
    _description = "Tax Department"
    
    company_id=fields.Many2one('res.company', string='Company', required=True,
                               default=lambda self: self.env.user.company_id)
    fiscalyear_id = fields.Many2one('account.fiscal.year', string='Fiscal year',required=True)
    date_from=fields.Date("Start Date", required=True,default=fields.Date.context_today)
    date_to=fields.Date("End Date", required=True,default=fields.Date.context_today)
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
            'data': {'model': 'multi.company.profit.excel.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Account profit multi company report'}
        }         
    
    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        header = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': 16,
                                    
                                    })
        header_txt = workbook.add_format({
                                    'align': 'center',
                                    'font_size': 12,
                                    'text_wrap': True,
                                })
        
        header_title = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'bold': True,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    
                                })

        data_bold_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'bold': True,
                                    'font_size': 12,
                                    'num_format': '#,##0.00; (#,##0.00)'
                                })  

        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00; (#,##0.00)'
                                })

        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00; (#,##0.00)'
                                })

        sheet.set_column(0, 0, 10)
        sheet.set_column(1, 1, 60)
        sheet.set_column(2, 4, 20)

        

        sheet.write("D1", u'Маягт CT-3', header)
        
        
        sheet.merge_range("A2:D2", u'ОРЛОГЫН ДЭЛГЭРЭНГҮЙ ТАЙЛАН', header)
        sheet.merge_range("C3:D3", u"%s" % (data['company_name']), header_txt)
        sheet.merge_range("C4:D4", u'(Аж ахуй нэгж, байгууллагын нэр)', header_txt)
        sheet.write("D5", u'%s - %s' % (data['start_date'],data['end_date']), header_txt)
        
        
        account_obj = self.env['account.account']
        type_obj = self.env['account.account.type']
        profit_obj = self.env['account.income.type']
        move_line_obj = self.env['account.move.line']

        journal_obj = self.env['account.journal']
        journal_ids = journal_obj.search([('company_id','=',data['company_id']),('type','!=','opening')]).ids

        company_id_dlp = self.env['res.company'].search([('name','=','Ди Эл Пи ХХК')],limit=1)
        company_id_vmc = self.env['res.company'].search([('name','=','Ви Эм Си холдинг ХХК')],limit=1)
        f_journal_ids = journal_obj.search([('type','=','opening'),('company_id','=',data['company_id'])],limit=1)
        f_journal_ids_dlp = journal_obj.search([('type','=','opening'),('company_id','=',company_id_dlp.id)],limit=1)
        f_journal_ids_vmc = journal_obj.search([('type','=','opening'),('company_id','=',company_id_vmc.id)],limit=1)
        journal_dlp_ids = journal_obj.search([('company_id','=',company_id_dlp.id),('type','!=','opening')]).ids
        journal_vmc_ids = journal_obj.search([('company_id','=',company_id_vmc.id),('type','!=','opening')]).ids
        rowx = 7
        sheet.write("A%s"%rowx, u'Мөрийн дугаар', header_title)
        sheet.write("B%s"%rowx, u'Үзүүлэлт', header_title)
        sheet.write("C%s"%rowx, u'', header_title)
        sheet.write("D%s"%rowx, u'%s'%data['end_date'], header_title)
        rowx += 1

        if data['target_move'] =='posted':
            state = ['posted']
        else:
            state = ['posted','draft']
        
        profit = profit_obj.search([('company_id','=',data['company_id'])])
        profit = profit_obj.search([('company_id','=',data['company_id'])])
        profit = profit_obj.search([('company_id','=',data['company_id'])])



        last_number = 1
        for line in profit:
            sum_prev_balance = sum_balance = 0.0
            if int(line.seq_type) == 1:
                pre_account_id = account_obj.search([('income_id','=',line.id)])
                account_id = account_obj.search([('income_id','=',line.id)])
                
                pre_account_ids = self.action_account_ids(pre_account_id.ids)
                account_ids = self.action_account_ids(account_id.ids)
                
                


                if len(pre_account_ids) == 1:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',pre_account_ids[0]),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',pre_account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                else:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(pre_account_ids)),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(pre_account_ids)),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    
                if len(account_ids)==1:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',account_ids[0]),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                else:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(account_ids)),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(account_ids)),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                        
                
                sheet.write("A%s"%rowx, '%s'%last_number, data_left)
                sheet.write("B%s"%rowx, line.name, data_left)
                

                for pre_account in pre_move_line_ids:
                    if pre_account.debit < 0.0 and pre_account.credit == 0.0:
                        sum_prev_balance -=(pre_account.debit*(-1))
                    elif pre_account.credit == 0.0 and pre_account.debit > 0.0:
                        sum_prev_balance -=pre_account.debit
                    elif pre_account.credit < 0.0 and pre_account.debit == 0.0:
                        sum_prev_balance +=pre_account.credit*(-1)
                    
                    elif pre_account.credit > 0.0 and pre_account.debit == 0.0:
                        sum_prev_balance +=pre_account.credit
                    
                    
                if sum_prev_balance < 0.0:
                    sum_prev_balance = sum_prev_balance*(-1)
                    
                sheet.write("C%s"%rowx, sum_prev_balance, data_right)
                for ml in move_line_ids:
                    if ml.debit < 0.0 and ml.credit == 0.0:
                        sum_balance -=(ml.debit*(-1))
                    elif ml.credit == 0.0 and ml.debit > 0.0:
                        sum_balance -=ml.debit
                    elif ml.credit < 0.0 and ml.debit == 0.0:
                        sum_balance +=ml.credit*(-1)
                    elif ml.credit > 0.0 and ml.debit == 0.0:
                        sum_balance +=ml.credit
                        
                if sum_balance < 0.0:
                    sum_balance = sum_balance*(-1)
                sheet.write("D%s"%rowx, sum_balance, data_right)

                rowx +=1
                last_number +=1
        sum_prev_balance *= -1
        sum_balance *= -1
        # НИЙТ АШИГ (АЛДАГДАЛ)



        sheet.write("A%s"%rowx, '%s'%last_number, data_left)
        sheet.write("B%s"%rowx, u'Нийт ашиг (алдагдал)',data_right)
        sheet.write_formula("C%s"%rowx, f'=C8-C9', data_right)
        sheet.write_formula("D%s"%rowx, f'=D8-D9', data_right)
        rowx +=1
        last_number +=1
        for line in profit:
            income_balance = 0
            pre_income_balance = 0
            expense_balance = 0
            pre_expense_balance = 0
            if int(line.seq_type) == 2:
                sheet.write("A%s"%rowx, '%s'%last_number, data_left)
                sheet.write("B%s"%rowx, line.name, data_left)
                
                pre_account_id = account_obj.search([('income_id','=',line.id)])
                account_id = account_obj.search([('income_id','=',line.id)])
                
                pre_account_ids = self.action_account_ids(pre_account_id.ids)
                account_ids = self.action_account_ids(account_id.ids)


                    
                if len(pre_account_ids) == 1:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',pre_account_ids[0]),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',pre_account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                else:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(pre_account_ids)),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(pre_account_ids)),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    
                if len(account_ids)==1:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',account_ids[0]),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                else:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(account_ids)),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(account_ids)),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                
                for pre_account in pre_move_line_ids:
                    if pre_account.debit < 0.0 and pre_account.credit == 0.0:
                        pre_income_balance -=(pre_account.debit*(-1))
                    elif pre_account.credit == 0.0 and pre_account.debit > 0.0:
                        pre_income_balance -=pre_account.debit
                    elif pre_account.credit < 0.0 and pre_account.debit == 0.0:
                        pre_income_balance +=pre_account.credit*(-1)
                    
                    elif pre_account.credit > 0.0 and pre_account.debit == 0.0:
                        pre_income_balance +=pre_account.credit
                        
                
                
                sheet.write("C%s"%rowx, pre_income_balance, data_right)
                for ml in move_line_ids:
                    if ml.debit < 0.0 and ml.credit == 0.0:
                        income_balance -=(ml.debit*(-1))
                    elif ml.credit == 0.0 and ml.debit > 0.0:
                        income_balance -=ml.debit
                    elif ml.credit < 0.0 and ml.debit == 0.0:
                        income_balance +=ml.credit*(-1)
                    elif ml.credit > 0.0 and ml.debit == 0.0:
                        income_balance +=ml.credit
                        
                sheet.write("D%s"%rowx, income_balance, data_right)

                last_number +=1
                rowx +=1
            if int(line.seq_type) == 3:
                sheet.write("A%s"%rowx, '%s'%last_number, data_left)
                sheet.write("B%s"%rowx, line.name, data_left)
                pre_account_id = account_obj.search([('income_id','=',line.id)])
                account_id = account_obj.search([('income_id','=',line.id)])
                
                pre_account_ids = self.action_account_ids(pre_account_id.ids)
                account_ids = self.action_account_ids(account_id.ids)
                        
                    
                if len(pre_account_ids) == 1:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',pre_account_ids[0]),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',pre_account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                else:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(pre_account_ids)),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(pre_account_ids)),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    
                if len(account_ids)==1:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',account_ids[0]),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                else:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(account_ids)),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(account_ids)),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                
                
                for pre_account in pre_move_line_ids:
                    if pre_account.debit < 0.0 and pre_account.credit == 0.0:
                        pre_expense_balance +=(pre_account.debit*(-1))
                    elif pre_account.credit == 0.0 and pre_account.debit > 0.0:
                        pre_expense_balance +=pre_account.debit
                    elif pre_account.credit < 0.0 and pre_account.debit == 0.0:
                        pre_expense_balance -=pre_account.credit*(-1)
                    
                    elif pre_account.credit > 0.0 and pre_account.debit == 0.0:
                        pre_expense_balance -=pre_account.credit
                        
                
                sheet.write("C%s"%rowx, pre_expense_balance, data_right)
                for ml in move_line_ids:
                    if ml.debit < 0.0 and ml.credit == 0.0:
                        expense_balance +=(ml.debit*(-1))
                    elif ml.credit == 0.0 and ml.debit > 0.0:
                        expense_balance +=ml.debit
                    elif ml.credit < 0.0 and ml.debit == 0.0:
                        expense_balance -=ml.credit*(-1)
                    elif ml.credit > 0.0 and ml.debit == 0.0:
                        expense_balance -=ml.credit
                sheet.write("D%s"%rowx, expense_balance, data_right)
                last_number +=1
                rowx +=1

        
        # ҮНДСЭН ҮЙЛ АЖИЛЛАГААНЫ АШИГ
        sheet.write("A%s"%rowx, '%s'%last_number, data_left)
        sheet.write("B%s"%rowx, u'Татвар төлөхийн өмнөх ашиг (алдагдал)',data_left)
        sheet.write_formula("C%s"%rowx, f'=C10+C11+C12+C13+C14+C15-C16-C17-C18-C19+C20+C21+C22+C23+C24', data_right)
        sheet.write_formula("D%s"%rowx, f'D10+D11+D12+D13+D14+D15-D16-D17-D18-D19+D20+D21+D22+D23+D24', data_right)
        rowx +=1
        last_number +=1
        for line in profit:
            expense_balance = 0
            pre_expense_balance = 0
            if int(line.seq_type)==4:
                sheet.write("A%s"%rowx, '%s'%last_number, data_left)
                sheet.write("B%s"%rowx, line.name, data_left)
                pre_account_id = account_obj.search([('income_id','=',line.id)])
                account_id = account_obj.search([('income_id','=',line.id)])
                
                pre_account_ids = self.action_account_ids(pre_account_id.ids)
                account_ids = self.action_account_ids(account_id.ids)

                    
                if len(pre_account_ids) == 1:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',pre_account_ids[0]),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',pre_account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                else:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(pre_account_ids)),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(pre_account_ids)),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    
                if len(account_ids)==1:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',account_ids[0]),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                else:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(account_ids)),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(account_ids)),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                account_id = account_obj.search([('income_id','=',line.id)])
                pre_account_id = account_obj.search([('income_id','=',line.id)])
                
                for pre_account in pre_move_line_ids:
                    if pre_account.debit < 0.0 and pre_account.credit == 0.0:
                        sum_prev_balance +=(pre_account.debit*(-1))
                    elif pre_account.credit == 0.0 and pre_account.debit > 0.0:
                        sum_prev_balance +=pre_account.debit
                    elif pre_account.credit < 0.0 and pre_account.debit == 0.0:
                        sum_prev_balance -=pre_account.credit*(-1)
                    
                    elif pre_account.credit > 0.0 and pre_account.debit == 0.0:
                        sum_prev_balance -=pre_account.credit
                        
                
               # sheet.write(rowx, 2, sum_prev_balance, data_right)
                for ml in move_line_ids:
                    if ml.debit < 0.0 and ml.credit == 0.0:
                        sum_balance +=(ml.debit*(-1))
                    elif ml.credit == 0.0 and ml.debit > 0.0:
                        sum_balance +=ml.debit
                    elif ml.credit < 0.0 and ml.debit == 0.0:
                        sum_balance -=ml.credit*(-1)
                    elif ml.credit > 0.0 and ml.debit == 0.0:
                        sum_balance -=ml.credit
               # sheet.write(rowx, 3, sum_balance, data_right)
               
                sheet.write("C%s"%rowx, sum_prev_balance, data_right)
                #for account in account_id:
                #    print("loggg",account.balance)
                #    if account.balance < 0.0:
                #        expense_balance +=(account.balance*(-1))
                #    else:
                #        expense_balance +=account.balance
                sheet.write("D%s"%rowx, sum_balance, data_right)
                rowx +=1
                last_number +=1
        # ТАТВАР ТӨЛӨХИЙН ӨМНӨХ АШИГ
        sheet.write("A%s"%rowx, '%s'%last_number,data_left)
        sheet.write("B%s"%rowx, u'Татварын дараахь ашиг (алдагдал)', data_left)
        sheet.write_formula("C%s"%rowx, f'=C25-C26', data_bold_right)
        sheet.write_formula("D%s"%rowx, f'=D25-D26', data_bold_right)
        rowx +=1

        last_number +=1
        # ТАТВАРЫН ДАРААХ АШИГ
        sheet.write("A%s"%rowx, '%s'%last_number, data_left)
        sheet.write("B%s"%rowx, u'Зогсоосон үйл ажиллагааны татварын дараахь ашиг (алдагдал)',data_left)
        sheet.write("C%s"%rowx, 0, data_right)
        sheet.write("D%s"%rowx, 0, data_right)
        rowx +=1
        last_number +=1

        # ЕРДИЙН АЖИЛЛАГААНЫ АШИГ (АЛДАГДАЛ)
        sheet.write("A%s"%rowx, '%s'%last_number,data_left)
        sheet.write("B%s"%rowx, u'Тайлант үеийн цэвэр ашиг (алдагдал)',data_left)
        sheet.write_formula("C%s"%rowx, f'=C27-C28', data_right)
        sheet.write_formula("D%s"%rowx, f'=D27-D28', data_right)
        rowx +=1
        last_number +=1


        # ЦЭВЭР АШИГ
        sheet.write("A%s"%rowx, '%s'%last_number,data_left)
        sheet.write("B%s"%rowx,  u'Бусад дэлгэрэнгүй орлого', data_left)
        sheet.write_formula("C%s"%rowx, f'=C31+C32', data_bold_right)
        sheet.write_formula("D%s"%rowx, f'=D31+D32', data_bold_right)   
        rowx +=1
        last_number +1
        for line in profit:
            other_income_balance = 0
            pre_other_income_balance = 0
            if int(line.seq_type)==5:
                sheet.write("A%s"%rowx, '%s'%line.sequence, data_left)
                sheet.write("B%s"%rowx, line.name, data_left)
                pre_account_id = account_obj.search([('income_id','=',line.id)])
                account_id = account_obj.search([('income_id','=',line.id)])
                
                pre_account_ids = self.action_account_ids(pre_account_id.ids)
                account_ids = self.action_account_ids(account_id.ids)
                    
                if len(pre_account_ids) == 1:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',pre_account_ids[0]),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',pre_account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                else:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(pre_account_ids)),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(pre_account_ids)),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    
                if len(account_ids)==1:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',account_ids[0]),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','=',account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                else:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(account_ids)),('move_id.state','=',state[0]),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                    else:
                        move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(account_ids)),('move_id.state','in',tuple(state)),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                
                for pre_account in pre_move_line_ids:
                    if pre_account.debit < 0.0 and pre_account.credit == 0.0:
                        pre_other_income_balance +=(pre_account.debit*(-1))
                    elif pre_account.credit == 0.0 and pre_account.debit > 0.0:
                        pre_other_income_balance +=pre_account.debit
                    elif pre_account.credit < 0.0 and pre_account.debit == 0.0:
                        pre_other_income_balance -=pre_account.credit*(-1)
                    
                    elif pre_account.credit > 0.0 and pre_account.debit == 0.0:
                        pre_other_income_balance -=pre_account.credit
                        
                        
                
                sheet.write("C%s"%rowx, pre_other_income_balance, data_right)
                for ml in move_line_ids:
                    if ml.debit < 0.0 and ml.credit == 0.0:
                        other_income_balance +=(ml.debit*(-1))
                    elif ml.credit == 0.0 and ml.debit > 0.0:
                        other_income_balance +=ml.debit
                    elif ml.credit < 0.0 and ml.debit == 0.0:
                        other_income_balance -=ml.credit*(-1)
                    elif ml.credit > 0.0 and ml.debit == 0.0:
                        other_income_balance -=ml.credit
                sheet.write("D%s"%rowx, other_income_balance, data_right)
                rowx +=1
        last_number +=1

        # ЦЭВЭР АШИГ
        sheet.write("A%s"%rowx, '%s'%last_number, data_left)
        sheet.write("B%s"%rowx,  u'Орлогын нийт дүн', data_left)
        sheet.write("C%s"%rowx, f'=C29+C30', data_right)
        sheet.write("D%s"%rowx, f'=D29+D30', data_right)
        rowx +=1
        last_number +=1


        # ЦЭВЭР АШИГ
        sheet.write("A%s"%rowx, '%s'%last_number, data_left)
        sheet.write("B%s"%rowx,  u'Нэгж хувьцаанд ноогдох суурь ашиг (алдагдал)', data_left)
        sheet.write("C%s"%rowx, f'=C33', data_right)
        sheet.write("D%s"%rowx, f'=D33', data_right)
        
        

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()