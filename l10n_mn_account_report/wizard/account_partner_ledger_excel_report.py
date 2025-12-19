# -*- coding: utf-8 -*#
import io
import json
import xlsxwriter
import time
from odoo import fields, models
from odoo.tools import date_utils


class AccountPartnerLedgerExcelReport(models.TransientModel):
    _name = 'account.partner.ledger.excel.report'
    _description = 'account partner ledger excel report'
    

    
    def _get_all_journal(self):
        company_id = self.env['res.company']._company_default_get('account.partner.ledger.excel.employee.report')
        return self.env['account.journal'].search([('company_id','=',company_id.id)])
    

    
    def _get_account_id(self):
        company_id = self.env['res.company']._company_default_get('account.partner.ledger.excel.employee.report')
        account_id = self.env['account.account'].search([('company_id','=',company_id.id),('code','=','12000001')],limit=1)
        return account_id.id
        


    company_id = fields.Many2one('res.company',u'Компани',required=True,default=lambda self: self.env['res.company']._company_default_get('account.partner.ledger.excel.report'))
    fiscalyear_id = fields.Many2one('account.fiscal.year',u'Санхүүгийн жил',required=True)
    is_transaction = fields.Boolean(u'Үлдэгдэлтэй, гүйлгээтэй эсэх')
    account_id = fields.Many2one('account.account',u'Данс')
    target_move = fields.Selection([('posted',u'Батлагдсан гүйлгээ'),
                                    ('all',u'Бүх гүйлгээ')],u'Зорилтот гүйлгээ',required=True,default='posted')
    result_selection = fields.Selection([('customer',u'Авлагын данс'),
                                         ('supplier',u'Өглөгийн данс'),
                                         ('customer_supplier',u'Өглөг авлагийн данс')],u'Харилцагчийн',required=True,default='customer')
    filter = fields.Selection([('filter_date',u'Огноо')],u'Шүүлтүүр',required=True,default='filter_date')
    partner_id = fields.Many2one('res.partner',u'Харилцагч')
    is_extra = fields.Boolean(u'Задаргаатай эсэх')
    start_date = fields.Date(u'Эхлэх огноо',default=lambda *a: time.strftime('%Y-%m-01'))
    end_date = fields.Date(u'Дуусах огноо',default=lambda *a: time.strftime('%Y-%m-%d'))
    account_journal_ids = fields.Many2many('account.journal', 'account_partner_new_ledger_excel_journal_rel', 'account_id', 'journal_id','Journals',default=_get_all_journal) 


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'target_move': self.target_move,
            'result_selection': self.result_selection,
            'fiscalyear_id': self.fiscalyear_id.id,
            'is_transaction': self.is_transaction,
            'account_id': self.account_id.id,
            'partner_id': self.partner_id.id,
            'is_extra': self.is_extra,
            'account_journal_ids': self.account_journal_ids.ids,
            'filter ': 'filter_date'
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'account.partner.ledger.excel.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Account balance report'}
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
        data_center_no_border = workbook.add_format({
                                    'align': 'center', 
                                    'font_size': 12
                                    })
        txt = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12
                                })

        title = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'bold': True,
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
        
        data_center = workbook.add_format({
                                    'align': 'center',
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
        data_right_bold = workbook.add_format({
                                    'align': 'bold',
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
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 30)
        sheet.set_column(3, 14, 20)

        company = self.env['res.company'].browse(data['company_id'])
        fiscal_id = self.env['account.fiscal.year'].browse(data['fiscalyear_id'])
        account_id = False
        journal_obj = self.env['account.journal']
        account_move_line_obj = self.env['account.move.line']
        account_move = self.env['account.move']
        account_obj = self.env['account.account']

        partner_obj = self.env['res.partner']
        if data['result_selection'] == 'customer':
            account_type = ['asset_receivable']
        elif data['result_selection']=='supplier':
            account_type = ['liability_payable']
        else:
            account_type = ['asset_receivable','liability_payable']
        
        f_journal = []
        if str(fiscal_id.date_from) == str(data['start_date']):
            date_start = fiscal_id.date_from
            journal_id = journal_obj.search([('type','=','opening'),('company_id','=',data['company_id'])])
            f_journal.append(journal_id.id)
        elif str(fiscal_id.date_from) < str(data['start_date']):
            date_start = fiscal_id.date_from
            journal_id = journal_obj.search([('company_id', '=', data['company_id'])])
            for jl in  journal_id:
                f_journal.append(jl.id)
        else:
            date_start = data['start_date']
            journal_id = journal_obj.search([('type','=','opening'),('company_id','=',data['company_id'])])
            move_id = account_move.search([('date','=',data['start_date']),('journal_id','=',journal_id.id),('state','=','posted'),('company_id','=',data['company_id'])])
            if move_id !=False:
                journal_id = journal_obj.search([('type','=','opening'),('company_id','=',data['company_id'])])
            else:
                journal_id = journal_obj.search([('company_id','=',data['company_id']),('type','!=','opening')])
            for lins in journal_id:
                f_journal.append(lins.id)
        
        partner_id = []
        partner_ids = []
        move_state = ['draft', 'posted']
        if data['target_move'] == 'posted':
            move_state = ['posted']
        if data['account_id']:
            account_id = [data['account_id']]
        else:
            account_id = account_obj.search( [('account_type','in',account_type)]).ids

        if data['partner_id']:
            if len(account_id)==1:
                self._cr.execute(""" select aml.partner_id, rp.name, aml.account_id, aml.currency_id, rp.code from 
                                account_move as am left join
                                account_move_line as aml on aml.move_id = am.id left join 
                                res_partner as rp on rp.id = aml.partner_id where aml.partner_id is not null and
                                aml.account_id = %s and am.date >='%s' and am.date <='%s' and 
                                am.state = 'posted' and am.company_id = %s and aml.partner_id = %s
                                group by aml.partner_id,rp.name,aml.account_id, aml.currency_id, rp.code order by 
                                rp.name asc"""%(account_id[0],fiscal_id.date_from,data['end_date'], data['company_id'], data['partner_id']))
                partner_ids = self._cr.dictfetchall()
            else:
                self._cr.execute(""" select aml.partner_id, rp.name, aml.account_id, aml.currency_id, rp.code from account_move as am left join
                                    account_move_line as aml on aml.move_id = am.id left join 
                                    res_partner as rp on rp.id = aml.partner_id where aml.partner_id is not null and
                                    aml.account_id in %s and am.date >='%s' and am.date <='%s' and 
                                    am.state = 'posted' and am.company_id = %s and aml.partner_id = %s
                                    group by aml.partner_id,rp.name,aml.account_id, aml.currency_id, rp.code order by 
                                    rp.name asc"""%(tuple(account_id),fiscal_id.date_from,data['end_date'], data['company_id'], data['partner_id']  ))
                partner_ids = self._cr.dictfetchall()
        else:
            if data['is_transaction'] == True:
                if len(account_id)==1:
                    self._cr.execute(""" select aml.partner_id, rp.name, aml.account_id, aml.currency_id, rp.code from 
                                    account_move as am left join
                                    account_move_line as aml on aml.move_id = am.id left join 
                                    res_partner as rp on rp.id = aml.partner_id where aml.partner_id is not null and
                                    aml.account_id = %s and am.date >='%s' and am.date <='%s' and 
                                    am.state = 'posted' and am.company_id = %s
                                    group by aml.partner_id,rp.name,aml.account_id, aml.currency_id, rp.code order by 
                                    rp.name asc"""%(account_id[0],fiscal_id.date_from,data['end_date'], data['company_id']))
                    partner_ids = self._cr.dictfetchall()
                    for li in partner_ids:
                        if li['amount'] != 0.0 and li['amount'] !=None or li['debit'] !=0.0 and li['debit']!=None:
                            if li['partner_id'] not in partner_id:
                                partner_id.append(li['partner_id'])
                else:
                    self._cr.execute(""" select aml.partner_id, rp.name, aml.account_id, aml.currency_id, rp.code from account_move as am left join
                                    account_move_line as aml on aml.move_id = am.id left join 
                                    res_partner as rp on rp.id = aml.partner_id where aml.partner_id is not null and
                                    aml.account_id in %s and am.date >='%s' and am.date <='%s' and 
                                    am.state = 'posted' and am.company_id = %s
                                    group by aml.partner_id,rp.name,aml.account_id, aml.currency_id, rp.code order by rp.name asc"""%(tuple(account_id),fiscal_id.date_from,data['end_date'], data['company_id']))
                    partner_ids = self._cr.dictfetchall()
                    for li in partner_ids:
                        if li['amount'] != 0.0 and li['amount'] !=None or li['debit'] !=0.0 and li['debit']!=None:
                            if li['partner_id'] not in partner_id:
                                partner_id.append(li['partner_id'])
               
            else:
                if len(account_id)==1:
                    self._cr.execute(""" select aml.partner_id, rp.name, aml.account_id, aml.currency_id, rp.code, aa.acc_code,
                            aa.acc_name, ac.currency_name from 
                            account_move as am left join
                            account_move_line as aml on aml.move_id = am.id 
                            left join account_account as aa on aa.id = aml.account_id
                            left join res_partner as rp on rp.id = aml.partner_id 
                            left join res_currency as ac on ac.id = aml.currency_id
                            where aml.partner_id is not null and
                            am.date >='%s' and am.date <='%s' and aml.account_id=%s and 
                                am.state = 'posted' and am.company_id = %s 
                            group by aml.partner_id,rp.name,aml.account_id, aml.currency_id, 
                            aa.acc_code, aa.acc_name, ac.currency_name, rp.code order by rp.name asc"""%
                            (fiscal_id.date_from,data['end_date'],account_id[0], data['company_id']))
                    partner_ids = self._cr.dictfetchall()
                    partner_id = [p['partner_id'] for p in partner_ids]
                else:
                    self._cr.execute(""" select aml.partner_id, rp.name, aml.account_id, aml.currency_id, rp.code  from 
                                account_move as am left join
                                account_move_line as aml on aml.move_id = am.id 
                                left join res_partner as rp on rp.id = aml.partner_id 
                                where aml.partner_id is not null and
                                am.date >= '%s' and am.date <= '%s' and aml.account_id in %s and 
                                am.state = 'posted' and am.company_id = %s 
                                group by aml.partner_id, rp.name, aml.account_id, aml.currency_id, 
                                rp.code order by rp.name asc"""%
                                (fiscal_id.date_from,data['end_date'],tuple(account_id), data['company_id']))
                    partner_ids = self._cr.dictfetchall()
                    partner_id = [p['partner_id'] for p in partner_ids]
        
        sheet.merge_range("A1:C1", u'Байгууллагын нэр: %s' % (data['company_name']), head)

        if data['result_selection'] == 'customer' and data['is_extra'] == False:
            sheet.merge_range("A2:G2", u'Авлагын товчоо тайлан', head)
        elif data['result_selection'] == 'customer' and data['is_extra'] == True:
            sheet.merge_range("A2:G2", u'Авлагын дэлгэрэнгүй тайлан', head)
        elif data['result_selection'] == 'supplier' and data['is_extra'] == False:
            sheet.merge_range("A2:G2", u'Өглөгийн товчоо тайлан', head)
        elif data['result_selection'] == 'supplier' and data['is_extra'] == True:
            sheet.merge_range("A2:G2", u'Өглөгийн дэлгэрэнгүй тайлан', head)
        elif data['result_selection'] == 'customer_supplier' and data['is_extra'] == False:
            sheet.merge_range("A2:G2", u'Өглөг, авлагын товчоо тайлан', head)
        elif data['result_selection'] == 'customer_supplier' and data['is_extra'] == True:
            sheet.merge_range("A2:G2", u'Өглөг, авлагийн дэлгэрэнгүй тайлан', head)

        sheet.merge_range("E3:G3", u'Тайлант хугацаа: %s - %s'%(data['start_date'],data['end_date']) , head)
        
        rowx = 0
        col = 0
        num = 0
        four = 0
        rowx = 4

        if data['result_selection'] == 'customer' and data['is_extra'] == False:
            sheet.merge_range("A%s:A%s"%(rowx, rowx+1), u'№', title)
            sheet.merge_range("B%s:C%s"%(rowx, rowx), u'Харилцагч', title)
            sheet.write("B%s"%(rowx+1), u'Код', title)
            sheet.write("C%s"%(rowx+1), u'Нэр', title)
            sheet.merge_range("D%s:D%s"%(rowx, rowx+1), u'Эхний үлдэгдэл', title)
            sheet.merge_range("E%s:F%s"%(rowx, rowx), u'Гүйлгээ', title)
            sheet.write("E%s"%(rowx+1), u'Дебит', title)
            sheet.write("F%s"%(rowx+1), u'Кредит', title)
            sheet.merge_range("G%s:G%s"%(rowx, rowx+1), u'Эцсийн үлдэгдэл', title)
            rowx +=1
            if len(account_id)==1:
                rowx +=1
                total_pre_amount = 0.0
                total_debit_amount = 0.0
                total_credit_amount = 0.0
                total_balance_amount = 0.0
                for part in partner_ids:
                    total_pre_currency_amount = 0.0
                    total_debit_currency_amount = 0.0
                    total_credit_currency_amount = 0.0
                    total_balance_currency_amount = 0.0
                    total_pre_account_amount = 0.0
                    total_debit_account_amount = 0.0
                    total_credit_account_amount = 0.0
                    total_balance_account_amount = 0.0
                    sheet.write("A%s"%(rowx), u'Данс:', txt)
                    account = account_obj.browse(part['account_id'])
                    sheet.merge_range("B%s:C%s"%(rowx, rowx), u'%s %s'%(account.code, account.name), txt)
                    rowx +=1
                    sheet.write("B%s"%(rowx), u'Валют:', txt)
                    currency = self.env['res.currency'].browse(part['currency_id'])
                    sheet.write("C%s"%(rowx), u'%s'%(currency.name), txt)
                    rowx +=1
                    if len(f_journal)==1:
                        self._cr.execute("""
                            select rp.id as partner_id, rp.name as partner_name, rp.ref as partner_ref,
                            sum(aml.debit - aml.credit) as balance, aml.amount_currency
                            from account_move_line aml
                            left join res_partner rp on aml.partner_id = rp.id
                            where aml.account_id = %s
                            and aml.date >= '%s' and aml.date <= '%s' and rp.id = %s
                            and aml.move_id in (select id from account_move where state = '%s')
                            and aml.journal_id = %s
                            group by rp.id, rp.name, rp.ref, aml.amount_currency
                            order by rp.name
                        """%(part['account_id'], date_start, data['start_date'], part['partner_id'], move_state[0], f_journal[0]))
                        pre_lines = self._cr.dictfetchall()
                    else:
                        self._cr.execute("""
                            select rp.id as partner_id, rp.name as partner_name, rp.ref as partner_ref,
                            sum(aml.debit - aml.credit) as balance, aml.amount_currency
                            from account_move_line aml
                            left join res_partner rp on aml.partner_id = rp.id
                            where aml.account_id = %s
                            and aml.date >= '%s' and aml.date <= '%s' and rp.id = %s
                            and aml.move_id in (select id from account_move where state = '%s')
                            and aml.journal_id in %s
                            group by rp.id, rp.name, rp.ref, aml.amount_currency
                            order by rp.name
                        """%(part['account_id'], date_start, data['start_date'], part['partner_id'], move_state[0], tuple(f_journal)))
                        pre_lines = self._cr.dictfetchall()
                    sheet.write("A%s"%(rowx), num+1, txt)
                    sheet.write("B%s"%(rowx), part['code'], data_left)
                    sheet.write("C%s"%(rowx), part['name'], data_left)
                    balance = 0.0
                    debit = 0.0
                    credit = 0.0
                    if pre_lines != False:
                        for pre_line in pre_lines:
                            balance += pre_line['balance'] or 0.0
                            total_pre_currency_amount += pre_line['amount_currency'] or 0.0
                            total_pre_account_amount += pre_line['balance'] or 0.0
                    # Эхний үлдэгдэл
                    sheet.write("D%s"%(rowx), balance, data_right)

                    self._cr.execute("""
                        select rp.id as partner_id, rp.name as partner_name, rp.ref as partner_ref,
                        sum(aml.debit) as debit, sum(aml.credit) as credit, aml.amount_currency
                        from account_move_line aml
                        left join res_partner rp on aml.partner_id = rp.id
                        where aml.account_id = %s
                        and aml.date >= %s and aml.date <= %s and rp.id = %s
                        and aml.move_id in (select id from account_move where state in %s)
                        group by rp.id, rp.name, rp.ref, aml.amount_currency
                        order by rp.name
                    """, (part['account_id'], data['start_date'], data['end_date'], part['partner_id'], tuple(move_state)))
                    lines = self._cr.dictfetchall()
                    if lines != False:
                        for line in lines:
                            if line['debit'] != 0.0 or line['credit'] != 0.0:
                                debit += line['debit'] or 0.0
                                credit += line['credit'] or 0.0
                                total_debit_currency_amount += line['amount_currency'] or 0.0
                                total_debit_account_amount += line['debit'] or 0.0  
                                total_credit_currency_amount += line['amount_currency'] or 0.0
                                total_credit_account_amount += line['credit'] or 0.0


                    # Гүйлгээний дебит кредит
                    sheet.write("E%s"%rowx, debit or 0.0, data_right)
                    sheet.write("F%s"%rowx, credit or 0.0, data_right)
                    # Эцсийн үлдэгдэл
                    balance = balance + (debit or 0.0) - (credit or 0.0)
                    sheet.write("G%s"%rowx, balance, data_right)
                    total_balance_account_amount += balance
                    
                    rowx +=1
                    sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Валют', data_right_bold)
                    sheet.write("D%s"%(rowx), total_pre_currency_amount, data_right_bold)
                    sheet.write("E%s"%(rowx), total_debit_currency_amount, data_right_bold)
                    sheet.write("F%s"%(rowx), total_credit_currency_amount, data_right_bold)
                    sheet.write("G%s"%(rowx), total_balance_currency_amount, data_right_bold)
                    rowx +=1

                    sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Дансны дүн', data_right_bold)
                    sheet.write("D%s"%(rowx), total_pre_account_amount, data_right_bold)
                    sheet.write("E%s"%(rowx), total_debit_account_amount, data_right_bold)
                    sheet.write("F%s"%(rowx), total_credit_account_amount, data_right_bold)
                    sheet.write("G%s"%(rowx), total_balance_account_amount, data_right_bold)
                    rowx +=1
                    total_pre_amount += total_pre_account_amount
                    total_debit_amount += total_debit_account_amount
                    total_credit_amount += total_credit_account_amount
                    total_balance_amount += total_balance_account_amount
                sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Нийт дүн', data_right_bold)
                sheet.write("D%s"%(rowx), total_pre_amount, data_right_bold)
                sheet.write("E%s"%(rowx), total_debit_amount, data_right_bold)
                sheet.write("F%s"%(rowx), total_credit_amount, data_right_bold)
                sheet.write("G%s"%(rowx), total_balance_amount, data_right_bold)
            else:
                rowx +=1
                total_pre_amount = 0.0
                total_debit_amount = 0.0
                total_credit_amount = 0.0
                total_balance_amount = 0.0
                for part in partner_ids:
                    total_pre_currency_amount = 0.0
                    total_debit_currency_amount = 0.0
                    total_credit_currency_amount = 0.0
                    total_balance_currency_amount = 0.0
                    total_pre_account_amount = 0.0
                    total_debit_account_amount = 0.0
                    total_credit_account_amount = 0.0
                    total_balance_account_amount = 0.0
                    sheet.write("A%s"%(rowx), u'Данс:', txt)
                    account = account_obj.browse(part['account_id'])
                    sheet.merge_range("B%s:C%s"%(rowx, rowx), u'%s %s'%(account.code, account.name), txt)
                    rowx +=1
                    sheet.write("B%s"%(rowx), u'Валют:', txt)
                    currency = self.env['res.currency'].browse(part['currency_id'])
                    sheet.write("C%s"%(rowx), u'%s'%(currency.name), txt)
                    rowx +=1
                    if len(f_journal)==1:
                        self._cr.execute("""
                            select rp.id as partner_id, rp.name as partner_name, rp.ref as partner_ref,
                            sum(aml.debit - aml.credit) as balance, aml.amount_currency
                            from account_move_line aml
                            left join res_partner rp on aml.partner_id = rp.id
                            where aml.account_id = %s
                            and aml.date >= '%s' and aml.date <= '%s' and rp.id = %s
                            and aml.move_id in (select id from account_move where state = '%s')
                            and aml.journal_id = %s
                            group by rp.id, rp.name, rp.ref, aml.amount_currency
                            order by rp.name
                        """%(part['account_id'], date_start, data['start_date'], part['partner_id'], move_state[0], f_journal[0]))
                        pre_lines = self._cr.dictfetchall()
                    else:
                        self._cr.execute("""
                            select rp.id as partner_id, rp.name as partner_name, rp.ref as partner_ref,
                            sum(aml.debit - aml.credit) as balance, aml.amount_currency
                            from account_move_line aml
                            left join res_partner rp on aml.partner_id = rp.id
                            where aml.account_id = %s
                            and aml.date >= '%s' and aml.date <= '%s' and rp.id = %s
                            and aml.move_id in (select id from account_move where state = '%s')
                            and aml.journal_id in %s
                            group by rp.id, rp.name, rp.ref, aml.amount_currency
                            order by rp.name
                        """%(part['account_id'], date_start, data['start_date'], part['partner_id'], move_state[0], tuple(f_journal)))
                        pre_lines = self._cr.dictfetchall()

                    sheet.write("A%s"%(rowx), num+1, txt)
                    sheet.write("B%s"%(rowx), part['code'], data_left)
                    sheet.write("C%s"%(rowx), part['name'], data_left)
                    balance = 0.0
                    debit = 0.0
                    credit = 0.0
                    if pre_lines != False:
                        for pre_line in pre_lines:
                            balance += pre_line['balance'] or 0.0
                            total_pre_currency_amount += pre_line['amount_currency'] or 0.0
                            total_pre_account_amount += pre_line['balance'] or 0.0

                    # Эхний үлдэгдэл
                    sheet.write("D%s"%(rowx), balance, data_right)

                    self._cr.execute("""
                        select rp.id as partner_id, rp.name as partner_name, rp.ref as partner_ref,
                        sum(aml.debit) as debit, sum(aml.credit) as credit, aml.amount_currency
                        from account_move_line aml
                        left join res_partner rp on aml.partner_id = rp.id
                        where aml.account_id = %s
                        and aml.date >= %s and aml.date <= %s and rp.id = %s
                        and aml.move_id in (select id from account_move where state in %s)
                        group by rp.id, rp.name, rp.ref, aml.amount_currency
                        order by rp.name
                    """, (part['account_id'], data['start_date'], data['end_date'], part['partner_id'], tuple(move_state)))
                    lines = self._cr.dictfetchall()
                    if lines != False:
                        for line in lines:
                            if line['debit'] != 0.0 or line['credit'] != 0.0:
                                debit += line['debit'] or 0.0
                                credit += line['credit'] or 0.0
                                total_debit_currency_amount += line['amount_currency'] or 0.0
                                total_debit_account_amount += line['debit'] or 0.0
                                total_credit_currency_amount += line['amount_currency'] or 0.0
                                total_credit_account_amount += line['credit'] or 0.0

                    # Гүйлгээний дебит кредит
                    sheet.write("E%s"%rowx, debit or 0.0, data_right)
                    sheet.write("F%s"%rowx, credit or 0.0, data_right)
                    # Эцсийн үлдэгдэл
                    balance = balance + (debit or 0.0) - (credit or 0.0)
                    sheet.write("G%s"%rowx, balance, data_right)

                    rowx +=1
                    sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Валют', data_right_bold)
                    sheet.write("D%s"%(rowx), total_pre_currency_amount, data_right_bold)
                    sheet.write("E%s"%(rowx), total_debit_currency_amount, data_right_bold)
                    sheet.write("F%s"%(rowx), total_credit_currency_amount, data_right_bold)
                    sheet.write("G%s"%(rowx), total_balance_currency_amount, data_right_bold)
                    rowx +=1

                    sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Дансны дүн', data_right_bold)
                    sheet.write("D%s"%(rowx), total_pre_account_amount, data_right_bold)
                    sheet.write("E%s"%(rowx), total_debit_account_amount, data_right_bold)
                    sheet.write("F%s"%(rowx), total_credit_account_amount, data_right_bold)
                    sheet.write("G%s"%(rowx), total_balance_account_amount, data_right_bold)
                    rowx +=1
                    total_pre_amount += total_pre_account_amount
                    total_debit_amount += total_debit_account_amount
                    total_credit_amount += total_credit_account_amount
                    total_balance_amount += total_balance_account_amount
                sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Нийт дүн', data_right_bold)
                sheet.write("D%s"%(rowx), total_pre_amount, data_right_bold)
                sheet.write("E%s"%(rowx), total_debit_amount, data_right_bold)
                sheet.write("F%s"%(rowx), total_credit_amount, data_right_bold)
                sheet.write("G%s"%(rowx), total_balance_amount, data_right_bold)


        elif data['result_selection'] == 'supplier' and data['is_extra'] == False:
            sheet.merge_range("A%s:A%s"%(rowx, rowx+1), u'№', title)
            sheet.merge_range("B%s:C%s"%(rowx, rowx), u'Харилцагч', title)
            sheet.write("B%s"%(rowx+1), u'Код', title)
            sheet.write("C%s"%(rowx+1), u'Нэр', title)
            sheet.merge_range("D%s:D%s"%(rowx, rowx+1), u'Эхний үлдэгдэл', title)
            sheet.merge_range("E%s:F%s"%(rowx, rowx), u'Гүйлгээ', title)
            sheet.write("E%s"%(rowx+1), u'Дебит', title)
            sheet.write("F%s"%(rowx+1), u'Кредит', title)
            sheet.merge_range("G%s:G%s"%(rowx, rowx+1), u'Эцсийн үлдэгдэл', title)
            rowx +=1
            total_pre_amount = 0.0
            total_debit_amount = 0.0
            total_credit_amount = 0.0
            total_balance_amount = 0.0
            if len(account_id)==1:
                rowx +=1
                for part in partner_ids:
                    total_pre_currency_amount = 0.0
                    total_debit_currency_amount = 0.0
                    total_credit_currency_amount = 0.0
                    total_balance_currency_amount = 0.0
                    total_pre_account_amount = 0.0
                    total_debit_account_amount = 0.0
                    total_credit_account_amount = 0.0
                    total_balance_account_amount = 0.0
                    sheet.write("A%s"%(rowx), u'Данс:', txt)
                    account = account_obj.browse(part['account_id'])
                    sheet.merge_range("B%s:C%s"%(rowx, rowx), u'%s %s'%(account.code, account.name), txt)
                    rowx +=1
                    sheet.write("B%s"%(rowx), u'Валют:', txt)
                    currency = self.env['res.currency'].browse(part['currency_id'])
                    sheet.write("C%s"%(rowx), u'%s'%(currency.name), txt)
                    rowx +=1
                    if len(f_journal)==1:
                        self._cr.execute("""
                            select rp.id as partner_id, rp.name as partner_name, rp.ref as partner_ref,
                            sum(aml.debit - aml.credit) as balance, aml.amount_currency
                            from account_move_line aml
                            left join res_partner rp on aml.partner_id = rp.id
                            where aml.account_id = %s
                            and aml.date >= '%s' and aml.date <= '%s' and rp.id = %s
                            and aml.move_id in (select id from account_move where state = '%s')
                            and aml.journal_id = %s
                            group by rp.id, rp.name, rp.ref, aml.amount_currency
                            order by rp.name
                        """%(part['account_id'], date_start, data['start_date'], part['partner_id'], move_state[0], f_journal[0]))
                        pre_lines = self._cr.dictfetchall()
                    else:
                        self._cr.execute("""
                            select rp.id as partner_id, rp.name as partner_name, rp.ref as partner_ref,
                            sum(aml.debit - aml.credit) as balance, aml.amount_currency
                            from account_move_line aml
                            left join res_partner rp on aml.partner_id = rp.id
                            where aml.account_id = %s
                            and aml.date >= '%s' and aml.date <= '%s' and rp.id = %s
                            and aml.move_id in (select id from account_move where state = '%s')
                            and aml.journal_id = %s
                            group by rp.id, rp.name, rp.ref, aml.amount_currency
                            order by rp.name
                        """%(part['account_id'], date_start, data['start_date'], part['partner_id'], move_state[0], f_journal[0]))
                        pre_lines = self._cr.dictfetchall()
                    
                    sheet.write("A%s"%(rowx), num+1, txt)
                    sheet.write("B%s"%(rowx), part['code'], data_left)
                    sheet.write("C%s"%(rowx), part['name'], data_left)
                    balance = 0.0
                    debit = 0.0
                    credit = 0.0
                    if pre_lines != False:
                        for pre_line in pre_lines:
                            balance += pre_line['balance'] or 0.0
                            total_pre_currency_amount += pre_line['amount_currency'] or 0.0
                            total_pre_account_amount += pre_line['balance'] or 0.0
                    # Эхний үлдэгдэл
                    sheet.write("D%s"%(rowx), balance, data_right)

                    self._cr.execute("""
                        select rp.id as partner_id, rp.name as partner_name, rp.ref as partner_ref,
                        sum(aml.debit) as debit, sum(aml.credit) as credit, aml.amount_currency
                        from account_move_line aml
                        left join res_partner rp on aml.partner_id = rp.id
                        where aml.account_id = %s
                        and aml.date >= %s and aml.date <= %s and rp.id = %s
                        and aml.move_id in (select id from account_move where state in %s)
                        group by rp.id, rp.name, rp.ref, aml.amount_currency
                        order by rp.name
                    """, (part['account_id'], data['start_date'], data['end_date'], part['partner_id'], tuple(move_state)))
                    lines = self._cr.dictfetchall()
                    if lines != False:
                        for line in lines:
                            if line['debit'] != 0.0 or line['credit'] != 0.0:
                                debit += line['debit'] or 0.0
                                credit += line['credit'] or 0.0
                                total_debit_currency_amount += line['amount_currency'] or 0.0
                                total_debit_account_amount += line['debit'] or 0.0
                                total_credit_currency_amount += line['amount_currency'] or 0.0
                                total_credit_account_amount += line['credit'] or 0.0


                    # Гүйлгээний дебит кредит
                    sheet.write("E%s"%rowx, debit or 0.0, data_right)
                    sheet.write("F%s"%rowx, credit or 0.0, data_right)
                    # Эцсийн үлдэгдэл
                    balance = balance + (debit or 0.0) - (credit or 0.0)
                    sheet.write("G%s"%rowx, balance, data_right)
                    rowx +=1
                    sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Валют', data_right_bold)
                    sheet.write("D%s"%(rowx), total_pre_currency_amount, data_right_bold)
                    sheet.write("E%s"%(rowx), total_debit_currency_amount, data_right_bold)
                    sheet.write("F%s"%(rowx), total_credit_currency_amount, data_right_bold)
                    sheet.write("G%s"%(rowx), total_balance_currency_amount, data_right_bold)
                    rowx +=1

                    sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Дансны дүн', data_right_bold)
                    sheet.write("D%s"%(rowx), total_pre_account_amount, data_right_bold)
                    sheet.write("E%s"%(rowx), total_debit_account_amount, data_right_bold)
                    sheet.write("F%s"%(rowx), total_credit_account_amount, data_right_bold)
                    sheet.write("G%s"%(rowx), total_balance_account_amount, data_right_bold)
                    rowx +=1
                    total_pre_amount += total_pre_account_amount
                    total_debit_amount += total_debit_account_amount
                    total_credit_amount += total_credit_account_amount
                    total_balance_amount += total_balance_account_amount
                sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Нийт дүн', data_right_bold)
                sheet.write("D%s"%(rowx), total_pre_amount, data_right_bold)
                sheet.write("E%s"%(rowx), total_debit_amount, data_right_bold)
                sheet.write("F%s"%(rowx), total_credit_amount, data_right_bold)
                sheet.write("G%s"%(rowx), total_balance_amount, data_right_bold)
            else:
                rowx +=1
                total_pre_amount = 0.0
                total_debit_amount = 0.0
                total_credit_amount = 0.0
                total_balance_amount = 0.0
                for part in partner_ids:
                    total_pre_currency_amount = 0.0
                    total_debit_currency_amount = 0.0
                    total_credit_currency_amount = 0.0
                    total_balance_currency_amount = 0.0
                    total_pre_account_amount = 0.0
                    total_debit_account_amount = 0.0
                    total_credit_account_amount = 0.0
                    total_balance_account_amount = 0.0
                    sheet.write("A%s"%(rowx), u'Данс:', txt)
                    account = account_obj.browse(part['account_id'])
                    sheet.merge_range("B%s:C%s"%(rowx, rowx), u'%s %s'%(account.code, account.name), txt)
                    rowx +=1
                    sheet.write("B%s"%(rowx), u'Валют:', txt)
                    currency = self.env['res.currency'].browse(part['currency_id'])
                    sheet.write("C%s"%(rowx), u'%s'%(currency.name), txt)
                    rowx +=1
                    if len(f_journal)==1:
                        self._cr.execute("""
                            select rp.id as partner_id, rp.name as partner_name, rp.ref as partner_ref,
                            sum(aml.debit - aml.credit) as balance, aml.amount_currency
                            from account_move_line aml
                            left join res_partner rp on aml.partner_id = rp.id
                            where aml.account_id = %s
                            and aml.date >= '%s' and aml.date <= '%s' and rp.id = %s
                            and aml.move_id in (select id from account_move where state = '%s')
                            and aml.journal_id = %s
                            group by rp.id, rp.name, rp.ref, aml.amount_currency
                            order by rp.name
                        """%(part['account_id'], date_start, data['start_date'], part['partner_id'], move_state[0], f_journal[0]))
                        pre_lines = self._cr.dictfetchall()
                    else:
                        self._cr.execute("""
                            select rp.id as partner_id, rp.name as partner_name, rp.ref as partner_ref,
                            sum(aml.debit - aml.credit) as balance, aml.amount_currency
                            from account_move_line aml
                            left join res_partner rp on aml.partner_id = rp.id
                            where aml.account_id = %s
                            and aml.date >= '%s' and aml.date <= '%s' and rp.id = %s
                            and aml.move_id in (select id from account_move where state = '%s')
                            and aml.journal_id in %s
                            group by rp.id, rp.name, rp.ref, aml.amount_currency
                            order by rp.name
                        """%(part['account_id'], date_start, data['start_date'], part['partner_id'], move_state[0], tuple(f_journal)))
                        pre_lines = self._cr.dictfetchall()
                    
                    sheet.write("A%s"%(rowx), num+1, txt)
                    sheet.write("B%s"%(rowx), part['code'], data_left)
                    sheet.write("C%s"%(rowx), part['name'], data_left)
                    balance = 0.0
                    debit = 0.0
                    credit = 0.0
                    if pre_lines != False:
                        for pre_line in pre_lines:
                            balance += pre_line['balance'] or 0.0
                            total_pre_currency_amount += pre_line['amount_currency'] or 0.0
                            total_pre_account_amount += pre_line['balance'] or 0.0
                    # Эхний үлдэгдэл
                    sheet.write("D%s"%(rowx), balance, data_right)

                    self._cr.execute("""
                        select rp.id as partner_id, rp.name as partner_name, rp.ref as partner_ref,
                        sum(aml.debit) as debit, sum(aml.credit) as credit, aml.amount_currency
                        from account_move_line aml
                        left join res_partner rp on aml.partner_id = rp.id
                        where aml.account_id = %s
                        and aml.date >= %s and aml.date <= %s and rp.id = %s
                        and aml.move_id in (select id from account_move where state in %s)
                        group by rp.id, rp.name, rp.ref, aml.amount_currency
                        order by rp.name
                    """, (part['account_id'], data['start_date'], data['end_date'], part['partner_id'], tuple(move_state)))
                    lines = self._cr.dictfetchall()
                    if lines != False:
                        for line in lines:
                            if line['debit'] != 0.0 or line['credit'] != 0.0:
                                debit += line['debit'] or 0.0
                                credit += line['credit'] or 0.0
                                total_debit_currency_amount += line['amount_currency'] or 0.0
                                total_credit_currency_amount += line['amount_currency'] or 0.0
                                total_debit_account_amount += line['debit'] or 0.0
                                total_credit_account_amount += line['credit'] or 0.0
                    total_balance_currency_amount = total_pre_currency_amount + total_debit_currency_amount - total_credit_currency_amount
                    # Гүйлгээний дебит кредит
                    sheet.write("E%s"%rowx, debit or 0.0, data_right)
                    sheet.write("F%s"%rowx, credit or 0.0, data_right)
                    # Эцсийн үлдэгдэл
                    balance = balance + (debit or 0.0) - (credit or 0.0)
                    total_balance_account_amount = total_pre_account_amount + total_debit_account_amount - total_credit_account_amount
                    sheet.write("G%s"%rowx, balance, data_right)
                    rowx +=1
                    sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Валют', data_right_bold)
                    sheet.write("D%s"%(rowx), total_pre_currency_amount, data_right_bold)
                    sheet.write("E%s"%(rowx), total_debit_currency_amount, data_right_bold)
                    sheet.write("F%s"%(rowx), total_credit_currency_amount, data_right_bold)
                    sheet.write("G%s"%(rowx), total_balance_currency_amount, data_right_bold)
                    rowx +=1

                    sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Дансны дүн', data_right_bold)
                    sheet.write("D%s"%(rowx), total_pre_account_amount, data_right_bold)
                    sheet.write("E%s"%(rowx), total_debit_account_amount, data_right_bold)
                    sheet.write("F%s"%(rowx), total_credit_account_amount, data_right_bold)
                    sheet.write("G%s"%(rowx), total_balance_account_amount, data_right_bold)
                    rowx +=1
                    total_pre_amount += total_pre_account_amount
                    total_debit_amount += total_debit_account_amount
                    total_credit_amount += total_credit_account_amount
                    total_balance_amount += total_balance_account_amount
                sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Нийт дүн', data_right_bold)
                sheet.write("D%s"%(rowx), total_pre_amount, data_right_bold)
                sheet.write("E%s"%(rowx), total_debit_amount, data_right_bold)
                sheet.write("F%s"%(rowx), total_credit_amount, data_right_bold)
                sheet.write("G%s"%(rowx), total_balance_amount, data_right_bold)

            






        

        
            
       
        
        rowx +=3
        sheet.merge_range("A%s:E%s"%(rowx, rowx),  u'Тайлан гаргасан:................................./........................../', data_center_no_border)
        



        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


