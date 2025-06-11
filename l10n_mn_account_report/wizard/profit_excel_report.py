# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class profit_excel_report(models.TransientModel):
    """
        Татварын албанд зориулсан Орлогын тайлан
    """
    _name = "profit.excel.report"
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
            'fiscalyear_id': self.fiscalyear_id.id,
            'state': self.target_move,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'cash.move.line.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Profit excel report'}
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

        sheet.write(0, 3, u'Маягт CT-3', ezxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        sheet.write(3, 1, u"%s" % (self.company_id.name,), ezxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))
        
        sheet.write(1, 1, u'ОРЛОГЫН ДЭЛГЭРЭНГҮЙ ТАЙЛАН', ezxf('font: bold on; align: wrap off, vert centre, horiz centre;font: height 200'))
        
        sheet.write(4, 1, u'(Аж ахуй нэгж, байгууллагын нэр)', ezxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write(4, 2, u'%s' % (self.date_to), ezxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        
        
        rowx = 6
        sheet.write(rowx, 0, u'Мөрийн дугаар', data_style)
        sheet.write(rowx, 1, u'Үзүүлэлт', data_style)
        sheet.write(rowx, 2, u'', data_style)
        sheet.write(rowx, 3, u'%s'%self.date_to, data_style)
        rowx += 1

        
    
    def action_account_ids(self,account_id):
        account_ids = []
        account_obj = self.env['account.account']
        acc_ids = account_obj.search([('parent_id','=',account_id)])
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
    
    
        
    def get_export_data(self):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''
        context = dict(self.env.context)
        context.update({'date_from':self.date_from,
                        'date_to':self.date_to})
        date_str = '%s-%s' % (
            datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime('%Y.%m.%d'),
            datetime.strptime(str(self.date_to), '%Y-%m-%d').strftime('%Y.%m.%d')
        )


        
        ezxf = xlwt.easyxf
        styles = self.get_easyxf_styles()
        account_obj = self.env['account.account']
        type_obj = self.env['account.account.type']
        profit_obj = self.env['account.income.type']
        move_line_obj = self.env['account.move.line']
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet(u'Орлого үр дүн тайлан')
        sheet.portrait = False
        
        data_style = ezxf('font: bold off; align: wrap on, vert centre, horiz centre; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold = ezxf('font: bold on; align: wrap on, vert centre, horiz left; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_right = ezxf('font: bold off; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_left = ezxf('font: bold off; align: wrap on, vert centre, horiz left; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_left = ezxf('font: bold on; align: wrap on, vert centre, horiz left; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_right = ezxf('font: bold on; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')

        
        
        if self.target_move =='posted':
            state = ['posted']
        else:
            state = ['posted','draft']
        
        
        profit = profit_obj.search([('company_id','=',self.company_id.id)])
        
        last_number = 1
        for line in profit:
            sum_prev_balance = sum_balance = 0.0
            if int(line.seq_type)==1:
                pre_account_id = account_obj.search([('income_id','=',line.id)])
                account_id = account_obj.search([('income_id','=',line.id)])
                
                pre_account_ids = self.action_account_ids(pre_account_id.id)
                account_ids = self.action_account_ids(account_id.id)


                if len(pre_account_ids) == 1:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('account_id','=',pre_account_ids[0]),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        pre_move_line_ids = move_line_obj.search([('account_id','=',pre_account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                else:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('account_id','in',tuple(pre_account_ids)),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        pre_move_line_ids = move_line_obj.search([('account_id','in',tuple(pre_account_ids)),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                    
                if len(account_ids)==1:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('account_id','=',account_ids[0]),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        move_line_ids = move_line_obj.search([('account_id','=',account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                else:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('account_id','in',tuple(account_ids)),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        move_line_ids = move_line_obj.search([('account_id','in',tuple(account_ids)),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                        
                
                sheet.write(rowx, 0, '%s'%last_number, data_style)
                sheet.write(rowx, 1, line.name, styles['text_xf'])
                
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
                    
                sheet.write(rowx, 2, sum_prev_balance, data_right)
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
                sheet.write(rowx, 3, sum_balance, data_right)
                rowx +=1
                last_number +=1
        sum_prev_balance *= -1
        sum_balance *= -1
        # НИЙТ АШИГ (АЛДАГДАЛ)
        
        sheet.write(rowx, 0, '%s'%last_number, data_style)
        sheet.write(rowx, 1, u'Нийт ашиг (алдагдал)',data_bold)
        sheet.write(rowx, 2, Formula('SUM(C8-C9)'), data_bold_right)
        sheet.write(rowx, 3, Formula('SUM(D8-D9)'), data_bold_right)
        rowx +=1
        last_number +=1
        for line in profit:
            income_balance = 0
            pre_income_balance = 0
            expense_balance = 0
            pre_expense_balance = 0
            if int(line.seq_type)==2:
                sheet.write(rowx, 0, '%s'%last_number, data_style)
                sheet.write(rowx, 1, line.name, styles['text_xf'])
                
                pre_account_id = account_obj.search([('income_id','=',line.id)])
                account_id = account_obj.search([('income_id','=',line.id)])
                
                pre_account_ids = self.action_account_ids(pre_account_id.id)
                account_ids = self.action_account_ids(account_id.id)

                    
                if len(pre_account_ids) == 1:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('account_id','=',pre_account_ids[0]),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        pre_move_line_ids = move_line_obj.search([('account_id','=',pre_account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                else:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('account_id','in',tuple(pre_account_ids)),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        pre_move_line_ids = move_line_obj.search([('account_id','in',tuple(pre_account_ids)),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                    
                if len(account_ids)==1:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('account_id','=',account_ids[0]),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        move_line_ids = move_line_obj.search([('account_id','=',account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                else:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('account_id','in',tuple(account_ids)),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        move_line_ids = move_line_obj.search([('account_id','in',tuple(account_ids)),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                
                for pre_account in pre_move_line_ids:
                    if pre_account.debit < 0.0 and pre_account.credit == 0.0:
                        pre_income_balance -=(pre_account.debit*(-1))
                    elif pre_account.credit == 0.0 and pre_account.debit > 0.0:
                        pre_income_balance -=pre_account.debit
                    elif pre_account.credit < 0.0 and pre_account.debit == 0.0:
                        pre_income_balance +=pre_account.credit*(-1)
                    
                    elif pre_account.credit > 0.0 and pre_account.debit == 0.0:
                        pre_income_balance +=pre_account.credit
                        
                
                
                sheet.write(rowx, 2, pre_income_balance, data_right)
                for ml in move_line_ids:
                    if ml.debit < 0.0 and ml.credit == 0.0:
                        income_balance -=(ml.debit*(-1))
                    elif ml.credit == 0.0 and ml.debit > 0.0:
                        income_balance -=ml.debit
                    elif ml.credit < 0.0 and ml.debit == 0.0:
                        income_balance +=ml.credit*(-1)
                    elif ml.credit > 0.0 and ml.debit == 0.0:
                        income_balance +=ml.credit
                        
                sheet.write(rowx, 3, income_balance, data_right)

                last_number +=1
                rowx +=1
            if int(line.seq_type) == 3:
                sheet.write(rowx, 0, '%s'%last_number, data_style)
                sheet.write(rowx, 1, line.name, styles['text_xf'])
                pre_account_id = account_obj.search([('income_id','=',line.id)])
                account_id = account_obj.search([('income_id','=',line.id)])
                
                pre_account_ids = self.action_account_ids(pre_account_id.id)
                account_ids = self.action_account_ids(account_id.id)
                        
                    
                if len(pre_account_ids) == 1:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('account_id','=',pre_account_ids[0]),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        pre_move_line_ids = move_line_obj.search([('account_id','=',pre_account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                else:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('account_id','in',tuple(pre_account_ids)),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        pre_move_line_ids = move_line_obj.search([('account_id','in',tuple(pre_account_ids)),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                    
                if len(account_ids)==1:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('account_id','=',account_ids[0]),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        move_line_ids = move_line_obj.search([('account_id','=',account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                else:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('account_id','in',tuple(account_ids)),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        move_line_ids = move_line_obj.search([('account_id','in',tuple(account_ids)),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                
                
                for pre_account in pre_move_line_ids:
                    if pre_account.debit < 0.0 and pre_account.credit == 0.0:
                        pre_expense_balance +=(pre_account.debit*(-1))
                    elif pre_account.credit == 0.0 and pre_account.debit > 0.0:
                        pre_expense_balance +=pre_account.debit
                    elif pre_account.credit < 0.0 and pre_account.debit == 0.0:
                        pre_expense_balance -=pre_account.credit*(-1)
                    
                    elif pre_account.credit > 0.0 and pre_account.debit == 0.0:
                        pre_expense_balance -=pre_account.credit
                        
                
                sheet.write(rowx, 2, pre_expense_balance, data_right)
                for ml in move_line_ids:
                    if ml.debit < 0.0 and ml.credit == 0.0:
                        expense_balance +=(ml.debit*(-1))
                    elif ml.credit == 0.0 and ml.debit > 0.0:
                        expense_balance +=ml.debit
                    elif ml.credit < 0.0 and ml.debit == 0.0:
                        expense_balance -=ml.credit*(-1)
                    elif ml.credit > 0.0 and ml.debit == 0.0:
                        expense_balance -=ml.credit
                sheet.write(rowx, 3, expense_balance, data_right)
                last_number +=1
                rowx +=1
                
        # ҮНДСЭН ҮЙЛ АЖИЛЛАГААНЫ АШИГ
        sheet.write(rowx, 0, '%s'%last_number, data_style)
        sheet.write(rowx, 1, u'Татвар төлөхийн өмнөх ашиг (алдагдал)',data_bold)
        sheet.write(rowx, 2, Formula('SUM(C10+C11+C12+C13+C14+C15-C16-C17-C18-C19+C20+C21+C22+C23+C24)'), data_bold_right)
        sheet.write(rowx, 3, Formula('SUM(D10+D11+D12+D13+D14+D15-D16-D17-D18-D19+D20+D21+D22+D23+D24)'), data_bold_right)
        rowx +=1
        last_number +=1
        for line in profit:
            expense_balance = 0
            pre_expense_balance = 0
            if int(line.seq_type)==4:
                sheet.write(rowx, 0, '%s'%last_number, data_style)
                sheet.write(rowx, 1, line.name, styles['text_xf'])
                pre_account_id = account_obj.search([('income_id','=',line.id)])
                account_id = account_obj.search([('income_id','=',line.id)])
                
                pre_account_ids = self.action_account_ids(pre_account_id.id)
                account_ids = self.action_account_ids(account_id.id)

                    
                if len(pre_account_ids) == 1:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('account_id','=',pre_account_ids[0]),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        pre_move_line_ids = move_line_obj.search([('account_id','=',pre_account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                else:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('account_id','in',tuple(pre_account_ids)),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        pre_move_line_ids = move_line_obj.search([('account_id','in',tuple(pre_account_ids)),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                    
                if len(account_ids)==1:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('account_id','=',account_ids[0]),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        move_line_ids = move_line_obj.search([('account_id','=',account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                else:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('account_id','in',tuple(account_ids)),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        move_line_ids = move_line_obj.search([('account_id','in',tuple(account_ids)),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
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
               
                sheet.write(rowx, 2,sum_prev_balance, data_right)
                #for account in account_id:
                #    print("loggg",account.balance)
                #    if account.balance < 0.0:
                #        expense_balance +=(account.balance*(-1))
                #    else:
                #        expense_balance +=account.balance
                sheet.write(rowx, 3, sum_balance, data_right)
                rowx +=1
                last_number +=1
        # ТАТВАР ТӨЛӨХИЙН ӨМНӨХ АШИГ
        sheet.write(rowx, 0, '%s'%last_number,data_style)
        sheet.write(rowx, 1, u'Татварын дараахь ашиг (алдагдал)',data_bold)
        sheet.write(rowx, 2, Formula('SUM(C25-C26)'), data_bold_right)
        sheet.write(rowx, 3, Formula('SUM(D25-D26)'), data_bold_right)
        rowx +=1
        # Татварын онцгой дансыг олж тодорхойлох
        #tmp, tax_account_type_id = self.env['ir.model.data'].get_object_reference('l10n_mn_account','account_financial_report_income2')
        #account_ids = account_obj.search([('user_type','=',tax_account_type_id.id)])

        last_number +=1
        # ТАТВАРЫН ДАРААХ АШИГ
        sheet.write(rowx, 0, '%s'%last_number, data_style)
        sheet.write(rowx, 1, u'Зогсоосон үйл ажиллагааны татварын дараахь ашиг (алдагдал)',data_bold)
        sheet.write(rowx, 2, 0, data_bold_right)
        sheet.write(rowx, 3, 0, data_bold_right)
        rowx +=1
        last_number +=1
        #tmp, divid_account_type_id = self.env['ir.model.data'].get_object_reference( 'l10n_mn_account','account_financial_report_income2')
        #account_ids = account_obj.search([('user_type','=',divid_account_type_id)])


        # ЕРДИЙН АЖИЛЛАГААНЫ АШИГ (АЛДАГДАЛ)
        sheet.write(rowx, 0, '%s'%last_number,data_style)
        sheet.write(rowx, 1, u'Тайлант үеийн цэвэр ашиг (алдагдал)',data_bold)
        sheet.write(rowx, 2, Formula('SUM(C27-C28)'), data_bold_right)
        sheet.write(rowx, 3, Formula('SUM(D27-D28)'), data_bold_right)
        rowx +=1
        last_number +=1
        #tmp, charact_account_type_id = self.env['ir.model.data'].get_object_reference( 'l10n_mn_account', 'account_financial_report_income2')
        #account_ids = account_obj.search([('user_type','=',charact_account_type_id)])


        # ЦЭВЭР АШИГ
        sheet.write(rowx, 0, '%s'%last_number,data_style)
        sheet.write(rowx, 1,  u'Бусад дэлгэрэнгүй орлого', data_bold)
        sheet.write(rowx, 2, Formula('SUM(C31+C32)'), data_bold_right)
        sheet.write(rowx, 3, Formula('SUM(D31+D32)'), data_bold_right)   
        rowx +=1
        last_number +1
        for line in profit:
            other_income_balance = 0
            pre_other_income_balance = 0
            if int(line.seq_type)==5:
                sheet.write(rowx, 0, '%s'%line.sequence, data_style)
                sheet.write(rowx, 1, line.name, styles['text_xf'])
                pre_account_id = account_obj.search([('income_id','=',line.id)])
                account_id = account_obj.search([('income_id','=',line.id)])
                
                pre_account_ids = self.action_account_ids(pre_account_id.id)
                account_ids = self.action_account_ids(account_id.id)
                    
                if len(pre_account_ids) == 1:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('account_id','=',pre_account_ids[0]),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        pre_move_line_ids = move_line_obj.search([('account_id','=',pre_account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                else:
                    if len(state)==1:
                        pre_move_line_ids = move_line_obj.search([('account_id','in',tuple(pre_account_ids)),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        pre_move_line_ids = move_line_obj.search([('account_id','in',tuple(pre_account_ids)),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                    
                if len(account_ids)==1:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('account_id','=',account_ids[0]),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        move_line_ids = move_line_obj.search([('account_id','=',account_ids[0]),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                else:
                    if len(state)==1:
                        move_line_ids = move_line_obj.search([('account_id','in',tuple(account_ids)),('move_id.state','=',state[0]),('date','>=',self.date_from),('date','<=',self.date_to)])
                    else:
                        move_line_ids = move_line_obj.search([('account_id','in',tuple(account_ids)),('move_id.state','in',tuple(state)),('date','>=',self.date_from),('date','<=',self.date_to)])
                
                for pre_account in pre_move_line_ids:
                    if pre_account.debit < 0.0 and pre_account.credit == 0.0:
                        pre_other_income_balance +=(pre_account.debit*(-1))
                    elif pre_account.credit == 0.0 and pre_account.debit > 0.0:
                        pre_other_income_balance +=pre_account.debit
                    elif pre_account.credit < 0.0 and pre_account.debit == 0.0:
                        pre_other_income_balance -=pre_account.credit*(-1)
                    
                    elif pre_account.credit > 0.0 and pre_account.debit == 0.0:
                        pre_other_income_balance -=pre_account.credit
                        
                        
                
                sheet.write(rowx, 2, pre_other_income_balance, data_right)
                for ml in move_line_ids:
                    if ml.debit < 0.0 and ml.credit == 0.0:
                        other_income_balance +=(ml.debit*(-1))
                    elif ml.credit == 0.0 and ml.debit > 0.0:
                        other_income_balance +=ml.debit
                    elif ml.credit < 0.0 and ml.debit == 0.0:
                        other_income_balance -=ml.credit*(-1)
                    elif ml.credit > 0.0 and ml.debit == 0.0:
                        other_income_balance -=ml.credit
                sheet.write(rowx, 3, other_income_balance, data_right)
                rowx +=1
        last_number +=1
        # ЦЭВЭР АШИГ
        sheet.write(rowx, 0, '%s'%last_number,data_style)
        sheet.write(rowx, 1,  u'Орлогын нийт дүн', data_bold)
        sheet.write(rowx, 2, Formula('SUM(C29+C30)'), data_bold_right)
        sheet.write(rowx, 3, Formula('SUM(D29+D30)'), data_bold_right)
        rowx +=1
        last_number +=1
        # ЦЭВЭР АШИГ
        sheet.write(rowx, 0, '%s'%last_number,data_style)
        sheet.write(rowx, 1,  u'Нэгж хувьцаанд ноогдох суурь ашиг (алдагдал)', data_bold)
        sheet.write(rowx, 2, Formula('SUM(C33)'), data_bold_right)
        sheet.write(rowx, 3, Formula('SUM(D33)'), data_bold_right)
        
        inch = 1000
        sheet.col(0).width = 2 * inch
        sheet.col(1).width = 16 * inch
        sheet.col(2).width = 4 * inch
        sheet.col(3).width = 4 * inch
        sheet.col(4).width = 3 * inch
        sheet.col(5).width = 3 * inch
        sheet.col(6).width = 3 * inch
        sheet.col(7).width = 3 * inch
        sheet.col(8).width = 3 * inch
        sheet.col(9).width = 3 * inch
        sheet.row(6).height = 640
        
        sheet.write(rowx + 3, 1, u'Гүйцэтгэх захирал....................................../\
                                                 /', ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 180'))
        sheet.write(rowx + 5, 1, u'Ерөнхий нягтлан бодогч....................................../\
                                                 /', ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 180'))
        
        return {'data':book, 'directory_name':u'Орлого үр дүнгийн тайлан',
                'attache_name':'Орлого үр дүнгийн тайлан'}
    