# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

class CashMovelineReport(models.TransientModel):
    """
        Бэлэн мөнгө болон харилцахын гүйлгээний тайлан
    """
    _name = "cash.move.line.report"
    _description = "Account move line report"
    
    
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    date_from = fields.Date(string="Start date", required=True)
    date_to = fields.Date(string="End date", required=True)
    account_ids = fields.Many2many('account.account', 'account_move_report_rel', 'account_id','report_id', 
                                   string='Account', required=True)


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.date_from,
            'end_date': self.date_to,
            'account_ids': self.account_ids.ids
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'cash.move.line.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'cash_and_bank_report'}
        }

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
                                    'align': 'right', 
                                    'font_size': 12
                                    })
        head_title = workbook.add_format({
                                    'align': 'center', 
                                    'font_size': 16,
                                    'bold': True
                                    })
        txt_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'bold': True
                                })
        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00'
                                    })

        sheet.set_column(3, 8, 20)
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 2, 15)
        sheet.merge_range('A1:B1', u'НХМаягт МХ-4', head)
        sheet.merge_range('G1:H1', u'Сангийн сайдын 2018 оны 100 дугаар', head)
        sheet.merge_range('B2:H2', u'тушаалын хавсралт', head)
        sheet.merge_range('A3:H3', u'Бэлэн мөнгөний гүйлгээний тайлан', head_title)
        sheet.merge_range('A4:B4', u'Байгууллагын нэр: %s' % data['company_name'], head)
        sheet.write('H4', u'Он сар өдөр: %s - %s' % (data['start_date'],data['end_date']), head)

        rowx = 5
        
        
        sheet.merge_range('A%s:A%s'%(rowx, rowx+1), u'Д/д', txt_center)
        sheet.merge_range('B%s:C%s'%(rowx, rowx), u'Баримтын', txt_center)
        sheet.write('B%s'%(rowx+1), u'Дугаар', txt_center)
        sheet.write('C%s'%(rowx+1), u'Он сар өдөр', txt_center)
        sheet.merge_range('D%s:D%s'%(rowx, rowx+1), u'Гүйлгээний утга', txt_center)
        sheet.merge_range('E%s:E%s'%(rowx, rowx+1), u'Харилцагч', txt_center)
        sheet.merge_range('F%s:F%s'%(rowx, rowx+1), u'Орлого', txt_center)
        sheet.merge_range('G%s:G%s'%(rowx, rowx+1), u'Зарлага', txt_center)
        sheet.merge_range('H%s:H%s'%(rowx, rowx+1), u'Үлдэгдлийн дүн', txt_center)

        rowx += 2
        account_obj = self.env['account.account']
        if len(data['account_ids']) == 1:
            account_id = account_obj.search([('id','=',data['account_ids'][0]),('company_id','=',data['company_id'])])
            self.env.cr.execute("select am.date, aml.name, aml.ref, sp.name, aa.code, aa.name, acmt.name, \
            aml.debit, aml.credit, am.name,am.partner_id from account_move_line AS aml \
            left join account_move AS am ON am.id = aml.move_id \
            left join res_partner AS sp on sp.id = aml.partner_id \
            left join account_account AS aa on aa.id = aml.account_id \
            left join account_cash_move_type AS acmt on acmt.id = aml.cash_move_type_id \
            WHERE am.date >= '%s' and am.date <='%s' and aml.account_id = %s and am.state='posted' \
            order by aml.date asc"%(data['start_date'],data['end_date'],data['account_ids'][0]))
            all = self._cr.fetchall()
            
        else:
            account_id = account_obj.search([('id','in',tuple(data['account_ids'])),('company_id','=',data['company_id'])])
            self.env.cr.execute("select am.date, aml.name, aml.ref, sp.name, aa.code, aa.name, acmt.name, \
            aml.debit, aml.credit, am.name,am.partner_id from account_move_line AS aml \
            left join account_move AS am ON am.id = aml.move_id \
            left join res_partner AS sp on sp.id = aml.partner_id \
            left join account_account AS aa on aa.id = aml.account_id \
            left join account_cash_move_type AS acmt on acmt.id = aml.cash_move_type \
            WHERE am.date >= '%s' and am.date <='%s' and aml.account_id in %s and am.state='posted' \
            order by aml.date asc"%(data['start_date'],data['end_date'],tuple(data['account_ids'])))
            all = self._cr.fetchall()
        start_balance = 0.0
        total = 0.0
        number = 1
        partner_obj = self.env['res.partner']
        for line in account_id:
            balance = 0.0
            self.env.cr.execute("select sum(debit-credit) as balance from account_move_line where date >= '%s' and date < '%s' and account_id = %s"%(data['start_date'],data['start_date'],line.id))
            acc = self._cr.dictfetchall()
            if acc[0]['balance'] !=None:
                balance = acc[0]['balance']
            sheet.merge_range('A%s:B%s'%(rowx, rowx), u'Дансны №', txt_center)
            sheet.merge_range('C%s:D%s'%(rowx, rowx), u'%s %s'%(line.code,line.name), txt_center)
            sheet.merge_range('E%s:G%s'%(rowx, rowx), u'Эхний үлдэгдэл', txt_center)
            sheet.merge_range('H%s:H%s'%(rowx, rowx), balance, txt_center)
            rowx +=1
            for i in all:
                if line.code==i[4]:
                    if i[10]:
                        partner = partner_obj.browse(i[10])
                        sheet.write('E%s'%rowx, partner.name, data_right)
                    else:
                        sheet.write('E%s'%rowx, '', data_right)
                    sheet.write('A%s'%rowx, number, data_right)
                    sheet.write('B%s'%rowx, i[9], data_right)
                    sheet.write('C%s'%rowx, '%s'%i[0], data_right)
                    sheet.write('D%s'%rowx, i[1], data_right)
                    sheet.write('F%s'%rowx, i[7], data_right)
                    sheet.write('G%s'%rowx, i[8], data_right)
                    if i[7] >0.0:
                        if balance !=None:
                            balance +=float(i[7])
                    elif i[8] > 0.0:
                        if balance !=None:
                            balance -=float(i[8])
                    sheet.write('H%s'%rowx, balance, data_right)
                    number += 1
                    rowx += 1
        
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


        
