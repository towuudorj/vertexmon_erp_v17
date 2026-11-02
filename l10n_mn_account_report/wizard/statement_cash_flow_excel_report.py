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
    _inherit = ['xls.report.base']
    _description = "Statement of cash flows"
    
    company_id= fields.Many2one('res.company', string='Company', required=True,
                                default=lambda self: self.env.company)
    date_from=fields.Date("Start Date", required=True,default=fields.Date.context_today)
    date_to=fields.Date("End Date", required=True,default=fields.Date.context_today)
    target_move=fields.Selection([('posted', 'All Posted Entries'),
                                     ('all', 'All Entries'),
                                    ], string='State', required=True,default='posted')

    def get_report_data(self):
        data = super(statement_cashflow_report, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.date_from,
            'end_date': self.date_to,
            'target_move': self.target_move,
        })
        return data
        
    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'statement.cashflow.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Cash and bank report'}
        }

    def get_xlsx_report(self, data, response, get_file=False):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        header = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': 16
                                    })
        header_txt = workbook.add_format({
                                    'align': 'center',
                                    'font_size': 12
                                })
        data_bold_left = workbook.add_format({ 
                                    'align': 'left',
                                    'bold': True,
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })
        data_bold_right = workbook.add_format({
                                    'align': 'right',
                                    'bold': True,
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })
        data_left = workbook.add_format({ 
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })
        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00;(#,##0.00)'
                                })
        

        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.set_column(0, 0, 10)
        sheet.set_column(1, 1, 80)
        sheet.set_column(2, 4, 25)


        sheet.write("D1", u'Маягт CT-4-1', header)
        
        sheet.merge_range("A2:D2", u'МӨНГӨН ГҮЙЛГЭЭНИЙ ТАЙЛАН', header)
        
        
        sheet.write('D3', u'"%s" ХХК'%data['company_name'], header)

        sheet.write("D4", u'(Аж ахуй нэгж, байгууллагын нэр)', header_txt)

        sheet.write("D5", u'%s' % (data['start_date']), header_txt)

        rowx = 6
        sheet.write("A%s"%(rowx), u'Мөрийн дугаар', data_bold_left)
        sheet.write("B%s"%(rowx), u'Үзүүлэлт', data_bold_left)
        sheet.write("C%s"%(rowx), u'%s'%data['start_date'], data_bold_right)
        sheet.write("D%s"%(rowx), u'%s'%data['end_date'], data_bold_right)
        rowx += 1
        
        account_obj = self.env['account.account']
        account_move_line_obj = self.env['account.move.line']
        cash_move_obj = self.env['account.cash.move.type']
        cash_ids = cash_move_obj.search([('company_id','=',data['company_id'])])
        # Зөвхөн мөнгөн хөрөнгийн дансны мөрүүдийг тоолно: харьцсан дансны мөрөнд төрөл бөглөгдсөн бол
        # мөнгөний мөртэйгөө харилцан хасагдаж гүйлгээ тайланд орохгүй болдог байсан
        cash_line_domain = [('account_id.account_type', '=', 'asset_cash'), ('company_id', '=', data['company_id'])]
        sheet.write("A%s"%rowx, u'1',data_bold_left)
        sheet.write("B%s"%rowx, u'Үндсэн үйл ажиллагааны мөнгөн гүйлгээ',data_bold_left)
        sheet.write("C%s"%rowx, '', data_bold_right)
        sheet.write("D%s"%rowx, '',data_bold_right)
        rowx += 1

        sheet.write("A%s"%rowx, u'1.1',data_bold_left)
        sheet.write("B%s"%rowx, u'Мөнгөн орлогын дүн',data_bold_left)
        if data['target_move'] == 'posted':
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
                    move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_line.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                else:
                    move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_line.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                if move_line_ids !=[]:
                    for lines in move_line_ids:
                        if lines.debit >0.0:
                            pre_amount +=lines.debit
                        else:
                            pre_amount -=lines.credit
                if len(state)==1:
                    now_move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_line.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                else:
                    now_move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_line.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                if now_move_line_ids !=[]:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit >0.0:
                            now_amount +=now_lines.debit
                        else:
                            now_amount -=now_lines.credit
                sheet.write("A%s"%rowx,  u'%s'%type_line.sequence,data_left)
                sheet.write("B%s"%rowx,  u'%s'%type_line.name,data_left)
                sheet.write("C%s"%rowx,  pre_amount, data_right)
                sheet.write("D%s"%rowx,  now_amount,data_right)
                in_pre_amount += pre_amount
                in_now_amount += now_amount 
                rowx +=1
                
        sheet.write("C%s"%(rowx-counts), in_pre_amount, data_bold_right)
        sheet.write("D%s"%(rowx-counts), in_now_amount,data_bold_right)
        
                
        sheet.write("A%s"%rowx, u'1.2',data_left)
        sheet.write("B%s"%rowx, u'Мөнгөн зарлагын дүн',data_bold_left)
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
                    move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_line_exp.id),('date','<',data['start_date']),('parent_state','=',state)])
                else:
                    move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_line_exp.id),('date','<',data['start_date']),('parent_state','in',state)])
                if move_line_ids !=[]:
                    for lines in move_line_ids:
                        if lines.debit >0.0:
                            pre_amount -=lines.debit
                        else:
                            pre_amount +=lines.credit
                if len(state)==1:       
                    now_move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_line_exp.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                else:
                    now_move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_line_exp.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                if now_move_line_ids !=[]:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit >0.0:
                            now_amount -=now_lines.debit
                        else:
                            now_amount +=now_lines.credit
                sheet.write("A%s"%rowx, u'%s'%type_line_exp.sequence,data_left)
                sheet.write("B%s"%rowx, u'%s'%type_line_exp.name,data_left)
                sheet.write("C%s"%rowx, pre_amount, data_right)
                if now_amount < 0.0:
                    now_amount = now_amount*(-1)
                sheet.write("D%s"%rowx, now_amount,data_right)
                exp_pre_amount +=pre_amount
                exp_now_amount +=now_amount
                rowx +=1

        sheet.write("C%s"%(rowx-counts), exp_pre_amount, data_bold_right)
        sheet.write("D%s"%(rowx-counts), exp_now_amount,data_bold_right)
        
        sheet.write("A%s"%rowx, u'1.3',data_bold_left)
        sheet.write("B%s"%rowx, u'Үндсэн үйл ажиллагааны цэвэр мөнгөн гүйлгээний дүн',data_bold_left)
        sheet.write("C%s"%rowx, in_pre_amount-exp_pre_amount, data_bold_right)
        sheet.write("D%s"%rowx, in_now_amount-exp_now_amount,data_bold_right)
        rowx += 1
        
        sheet.write("A%s"%rowx, u'2',data_bold_left)
        sheet.write("B%s"%rowx, u'Хөрөнгө оруулалтын үйл ажиллагааны мөнгөн гүйлгээ',data_bold_left)
        sheet.write("C%s"%rowx, '', data_bold_right)
        sheet.write("D%s"%rowx, '', data_bold_right)
        rowx += 1


        sheet.write("A%s"%rowx, u'2.1',data_bold_left)
        sheet.write("B%s"%rowx, u'Хөрөнгө оруулалтын үйл ажиллагааны мөнгөн орлогын дүн',data_bold_left)
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
                    move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_line_exp.id),('date','<',data['start_date']),('parent_state','=',state)])
                else:
                    move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_line_exp.id),('date','<',data['start_date']),('parent_state','in',state)])
                if move_line_ids !=[]:
                    for lines in move_line_ids:
                        if lines.debit >0.0:
                            pre_amount -=lines.debit
                        else:
                            pre_amount +=lines.credit
                if len(state)==1:    
                    now_move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_line_exp.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                else:
                    now_move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_line_exp.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                if now_move_line_ids !=[]:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit >0.0:
                            now_amount -=now_lines.debit
                        else:
                            now_amount -=now_lines.credit
                sheet.write("A%s"%rowx, u'%s'%type_line_exp.sequence,data_left)
                sheet.write("B%s"%rowx, u'%s'%type_line_exp.name,data_left)
                if pre_amount < 0.0:
                    pre_amount = pre_amount*(-1)
                sheet.write("C%s"%rowx, pre_amount, data_right)
                if now_amount < 0.0:
                    now_amount = now_amount*(-1)
                sheet.write("D%s"%rowx, now_amount,data_right)
                inv_pre_amount +=pre_amount
                inv_now_amount +=now_amount
                rowx +=1
        sheet.write("C%s"%(rowx-counts), inv_pre_amount, data_bold_right)
        sheet.write("D%s"%(rowx-counts), inv_now_amount,data_bold_right)


        sheet.write("A%s"%rowx, u'2.2',data_bold_left)
        sheet.write("B%s"%rowx, u'Хөрөнгө оруулалтын үйл ажиллагааны мөнгөн зарлагын дүн',data_bold_left)
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
                    
                    move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_inv_exp.id),('date','<',data['start_date']),('parent_state','=',state)])
                else:
                    move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_inv_exp.id),('date','<',data['start_date']),('parent_state','in',state)])
                if move_line_ids !=[]:
                    for lines in move_line_ids:
                        if lines.debit >0.0:
                            pre_amount +=lines.debit
                        else:
                            pre_amount -=lines.credit
                if len(state)==1:
                    now_move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_inv_exp.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                else:
                    now_move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_inv_exp.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                if now_move_line_ids !=[]:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit >0.0:
                            now_amount +=now_lines.debit
                        else:
                            now_amount -=now_lines.credit
                sheet.write("A%s"%rowx, u'%s'%type_inv_exp.sequence,data_left)
                sheet.write("B%s"%rowx, u'%s'%type_inv_exp.name,data_left)
                sheet.write("C%s"%rowx, pre_amount, data_right)
                if now_amount < 0.0:
                    now_amount = now_amount*(-1)
                sheet.write("D%s"%rowx, now_amount,data_right)
                inve_pre_amount +=pre_amount
                inve_now_amount +=now_amount
                rowx +=1

        sheet.write("C%s"%(rowx-counts), inve_pre_amount, data_bold_right)
        sheet.write("D%s"%(rowx-counts), inve_now_amount,data_bold_right)

        sheet.write("A%s"%rowx, u'2.3',data_bold_left)
        sheet.write("B%s"%rowx, u'Хөрөнгө оруулалтын үйл ажиллагааны цэвэр мөнгөн гүйлгээний дүн',data_bold_left)
        sheet.write("C%s"%rowx, inv_pre_amount - inve_pre_amount, data_bold_right)
        sheet.write("D%s"%rowx, inv_now_amount - inve_now_amount,data_bold_right)
        rowx +=1

        sheet.write("A%s"%rowx, u'3',data_bold_left)
        sheet.write("B%s"%rowx, u'Санхүүгийн үйл ажиллагааны мөнгөн гүйлгээ',data_bold_left)
        sheet.write("C%s"%rowx, '', data_bold_right)
        sheet.write("D%s"%rowx, '',data_bold_right)
        rowx +=1

        sheet.write("A%s"%rowx, u'3.1',data_bold_left)
        sheet.write("B%s"%rowx, u'Санхүүгийн үйл ажиллагааны мөнгөн орлогын дүн',data_bold_left)
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
                    move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_fi_exp.id),('date','<',data['start_date']),('parent_state','=',state)])
                else:
                    move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_fi_exp.id),('date','<',data['start_date']),('parent_state','in',state)])
                if move_line_ids !=[]:
                    for lines in move_line_ids:
                        if lines.debit >0.0:
                            pre_amount +=lines.debit
                        else:
                            pre_amount -=lines.credit
                if len(state)==1:
                    now_move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_fi_exp.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                else:
                    now_move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_fi_exp.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','in',state)])
                if now_move_line_ids !=[]:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit >0.0:
                            now_amount +=now_lines.debit
                        else:
                            now_amount -=now_lines.credit
                sheet.write("A%s"%rowx, u'%s'%type_fi_exp.sequence,data_left)
                sheet.write("B%s"%rowx, u'%s'%type_fi_exp.name,data_left)
                if pre_amount < 0.0:
                    pre_amount = pre_amount*(-1)
                sheet.write("C%s"%rowx, pre_amount, data_right)
                if now_amount < 0.0:
                    now_amount = now_amount*(-1)
                sheet.write("D%s"%rowx, now_amount,data_right)
                fi_pre_amount +=pre_amount
                fi_now_amount +=now_amount
                rowx +=1
        sheet.write("C%s"%(rowx-counts), fi_pre_amount, data_bold_right)
        sheet.write("D%s"%(rowx-counts), fi_now_amount,data_bold_right)


        sheet.write("A%s"%rowx, u'3.2',data_bold_left)
        sheet.write("B%s"%rowx, u'Санхүүгийн үйл ажиллагааны мөнгөн зарлагын дүн',data_bold_left)
        fie_pre_amount = 0.0
        fie_now_amount = 0.0
        rowx += 1
        counts = 1
        for type_fie_exp in cash_ids:
            if type_fie_exp.group == 'financing_expense':
                counts += 1
                pre_amount = 0.0
                now_amount = 0.0
                move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_fie_exp.id),('date','<',data['start_date']),('parent_state','=',state)])
                if move_line_ids !=[]:
                    for lines in move_line_ids:
                        if lines.debit >0.0:
                            pre_amount +=lines.debit
                        else:
                            pre_amount -=lines.credit
                            
                now_move_line_ids = account_move_line_obj.search(cash_line_domain + [('cash_move_type_id','=',type_fie_exp.id),('date','>=',data['start_date']),('date','<=',data['end_date']),('parent_state','=',state)])
                if now_move_line_ids !=[]:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit >0.0:
                            now_amount +=now_lines.debit
                        else:
                            now_amount -=now_lines.credit
                sheet.write("A%s"%rowx, u'%s'%type_fie_exp.sequence,data_left)
                sheet.write("B%s"%rowx, u'%s'%type_fie_exp.name,data_left)
                sheet.write("C%s"%rowx, pre_amount, data_right)
                if now_amount < 0.0:
                    now_amount = now_amount*(-1)
                if pre_amount < 0.0:
                    pre_amount = pre_amount*(-1)
                sheet.write("D%s"%rowx, now_amount,data_right)
                fie_pre_amount +=pre_amount
                fie_now_amount +=now_amount
                rowx +=1

        exch_diff_pre_amount = 0
        exch_diff_now_amount = 0

        sheet.write("C%s"%(rowx-counts), fie_pre_amount, data_bold_right)
        sheet.write("D%s"%(rowx-counts), fie_now_amount,data_bold_right)
        
        sheet.write("A%s"%rowx, u'3.20',data_bold_left)
        sheet.write("B%s"%rowx, u'Санхүүгийн үйл ажиллагааны цэвэр мөнгөн гүйлгээний дүн',data_bold_left)
        sheet.write("C%s"%rowx, fi_pre_amount-fie_pre_amount, data_bold_right)
        sheet.write("D%s"%rowx, fi_now_amount-fie_now_amount,data_bold_right)
        rowx +=1

        for type_fie_exp in cash_ids:
            if type_fie_exp.group == 'exchange_rate_difference':
                counts += 1
                pre_amount = 0.0
                now_amount = 0.0
                move_line_ids = account_move_line_obj.search(
                    cash_line_domain + [('cash_move_type_id', '=', type_fie_exp.id),
                     ('date', '<', data['start_date']), ('parent_state', '=', state)])
                if move_line_ids != []:
                    for lines in move_line_ids:
                        if lines.debit > 0.0:
                            pre_amount += lines.debit
                        else:
                            pre_amount -= lines.credit

                now_move_line_ids = account_move_line_obj.search(
                    cash_line_domain + [('cash_move_type_id', '=', type_fie_exp.id), ('date', '>=', data['start_date']),
                     ('date', '<=', data['end_date']), ('parent_state', '=', state)])
                if now_move_line_ids != []:
                    for now_lines in now_move_line_ids:
                        if now_lines.debit > 0.0:
                            now_amount += now_lines.debit
                        else:
                            now_amount -= now_lines.credit
                exch_diff_pre_amount += pre_amount
                exch_diff_now_amount += now_amount

        sheet.write("A%s"%rowx, u'4',data_bold_left)
        sheet.write("B%s"%rowx, u'Валютын ханшийн зөрүү',data_bold_left)
        sheet.write("C%s"%rowx, exch_diff_pre_amount, data_bold_right)
        sheet.write("D%s"%rowx, exch_diff_now_amount,data_bold_right)
        rowx +=1

        now_balance = (fi_now_amount-fie_now_amount)+(inv_now_amount-inve_now_amount)+(in_now_amount-exp_now_amount)+exch_diff_now_amount
        pre_now_balance = (fi_pre_amount-fie_pre_amount)+(inv_pre_amount-inve_pre_amount)+(in_pre_amount-exp_pre_amount)+exch_diff_pre_amount
        sheet.write("A%s"%rowx, u'5',data_bold_left)
        sheet.write("B%s"%rowx, u'Бүх цэвэр мөнгөн гүйлгээ',data_bold_left)
        sheet.write("C%s"%rowx, pre_now_balance, data_bold_right)
        sheet.write("D%s"%rowx, now_balance,data_bold_right)
        
        rowx +=1
        pre_pre_balance = 0.0
        pre_balance = 0.0
        accounts = []

        account_ids = account_obj.search([('account_type','=','asset_cash'), ('company_id', '=', data['company_id'])])

        for acc in account_ids:
                accounts.append(acc.id)
        if len(accounts) == 1:
            nowmove_line_ids = account_move_line_obj.search([('account_id','=',accounts.id),('date','<',data['start_date']),('parent_state','=',state)])
            if nowmove_line_ids !=[]:
                for lines in nowmove_line_ids:
                    if lines.debit >0.0:
                        pre_pre_balance +=lines.debit
                    else:
                        pre_pre_balance -=lines.credit
        else:
            nowmove_line_ids = account_move_line_obj.search([('account_id','in',tuple(accounts)),('date','<',data['start_date']),('parent_state','=',state)])
            if nowmove_line_ids !=[]:
                for lines in nowmove_line_ids:
                    if lines.debit >0.0:
                        pre_pre_balance +=lines.debit
                    else:
                        pre_pre_balance -=lines.credit

        for acc in account_ids:
                accounts.append(acc.id)
        if len(accounts) == 1:
            nowmove_line_ids = account_move_line_obj.search([('account_id','=',accounts.id),('date','<',data['start_date']),('parent_state','=',state)])
            if nowmove_line_ids !=[]:
                for lines in nowmove_line_ids:
                    if lines.debit >0.0:
                        pre_balance +=lines.debit
                    else:
                        pre_balance -=lines.credit
        else:
            nowmove_line_ids = account_move_line_obj.search([('account_id','in',tuple(accounts)),('date','<',data['start_date']),('parent_state','=',state)])
            if nowmove_line_ids !=[]:
                for lines in nowmove_line_ids:
                    if lines.debit >0.0:
                        pre_balance +=lines.debit
                    else:
                        pre_balance -=lines.credit
                        
        sheet.write("A%s"%rowx, u'6',data_bold_left)
        sheet.write("B%s"%rowx, u'Мөнгө, түүнтэй адилтгах хөрөнгийн эхний үлдэгдэл',data_bold_left)
        sheet.write("C%s"%rowx, pre_pre_balance, data_bold_right)
        sheet.write("D%s"%rowx, pre_balance,data_bold_right)
        
        rowx +=1
        pre_last_balance = pre_now_balance+pre_pre_balance
        last_balance = now_balance+pre_balance
        sheet.write("A%s"%rowx, u'7',data_bold_left)
        sheet.write("B%s"%rowx, u'Мөнгө, түүнтэй адилтгах хөрөнгийн эцсийн үлдэгдэл',data_bold_left)
        sheet.write("C%s"%rowx, pre_last_balance, data_bold_right)
        sheet.write("D%s"%rowx, last_balance,data_bold_right)
        
        
        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return
