# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
from xlwt import Workbook, Formula
from datetime import datetime

class profit_excel_report(models.TransientModel):
    """
        Татварын албанд зориулсан Орлогын тайлан
    """
    _name = "profit.excel.report"
    _inherit = ['xls.report.base']
    _description = "Tax Department"
    
    company_id=fields.Many2one('res.company', string='Company', required=True,
                               default=lambda self: self.env.user.company_id)
    date_from=fields.Date("Start Date", required=True,default=fields.Date.context_today)
    date_to=fields.Date("End Date", required=True,default=fields.Date.context_today)
    target_move=fields.Selection([('posted', 'All Posted Entries'),
                                     ('all', 'All Entries'),
                                    ], string='State', required=True, default='posted')

    def get_report_data(self):
        data = super(profit_excel_report, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': str(self.date_from),
            'end_date': str(self.date_to),
            'target_move': self.target_move,
        })
        return data
    
    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'profit.excel.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Profit excel report'}
        }

    def action_account_ids(self,account_id):
        account_ids = []
        account_obj = self.env['account.account']
        if len(account_id) == 1:
            acc_ids = account_obj.search([('parent_id','=',account_id)])
            if not acc_ids:
                for acc in account_id:
                    account_ids.append(acc)
            else:
                for line in acc_ids:
                    account_ids.append(line.id)
                    line_acc_ids = account_obj.search([('parent_id','=',line.id)])
                    if line_acc_ids:
                        for lines in line_acc_ids:
                            account_ids.append(lines.id)
                            new_acc_ids = account_obj.search([('parent_id','=',lines.id)])
                            if new_acc_ids:
                                for nacc_id in new_acc_ids:
                                    account_ids.append(nacc_id.id)
        else:
            acc_ids = account_obj.search([('parent_id','in',tuple(account_id))])
            if not acc_ids:
                for acc in account_id:
                    account_ids.append(acc)
            else:
                for line in acc_ids:
                    account_ids.append(line.id)
                    line_acc_ids = account_obj.search([('parent_id','=',line.id)])
                    if line_acc_ids:
                        for lines in line_acc_ids:
                            account_ids.append(lines.id)
                            new_acc_ids = account_obj.search([('parent_id','=',lines.id)])
                            if new_acc_ids:
                                for nacc_id in new_acc_ids:
                                    account_ids.append(nacc_id.id)
                            
            
        return account_ids

    def get_xlsx_report(self, data, response, get_file=False):
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
        
        header_txt_right = workbook.add_format({
                                    'align': 'right',
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
        
        data_bold_left = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'bold': True,
                                    'font_size': 12,
                                    'num_format': '#,##0.00; (#,##0.00)'
                                })

        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.set_column(0, 0, 5)
        sheet.set_column(1, 1, 60)
        sheet.set_column(2, 4, 25)

        self = self.env[self._name]

        sheet.write("D1", u'Маягт CT-3', header)
        
        
        sheet.merge_range("A2:D2", u'ОРЛОГЫН ДЭЛГЭРЭНГҮЙ ТАЙЛАН', header)
        sheet.merge_range("C3:D3", u"%s" % (data['company_name']), header_txt)
        sheet.merge_range("C4:D4", u'(Аж ахуй нэгж, байгууллагын нэр)', header_txt)
        sheet.merge_range("C5:D5", u'%s - %s' % (data['start_date'], data['end_date']), header_txt_right)
        
        
        account_obj = self.env['account.account']
        type_obj = self.env['account.account.type']
        profit_obj = self.env['account.income.type']
        move_line_obj = self.env['account.move.line']
        journal_obj = self.env['account.journal']
        journal_ids = journal_obj.search([('company_id','=',data['company_id']),('type','not in',('opening','closing'))]).ids

        last_year_date = datetime.strptime(data['start_date'], "%Y-%m-%d").date()
        last_year_date = last_year_date.replace(year=last_year_date.year - 1, month=12, day=31)
        last_year_date = str(last_year_date)

        rowx = 7
        sheet.write("A%s"%rowx, u'Мөрийн дугаар', header_title)
        sheet.write("B%s"%rowx, u'Үзүүлэлт', header_title)
        sheet.write("C%s"%rowx, u'%s' % last_year_date, header_title)
        sheet.write("D%s"%rowx, u'%s - %s'%(data['start_date'], data['end_date']), header_title)
        rowx += 1

        if data['target_move'] =='posted':
            state = ['posted']
        else:
            state = ['posted','draft']
        
        profit = profit_obj.search([('company_id','=',data['company_id'])])


        last_number = 1
        for line in profit:
            sum_prev_balance = sum_balance = 0.0
            if int(line.seq_type) == 1:
                pre_account_id = account_obj.search([('income_id','=',line.id)])
                account_id = account_obj.search([('income_id','=',line.id)])
                
                pre_account_ids = self.action_account_ids(pre_account_id.ids)
                account_ids = self.action_account_ids(account_id.ids)
                
                if pre_account_ids:
                    pre_move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(pre_account_ids)),('move_id.state','in',state),('date','<=',last_year_date)])
                else:
                    pre_move_line_ids = []

                if account_ids:
                    move_line_ids = move_line_obj.search([('move_id.journal_id','in', tuple(journal_ids)),('account_id','in',tuple(account_ids)),('move_id.state','in',state),('date','>=',data['start_date']),('date','<=',data['end_date'])])
                else:
                    move_line_ids = []
                
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
                    
                sheet.write("C%s"%rowx, abs(sum_prev_balance), data_right)
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
                sheet.write("D%s"%rowx, abs(sum_balance), data_right)

                rowx +=1
                last_number +=1
        sum_prev_balance *= -1
        sum_balance *= -1
        # НИЙТ АШИГ (АЛДАГДАЛ)



        sheet.write("A%s"%rowx, '%s'%last_number, data_left)
        sheet.write("B%s"%rowx, u'Нийт ашиг (алдагдал)', data_bold_left)
        sheet.write_formula(f"C{rowx}", f'=C{rowx-2}-C{rowx-1}', data_bold_right)
        sheet.write_formula(f"D{rowx}", f'=D{rowx-2}-D{rowx-1}', data_bold_right)
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

                if pre_account_ids:
                    pre_move_line_ids = move_line_obj.search([('move_id.journal_id', 'in', tuple(journal_ids)), ('account_id', 'in', tuple(pre_account_ids)),('move_id.state', 'in', state), ('date', '<=', last_year_date)])
                else:
                    pre_move_line_ids = []

                if account_ids:
                    move_line_ids = move_line_obj.search([('move_id.journal_id', 'in', tuple(journal_ids)), ('account_id', 'in', tuple(account_ids)),('move_id.state', 'in', state), ('date', '>=', data['start_date']),('date', '<=', data['end_date'])])
                else:
                    move_line_ids = []
                
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

                if pre_account_ids:
                    pre_move_line_ids = move_line_obj.search([('move_id.journal_id', 'in', tuple(journal_ids)), ('account_id', 'in', tuple(pre_account_ids)),('move_id.state', 'in', state), ('date', '<=', last_year_date)])
                else:
                    pre_move_line_ids = []

                if account_ids:
                    move_line_ids = move_line_obj.search([('move_id.journal_id', 'in', tuple(journal_ids)), ('account_id', 'in', tuple(account_ids)),('move_id.state', 'in', state), ('date', '>=', data['start_date']),('date', '<=', data['end_date'])])
                else:
                    move_line_ids = []
                
                
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
        sheet.write("B%s"%rowx, u'Татвар төлөхийн өмнөх ашиг (алдагдал)',data_bold_left)
        sheet.write_formula("C%s"%rowx, f'=C10+C11+C12+C13+C14+C15-C16-C17-C18-C19+C20+C21+C22+C23+C24', data_bold_right)
        sheet.write_formula("D%s"%rowx, f'=D10+D11+D12+D13+D14+D15-D16-D17-D18-D19+D20+D21+D22+D23+D24', data_bold_right)
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

                if pre_account_ids:
                    pre_move_line_ids = move_line_obj.search([('move_id.journal_id', 'in', tuple(journal_ids)), ('account_id', 'in', tuple(pre_account_ids)),('move_id.state', 'in', state), ('date', '<=', last_year_date)])
                else:
                    pre_move_line_ids = []

                if account_ids:
                    move_line_ids = move_line_obj.search([('move_id.journal_id', 'in', tuple(journal_ids)), ('account_id', 'in', tuple(account_ids)),('move_id.state', 'in', state), ('date', '>=', data['start_date']),('date', '<=', data['end_date'])])
                else:
                    move_line_ids = []

                # account_id = account_obj.search([('income_id','=',line.id)])
                # pre_account_id = account_obj.search([('income_id','=',line.id)])
                
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
        sheet.write("B%s"%rowx, u'Татварын дараахь ашиг (алдагдал)', data_bold_left)
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
        sheet.write("B%s"%rowx, u'Тайлант үеийн цэвэр ашиг (алдагдал)',data_bold_left)
        sheet.write_formula("C%s"%rowx, f'=C27-C28', data_bold_right)
        sheet.write_formula("D%s"%rowx, f'=D27-D28', data_bold_right)
        rowx +=1
        last_number +=1


        # ЦЭВЭР АШИГ
        sheet.write("A%s"%rowx, '%s'%last_number,data_left)
        sheet.write("B%s"%rowx,  u'Бусад дэлгэрэнгүй орлого', data_bold_left)
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

                if pre_account_ids:
                    pre_move_line_ids = move_line_obj.search([('move_id.journal_id', 'in', tuple(journal_ids)), ('account_id', 'in', tuple(pre_account_ids)),('move_id.state', 'in', state), ('date', '<=', last_year_date)])
                else:
                    pre_move_line_ids = []

                if account_ids:
                    move_line_ids = move_line_obj.search([('move_id.journal_id', 'in', tuple(journal_ids)), ('account_id', 'in', tuple(account_ids)),('move_id.state', 'in', state), ('date', '>=', data['start_date']),('date', '<=', data['end_date'])])
                else:
                    move_line_ids = []
                
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
        sheet.write("B%s"%rowx,  u'Орлогын нийт дүн', data_bold_left)
        sheet.write("C%s"%rowx, f'=C29+C30', data_bold_right)
        sheet.write("D%s"%rowx, f'=D29+D30', data_bold_right)
        rowx +=1
        last_number +=1


        # ЦЭВЭР АШИГ
        sheet.write("A%s"%rowx, '%s'%last_number, data_left)
        sheet.write("B%s"%rowx,  u'Нэгж хувьцаанд ноогдох суурь ашиг (алдагдал)', data_bold_left)
        sheet.write("C%s"%rowx, f'=C33', data_bold_right)
        sheet.write("D%s"%rowx, f'=D33', data_bold_right)
        
        

        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return


        
    

    
    
        