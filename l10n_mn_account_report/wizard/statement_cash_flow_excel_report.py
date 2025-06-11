# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class statement_cashflow_report(models.TransientModel):
    """
        МӨНГӨН ГҮЙЛГЭЭНИЙ ТАЙЛАН
    """
    _name = "statement.cashflow.report"
    _description = "Statement of cash flows"
    
    company_id= fields.Many2one('res.company', string='Company', required=True,
                                default=lambda self: self.env.user.company_id)
    date_from=fields.Date("Start Date", required=True,default=fields.Date.context_today)
    date_to=fields.Date("End Date", required=True,default=fields.Date.context_today)
    fiscalyear_id = fields.Many2one('account.fiscal.year', string='Fiscal year',required=True)
    target_move=fields.Selection([('posted', 'All Posted Entries'),
                                     ('all', 'All Entries'),
                                    ], string='State', required=True,default='posted')
        
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
                     'report_name': 'Cash and bank report'}
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
    
    def get_export_data(self):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''
        
        
        
        date_str = '%s-%s' % (
            datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime('%Y.%m.%d'),
            datetime.strptime(str(self.date_to), '%Y-%m-%d').strftime('%Y.%m.%d')
        )
        ezxf = xlwt.easyxf
        styles = self.get_easyxf_styles()
        data_style = ezxf('font: bold off; align: wrap on, vert centre, horiz centre; font: height 240;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold = ezxf('font: bold on; align: wrap on, vert centre, horiz centre; font: height 240;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_right = ezxf('font: bold off; align: wrap on, vert centre, horiz right; font: height 240;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_left = ezxf('font: bold off; align: wrap on, vert centre, horiz left; font: height 240;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_left = ezxf('font: bold on; align: wrap on, vert centre, horiz left; font: height 240;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_right = ezxf('font: bold on; align: wrap on, vert centre, horiz right; font: height 240;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')

        
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet(u'Мөнгөн гүйлгээний тайлан')
        
        sheet.write(0, 2, u'Маягт CT-4-1', ezxf('font:bold on;align:wrap off,vert centre,horiz right; font: height 180'))
        
        sheet.write_merge(1, 1, 0, 3, u'МӨНГӨН ГҮЙЛГЭЭНИЙ ТАЙЛАН', ezxf('font: bold on; align: wrap off, vert centre, horiz centre;font: height 250'))
        sheet.row(2).height = 400
        
        
        sheet.write(2, 1, u'"%s" ХХК'%self.company_id.name, ezxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 240'))

        sheet.write(3, 1, u'(Аж ахуй нэгж, байгууллагын нэр)', ezxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 240'))

        sheet.write(4, 2, u'%s' % (self.date_to,), ezxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 240'))
        
        rowx = 6
        sheet.write(rowx, 0, u'Мөрийн дугаар', data_bold_left)
        sheet.write(rowx, 1, u'Үзүүлэлт', data_bold_left)
        sheet.write(rowx, 2, u'%s'%self.date_from, data_bold_right)
        sheet.write(rowx, 3, u'%s'%self.date_to, data_bold_right)
        rowx += 1
        
        account_obj = self.env['account.account']
        account_move_line_obj = self.env['account.move.line']
        cash_move_obj = self.env['account.cash.move.type']
        cash_ids = cash_move_obj.search([('company_id','=',self.company_id.id)])
        
        m_pre_amount = 0.0
        m_now_amount = 0.0
        sheet.write(rowx, 0, u'1',data_bold_left)
        sheet.write(rowx, 1, u'Үндсэн үйл ажиллагааны мөнгөн гүйлгээ',data_bold_left)
        sheet.write(rowx, 2, m_pre_amount, data_bold_right)
        sheet.write(rowx, 3, m_now_amount,data_bold_right)
        rowx += 1
        sheet.write(rowx, 0, u'1.1',data_bold_left)
        sheet.write(rowx, 1, u'Мөнгөн орлогын дүн',data_bold_left)
        if self.target_move =='posted':
            state = ['posted']
        else:
            state = ['posted','draft']
        rowx += 1
        counts = 1
        in_pre_amount = 0.0
        in_now_amount = 0.0
        for type_line in cash_ids:
            if type_line.group == 'activities_income':
                counts +=1
                pre_amount = 0.0
                now_amount = 0.0
                if len(state)==1:
                    move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_line.id),('date','>=',self.date_from),('date','<=',self.date_from),('parent_state','=',state)])
                else:
                    move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_line.id),('date','>=',self.date_from),('date','<=',self.date_from),('parent_state','in',state)])
                if move_line_ids !=[]:
                    for lines in move_line_ids:
                        if lines.debit >0.0:
                            pre_amount +=lines.debit
                        else:
                            pre_amount -=lines.credit
                if len(state)==1:
                    now_move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_line.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                else:
                    now_move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_line.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                if now_move_line_ids !=[]:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit >0.0:
                            now_amount +=now_lines.debit
                        else:
                            now_amount -=now_lines.credit
                sheet.write(rowx, 0, u'%s'%type_line.sequence,data_left)
                sheet.write(rowx, 1, u'%s'%type_line.name,data_left)
                sheet.write(rowx, 2, pre_amount, data_right)
                sheet.write(rowx, 3, now_amount,data_right)
                in_pre_amount += pre_amount
                in_now_amount += now_amount 
                rowx +=1
                
        sheet.write(rowx-counts, 2, in_pre_amount, data_bold_right)
        sheet.write(rowx-counts, 3, in_now_amount,data_bold_right)
        
        sheet.write(rowx, 0, u'1.2',data_left)
        sheet.write(rowx, 1, u'Мөнгөн зарлагын дүн',data_bold_left)
        rowx += 1
        counts = 1
        exp_pre_amount = 0.0
        exp_now_amount = 0.0
        for type_line_exp in cash_ids:
            if type_line_exp.group == 'activities_expense':
                counts += 1
                pre_amount = 0.0
                now_amount = 0.0
                if len(state)==1:
                    move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_line_exp.id),('date','>=',self.date_from),('date','<=',self.date_from),('parent_state','=',state)])
                else:
                    move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_line_exp.id),('date','>=',self.date_from),('date','<=',self.date_from),('parent_state','in',state)])
                if move_line_ids !=[]:
                    for lines in move_line_ids:
                        if lines.debit >0.0:
                            pre_amount +=lines.debit
                        else:
                            pre_amount -=lines.credit
                if len(state)==1:       
                    now_move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_line_exp.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                else:
                    now_move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_line_exp.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                if now_move_line_ids !=[]:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit >0.0:
                            now_amount +=now_lines.debit
                        else:
                            now_amount -=now_lines.credit
                sheet.write(rowx, 0, u'%s'%type_line_exp.sequence,data_left)
                sheet.write(rowx, 1, u'%s'%type_line_exp.name,data_left)
                sheet.write(rowx, 2, pre_amount, data_right)
                if now_amount < 0.0:
                    now_amount = now_amount*(-1)
                sheet.write(rowx, 3, now_amount,data_right)
                exp_pre_amount +=pre_amount
                exp_now_amount +=now_amount
                rowx +=1
               
            
        sheet.write(rowx-counts, 2, exp_pre_amount, data_bold_right)
        sheet.write(rowx-counts, 3, exp_now_amount,data_bold_right)
        
        sheet.write(rowx, 0, u'1.3',data_bold_left)
        sheet.write(rowx, 1, u'Үндсэн үйл ажиллагааны цэвэр мөнгөн гүйлгээний дүн',data_bold_left)
        sheet.write(rowx, 2, in_pre_amount-exp_pre_amount, data_bold_right)
        sheet.write(rowx, 3, in_now_amount-exp_now_amount,data_bold_right)
        rowx += 1
        
        sheet.write(rowx, 0, u'2',data_bold_left)
        sheet.write(rowx, 1, u'Хөрөнгө оруулалтын үйл ажиллагааны мөнгөн гүйлгээ',data_bold_left)
        sheet.write(rowx, 2, 0.0, data_bold_right)
        sheet.write(rowx, 3, 0.0, data_bold_right)
        rowx += 1
        
        sheet.write(rowx, 0, u'2.1',data_bold_left)
        sheet.write(rowx, 1, u'Хөрөнгө оруулалтын үйл ажиллагааны мөнгөн орлогын дүн',data_bold_left)
        inv_pre_amount = 0.0
        inv_now_amount = 0.0
        rowx += 1
        counts = 1
        for type_line_exp in cash_ids:
            if type_line_exp.group == 'investing_income':
                counts += 1
                pre_amount = 0.0
                now_amount = 0.0
                if len(state)==1:
                    move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_line_exp.id),('date','>=',self.date_from),('date','<=',self.date_from),('parent_state','=',state)])
                else:
                    move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_line_exp.id),('date','>=',self.date_from),('date','<=',self.date_from),('parent_state','in',state)])
                if move_line_ids !=[]:
                    for lines in move_line_ids:
                        if lines.debit >0.0:
                            pre_amount +=lines.debit
                        else:
                            pre_amount -=lines.credit
                if len(state)==1:    
                    now_move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_line_exp.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                else:
                    now_move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_line_exp.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                if now_move_line_ids !=[]:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit >0.0:
                            now_amount +=now_lines.debit
                        else:
                            now_amount -=now_lines.credit
                sheet.write(rowx, 0, u'%s'%type_line_exp.sequence,data_left)
                sheet.write(rowx, 1, u'%s'%type_line_exp.name,data_left)
                sheet.write(rowx, 2, pre_amount, data_right)
                sheet.write(rowx, 3, now_amount,data_right)
                inv_pre_amount +=pre_amount
                inv_now_amount +=now_amount
                rowx +=1
        sheet.write(rowx-counts, 2, inv_pre_amount, data_bold_right)
        sheet.write(rowx-counts, 3, inv_now_amount,data_bold_right)
        
            
        sheet.write(rowx, 0, u'2.2',data_bold_left)
        sheet.write(rowx, 1, u'Хөрөнгө оруулалтын үйл ажиллагааны мөнгөн зарлагын дүн',data_bold_left)
        inve_pre_amount = 0.0
        inve_now_amount = 0.0
        rowx += 1
        counts = 1
        for type_inv_exp in cash_ids:
            if type_inv_exp.group == 'investing_expense':
                counts += 1
                pre_amount = 0.0
                now_amount = 0.0
                if len(state)==1:
                    
                    move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_inv_exp.id),('date','>=',self.date_from),('date','<=',self.date_from),('parent_state','=',state)])
                else:
                    move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_inv_exp.id),('date','>=',self.date_from),('date','<=',self.date_from),('parent_state','in',state)])
                if move_line_ids !=[]:
                    for lines in move_line_ids:
                        if lines.debit >0.0:
                            pre_amount +=lines.debit
                        else:
                            pre_amount -=lines.credit
                if len(state)==1:
                    now_move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_inv_exp.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                else:
                    now_move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_inv_exp.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                if now_move_line_ids !=[]:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit >0.0:
                            now_amount +=now_lines.debit
                        else:
                            now_amount -=now_lines.credit
                sheet.write(rowx, 0, u'%s'%type_inv_exp.sequence,data_left)
                sheet.write(rowx, 1, u'%s'%type_inv_exp.name,data_left)
                sheet.write(rowx, 2, pre_amount, data_right)
                if now_amount < 0.0:
                    now_amount = now_amount*(-1)
                sheet.write(rowx, 3, now_amount,data_right)
                inve_pre_amount +=pre_amount
                inve_now_amount +=now_amount
                rowx +=1
        sheet.write(rowx-counts, 2, inve_pre_amount, data_bold_right)
        sheet.write(rowx-counts, 3, inve_now_amount,data_bold_right)
        sheet.write(rowx, 0, u'2.3',data_bold_left)
        sheet.write(rowx, 1, u'Хөрөнгө оруулалтын үйл ажиллагааны цэвэр мөнгөн гүйлгээний дүн',data_bold_left)
        sheet.write(rowx, 2, inv_pre_amount - inve_pre_amount, data_bold_right)
        sheet.write(rowx, 3, inv_now_amount - inve_now_amount,data_bold_right)
        rowx +=1
        
        
        sheet.write(rowx, 0, u'3',data_bold_left)
        sheet.write(rowx, 1, u'Санхүүгийн үйл ажиллагааны мөнгөн гүйлгээ',data_bold_left)
        sheet.write(rowx, 2, 0.0, data_bold_right)
        sheet.write(rowx, 3, 0.0,data_bold_right)
        rowx +=1

        sheet.write(rowx, 0, u'3.1',data_bold_left)
        sheet.write(rowx, 1, u'Санхүүгийн үйл ажиллагааны мөнгөн орлогын дүн',data_bold_left)
        fi_pre_amount = 0.0
        fi_now_amount = 0.0
        rowx += 1
        counts = 1
        for type_fi_exp in cash_ids:
            if type_fi_exp.group == 'financing_income':
                counts += 1
                pre_amount = 0.0
                now_amount = 0.0
                if len(state)==1:
                    move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_fi_exp.id),('date','>=',self.date_from),('date','<=',self.date_from),('parent_state','=',state)])
                else:
                    move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_fi_exp.id),('date','>=',self.date_from),('date','<=',self.date_from),('parent_state','in',state)])
                if move_line_ids !=[]:
                    for lines in move_line_ids:
                        if lines.debit >0.0:
                            pre_amount +=lines.debit
                        else:
                            pre_amount -=lines.credit
                if len(state)==1:
                    now_move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_fi_exp.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                else:
                    now_move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_fi_exp.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','in',state)])
                if now_move_line_ids !=[]:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit >0.0:
                            now_amount +=now_lines.debit
                        else:
                            now_amount -=now_lines.credit
                sheet.write(rowx, 0, u'%s'%type_fi_exp.sequence,data_left)
                sheet.write(rowx, 1, u'%s'%type_fi_exp.name,data_left)
                sheet.write(rowx, 2, pre_amount, data_right)
                sheet.write(rowx, 3, now_amount,data_right)
                fi_pre_amount +=pre_amount
                fi_now_amount +=now_amount
                rowx +=1
        sheet.write(rowx-counts, 2, fi_pre_amount, data_bold_right)
        sheet.write(rowx-counts, 3, fi_now_amount,data_bold_right)
        
        sheet.write(rowx, 0, u'3.2',data_bold_left)
        sheet.write(rowx, 1, u'Санхүүгийн үйл ажиллагааны мөнгөн зарлагын дүн',data_bold_left)
        fie_pre_amount = 0.0
        fie_now_amount = 0.0
        rowx += 1
        counts = 1
        for type_fie_exp in cash_ids:
            if type_fie_exp.group == 'financing_expense':
                counts += 1
                pre_amount = 0.0
                now_amount = 0.0
                move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_fie_exp.id),('date','>=',self.date_from),('date','<=',self.date_from),('parent_state','=',state)])
                if move_line_ids !=[]:
                    for lines in move_line_ids:
                        if lines.debit >0.0:
                            pre_amount +=lines.debit
                        else:
                            pre_amount -=lines.credit
                            
                now_move_line_ids = account_move_line_obj.search([('cash_move_type','=',type_fie_exp.id),('date','>=',self.date_from),('date','<=',self.date_to),('parent_state','=',state)])
                if now_move_line_ids !=[]:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit >0.0:
                            now_amount +=now_lines.debit
                        else:
                            now_amount -=now_lines.credit
                sheet.write(rowx, 0, u'%s'%type_fie_exp.sequence,data_left)
                sheet.write(rowx, 1, u'%s'%type_fie_exp.name,data_left)
                sheet.write(rowx, 2, pre_amount, data_right)
                if now_amount < 0.0:
                    now_amount = now_amount*(-1)
                sheet.write(rowx, 3, now_amount,data_right)
                fie_pre_amount +=pre_amount
                fie_now_amount +=now_amount
                rowx +=1
        sheet.write(rowx-counts, 2, fie_pre_amount, data_bold_right)
        sheet.write(rowx-counts, 3, fie_now_amount,data_bold_right)
        sheet.write(rowx, 0, u'3.20',data_bold_left)
        sheet.write(rowx, 1, u'Санхүүгийн үйл ажиллагааны цэвэр мөнгөн гүйлгээний дүн',data_bold_left)
        sheet.write(rowx, 2, fi_pre_amount-fie_pre_amount, data_bold_right)
        sheet.write(rowx, 3, fi_now_amount-fie_now_amount,data_bold_right)
        rowx +=1
        now_balance = (fi_now_amount-fie_now_amount)+(inv_now_amount-inve_now_amount)+(in_now_amount-exp_now_amount) 
        pre_now_balance = (fi_pre_amount-fie_pre_amount)+(inv_pre_amount-inve_pre_amount)+(in_pre_amount-exp_pre_amount)
        sheet.write(rowx, 0, u'4',data_bold_left)
        sheet.write(rowx, 1, u'Бүх цэвэр мөнгөн гүйлгээ',data_bold_left)
        sheet.write(rowx, 2, pre_now_balance, data_bold_right)
        sheet.write(rowx, 3, now_balance,data_bold_right)
        
        rowx +=1
        pre_pre_balance = 0.0
        pre_balance = 0.0
        account_type_obj = self.env['account.account.type']
        account_type_ids = account_type_obj.search([('type','=','liquidity')])
        accounts = []
        for acc_type_line in account_type_ids:
            account_ids = account_obj.search([('user_type_id','=',acc_type_line.id)])
            for acc in account_ids:
                accounts.append(acc.id)
        if len(accounts) == 1:
            nowmove_line_ids = account_move_line_obj.search([('account_id','=',accounts.id),('date','>=',self.fiscalyear_id.date_from),('date','<=',self.date_from),('parent_state','=',state)])
            if nowmove_line_ids !=[]:
                for lines in nowmove_line_ids:
                    if lines.debit >0.0:
                        pre_balance +=lines.debit
                    else:
                        pre_balance -=lines.credit
        else:
            nowmove_line_ids = account_move_line_obj.search([('account_id','in',tuple(accounts)),('date','>=',self.fiscalyear_id.date_from),('date','<=',self.date_from),('parent_state','=',state)])
            if nowmove_line_ids !=[]:
                for lines in nowmove_line_ids:
                    if lines.debit >0.0:
                        pre_balance +=lines.debit
                    else:
                        pre_balance -=lines.credit
                        
        sheet.write(rowx, 0, u'5.1',data_bold_left)
        sheet.write(rowx, 1, u'Мөнгө, түүнтэй адилтгах хөрөнгийн эхний үлдэгдэл',data_bold_left)
        sheet.write(rowx, 2, pre_pre_balance, data_bold_right)
        sheet.write(rowx, 3, pre_balance,data_bold_right)
        
        rowx +=1
        pre_last_balance = pre_now_balance+pre_pre_balance
        last_balance = now_balance+pre_balance
        sheet.write(rowx, 0, u'5.2',data_bold_left)
        sheet.write(rowx, 1, u'Мөнгө, түүнтэй адилтгах хөрөнгийн эцсийн үлдэгдэл',data_bold_left)
        sheet.write(rowx, 2, pre_last_balance, data_bold_right)
        sheet.write(rowx, 3, last_balance,data_bold_right)
        
        
        inch = 1000
        sheet.col(0).width = 3 * inch
        sheet.col(1).width = 20 * inch
        sheet.col(2).width = 5 * inch
        sheet.col(3).width = 5 * inch
        sheet.row(6).height = 700

        return {'data':book, 'directory_name':u"Мөнгөн гүйлгээний тайлан",
                'attache_name':u"Мөнгөн гүйлгээний тайлан"}

