# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils
import time

class AccountPartnerLedgerExcelReport(models.TransientModel):
    _name = 'account.partner.ledger.excel.report'
    _description = 'Account Partner Ledger Report'

    
    def _get_all_journal(self):
        return self.env['account.journal'].search([('type','!=','opening')])

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    fiscalyear_id = fields.Many2one('account.fiscal.year',string='Fiscal year',required=True)
    is_transaction = fields.Boolean(string='Үлдэгдэлтэй, гүйлгээтэй эсэх')
    account_id = fields.Many2one('account.account', string='Account', required=True)
    is_currency = fields.Boolean(string='Is currency')
    target_move = fields.Selection([('posted','Батлагдсан гүйлгээ'),
                                    ('all','Бүх гүйлгээ')], string='State',
                                    required=True, default='posted')
    result_selection = fields.Selection([('customer','Авлагын данс'),
                                         ('supplier','Өглөгийн данс'),
                                         ('customer_supplier','Өглөг авлагийн данс')],
                                         string='Partner',required=True,default='customer')
    filter = fields.Selection([('filter_date', 'Filter date')], string='Filter', required=True, 
                              default='filter_date')
    partner_id = fields.Many2one('res.partner', string='Partner')
    is_extra = fields.Boolean(string='Is extra')
    start_date = fields.Date(string='Start date', default=lambda *a: time.strftime('%Y-%m-01'))
    end_date = fields.Date(string='End date', default=lambda *a: time.strftime('%Y-%m-%d'))
    account_journal_ids = fields.Many2many('account.journal', 'account_partner_new_ledger_excel_journal_rel', 'account_id', 'journal_id',
                                           string='Journals', default=_get_all_journal) 

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'filter': self.filter,
            'is_extra': self.is_extra,
            'fiscalyear_id': self.fiscalyear_id.id,
            'result_selection': self.result_selection,
            'is_transaction': self.is_transaction,
            'state': self.target_move,
            'account_id': self.account_id.id
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'account.partner.ledger.excel.report',
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
                                    'font_size': 16
                                    })
        header_txt = workbook.add_format({
                                    'align': 'center',
                                    'font_size': 12
                                })

        data_left_border_bold = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'bold':True,
                                    'font_size': 12
                                })
        data_left_border = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'bold':False,
                                    'font_size': 12
                                })
        data_right_border = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'bold':False,
                                    'font_size': 12
                                })

        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'bold':False,
                                    'font_size': 12
                                }) 
        
        data_right_bold = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'bold':True,
                                    'font_size': 12
                                })


        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'bold':False,
                                    'font_size': 12
                                })
        
        data_center_border = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'bold':False,
                                    'font_size': 12
                                })
        

        sheet.set_column(0, 8, 15)
        sheet.merge_range('A2:B2', u'Байгууллагын нэр: %s' % (data['company_name']), header_txt)
        sheet.merge_range('A1:H1', u'Харилцагчийн дэвтэр', head)
        sheet.merge_range('F2:H2', u'Тайлант хугацаа: %s - %s'%(data['start_date'],data['end_date']) , header_txt)


        fiscal_id = self.env['account.fiscal.year'].browse(data['fiscalyear_id'])
        account_id = False
        account_obj = self.env['account.account']
        journal_obj = self.env['account.journal']
        account_move_line_obj = self.env['account.move.line']
        account_move = self.env['account.move']
        partner_obj = self.env['res.partner']
        if data['result_selection'] == 'customer':
            account_type = ['asset_receivable']
        elif data['result_selection'] == 'supplier':
            account_type = ['liability_payable']
        else:
            account_type = ['asset_receivable','liability_payable']
        
        f_journal = []
        if fiscal_id.date_to == data['start_date']:
            date_start = fiscal_id.date_start
            journal_id = journal_obj.search([('type','=','opening'),('company_id','=',data['company_id'])],limit=1)
            f_journal.append(journal_id.id)
        else:
            date_start = data['start_date']
            journal_id = journal_obj.search([('type','=','opening'),('company_id','=',data['company_id'])],limit=1)
            move_id = account_move.search([('date','=',data['start_date']),('journal_id','=',journal_id.id),('state','=','posted'),('company_id','=',data['company_id'])])
            if move_id != False:
                journal_id = journal_obj.search([('type','=','opening')])
            else:
                journal_id = journal_obj.search([])
            for lins in journal_id:
                f_journal.append(lins.id)

        self._cr.execute("select id,name from res_partner where parent_id is null group by id order by name")
        partner_parent_id = self._cr.dictfetchall()
        partner_id = []
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']
        if self.account_id:
            account_id = self.account_id.id
        else:
            if account_type:
                account_id = account_obj.search( [('account_type','=',account_type[0])]).ids
            else:
                account_id = account_obj.search( [('account_type','in',tuple(account_type))]).ids
            
        print ("account_id",account_id)
        if self.partner_id:
            partner_id.append(self.partner_id.id)
        else:
            if data['is_transaction'] == True:
                self._cr.execute(""" select aml.partner_id,rp.name, aml.debit,aml.credit as amount from account_move as am left join
                               account_move_line as aml on aml.move_id = am.id left join 
                               res_partner as rp on rp.id=aml.partner_id where aml.partner_id is not null and
                               aml.account_id = %s and am.date >='%s' and am.date <='%s' and 
                               am.state = 'posted'
                               group by aml.partner_id,rp.name,aml.debit,aml.credit order by rp.name asc"""%(account_id,fiscal_id.date_start,data['end_date']))
                partner_ids = self._cr.dictfetchall()
                for li in partner_ids:
                    print ("dddddddd aaaa", li)
                    if li['amount'] != 0.0 and li['amount'] !=None or li['debit'] !=0.0 and li['debit']!=None:
                        if li['partner_id'] not in partner_id:
                            partner_id.append(li['partner_id'])
               
            else:
                if len(account_id)==1:
                    self._cr.execute(""" select aml.partner_id,rp.name from account_move as am left join
                                account_move_line as aml on aml.move_id = am.id left join 
                                res_partner as rp on rp.id=aml.partner_id where aml.partner_id is not null and
                                am.date >='%s' and am.date <='%s' and aml.account_id =%s and 
                                am.state = 'posted'
                                group by aml.partner_id,rp.name order by rp.name asc"""%
                                (fiscal_id.date_from,data['end_date'],account_id))
                    parts = self._cr.dictfetchall()
                    partner_id = [p['partner_id'] for p in parts]
                else:
                    self._cr.execute(""" select aml.partner_id,rp.name from account_move as am left join
                                account_move_line as aml on aml.move_id = am.id left join 
                                res_partner as rp on rp.id = aml.partner_id where aml.partner_id is not null and
                                am.date >='%s' and am.date <='%s' and aml.account_id in %s and 
                                am.state = 'posted'
                                group by aml.partner_id,rp.name order by rp.name asc"""%
                                (fiscal_id.date_from,data['end_date'],tuple(account_id)))
                    parts = self._cr.dictfetchall()
                    partner_id = [p['partner_id'] for p in parts]
        move_obj = self.env['account.move']
        pre_balance = False
        journals = self.env['account.journal'].search([])
        journal = []
        for j_ids in journals:
            journal.append(j_ids.id)
        journal_ids = []
        for jr_ids in self.account_journal_ids:
            journal_ids.append(jr_ids.id)
        
        if data['filter'] == 'filter_date':
            if len(partner_id)==1:
                if len(move_state)==1:
                    move = move_obj.search( [('state','=',move_state[0]),('date','>=',data['date_start']),('date','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                else:
                    move = move_obj.search( [('state','in',tuple(move_state)),('date','>=',data['date_start']),('date','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                move_ids = []
                for mv in move:
                    move_ids.append(mv.id)
                account_move_line_id = account_move_line_obj.search( [('move_id','in',tuple(move_ids)),('partner_id','=',partner_id[0]),('account_id','=',data['account_id']),('date','>',data['start_date']),('date','<=',data['end_date'])],order="date asc")
                if len(f_journal)==1:
                    self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id 
                                    from account_move_line as ml left join account_move as am on am.id=ml.move_id where 
                                    am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                    and am.journal_id = %s and ml.account_id = %s group by ml.partner_id
                                    """%(fiscal_id.date_from,data['start_date'],partner_id[0],f_journal[0],data['account_id']))
                    pre_balance = self._cr.dictfetchall()
                else:
                    self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id 
                                    from account_move_line as ml left join account_move as am on am.id=ml.move_id where 
                                    am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                    and am.journal_id in %s and ml.account_id = %s group by ml.partner_id
                                    """%(fiscal_id.date_from,data['start_date'],
                                                      partner_id[0],
                                                      tuple(f_journal),data['account_id']))
                    pre_balance = self._cr.dictfetchall()
            else:
                print ("dddddd aaaa",move_state)
                if len(move_state)==1:
                    
                    move = move_obj.search( [('state','=',move_state[0]),('date','>=',data['start_date']),('date','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                else:
                    move = move_obj.search( [('state','in',tuple(move_state)),('date','>=',data['start_date']),('date','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                move_ids = []
                for mv in move:
                    move_ids.append(mv.id)
                account_move_line_id = account_move_line_obj.search([('move_id','in',tuple(move_ids)),('partner_id','in',tuple(partner_id)),('account_id','=',data['account_id']),('date','>',data['start_date']),('date','<=',data['end_date'])],order="date asc")
                if len(f_journal)==1:
                    self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id from account_move_line as ml 
                                    left join account_move as am on am.id=ml.move_id where 
                                    am.date>= '%s' and am.date<='%s' and ml.partner_id in %s and am.state='posted'
                                    and am.journal_id =  %s and ml.account_id = %s group by ml.partner_id
                                    """%(fiscal_id.date_from,data['start_date'],
                                                      tuple(partner_id),
                                                     f_journal[0],data['account_id']))
                    pre_balance = self._cr.dictfetchall()
                else:
                    if len(partner_id) > 1:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id from account_move_line as ml 
                                        left join account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date<='%s' and ml.partner_id in %s and am.state='posted'
                                        and am.journal_id in  %s and ml.account_id = %s group by ml.partner_id
                                        """%(fiscal_id.date_from,data['start_date'],
                                                          tuple(partner_id),
                                                         tuple(f_journal),data['account_id']))
                        pre_balance = self._cr.dictfetchall()
        else:
            if len(partner_id)==1:
                if len(move_state)==1:
                    move_id = move_obj.search( [('state','=',move_state[0]),('date','>=',date_start),('date','<=',data['start_date']),('journal_id','in',tuple(journal_ids))])
                else:
                    move_id = move_obj.search( [('state','in',tuple(move_state)),('date','>=',date_start),('date','<=',data['start_date']),('journal_id','in',tuple(journal_ids))])
                if len(move_state)==1:
                    move = move_obj.search( [('state','=',move_state[0]),('date','>=',date_start),('period_id','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                else:
                    move = move_obj.search( [('state','in',tuple(move_state)),('date','>=',date_start),('period_id','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                move_ids = []
                for mv in move:
                    move_ids.append(mv.id)
                account_move_line_id = account_move_line_obj.search( [('move_id','in',tuple(move_ids)),('partner_id','=',partner_id),('account_id','=',self.account_id.id),('date','>',data['start_date']),('date','<=',data['end_date'])],order="date asc")
                if move_id:
                    if len(f_journal)==1:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id from account_move_line as ml 
                                            left join account_move as am am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                        and ml.move_id in %s and ml.journal_id = %s and ml.account_id = %s group by ml.partner_id
                                        """%(fiscal_id.date_from,data['start_date'],
                                                          partner_id[0],tuple(move_id),
                                                          f_journal[0],data['account_id']))
                        pre_balance = self._cr.dictfetchall()
                    else:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id from account_move_line as ml 
                                        left join account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                        and ml.move_id in %s and ml.journal_id in %s and ml.account_id = %s group by ml.partner_id
                                        """%(fiscal_id.date_from,data['start_date'],
                                                          partner_id[0],tuple(move_id),
                                                          tuple(f_journal),data['account_id']))
                        pre_balance = self._cr.dictfetchall()
            else:
                if len(move_state)==1:
                    move_id = move_obj.search( [('state','=',move_state[0]),('date','>=',data['date_start']),('date','<=',data['start_date']),('journal_id','in',tuple(journal_ids))])
                else:
                    move_id = move_obj.search( [('state','in',tuple(move_state)),('date','>=',data['date_start']),('date','<=',data['start_date']),('journal_id','in',tuple(journal_ids))])
                if len(move_state)==1:
                    move = move_obj.search( [('state','=',move_state[0]),('date','>=',data['date_start']),('date','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                else:
                    move = move_obj.search( [('state','in',tuple(move_state)),('date','>=',data['date_start']),('date','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                move_ids = []
                for mv in move:
                    move_ids.append(mv.id)
                account_move_line_id = account_move_line_obj.search( [('move_id','in',tuple(move_ids)),('partner_id','in',tuple(partner_id)),('account_id','=',self.account_id.id),('date','>',data['start_date']),('date','<=',data['end_date'])],order="date asc")
                if move_id: 
                    if len(f_journal)==1:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id from account_move_line as ml 
                                        account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.account_id = %s and ml.partner_id in %s 
                                        and ml.move_id in %s and ml.journal_id = %s and ml.account_id = %s and am.state='posted' group by ml.partner_id 
                                        """%(fiscal_id.date_from,data['start_date'],
                                                          account_id,tuple(partner_id),tuple(move_id),
                                                          f_journal[0],data['account_id']))
                        pre_balance = self._cr.dictfetchall()
                    else:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id from account_move_line as ml left join
                                        account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.account_id = %s and ml.partner_id in %s 
                                        and ml.move_id in %s and ml.journal_id in %s and ml.account_id = %s and am.state='posted' group by ml.partner_id 
                                        """%(fiscal_id.date_from,data['start_date'],
                                                          account_id,tuple(partner_id),tuple(move_id),
                                                          tuple(f_journal),data['account_id']))
                        pre_balance = self._cr.dictfetchall()
        invoice_obj = self.env['account.move']
        
        total_amount = 0
        print ("aaaa",partner_id)
        rowx = 4
        if partner_id:
            if self.is_extra == True:

                sheet.merge_range('A%s:A%s'%(rowx, rowx+1), u'Огноо', data_left_border_bold)
                sheet.merge_range('B%s:B%s'%(rowx, rowx+1), u'Журнал', data_left_border_bold)
                sheet.merge_range('C%s:C%s'%(rowx, rowx+1), u'Сурвалж', data_left_border_bold)
                sheet.merge_range('D%s:D%s'%(rowx, rowx+1), u'Данс', data_left_border_bold)
                sheet.merge_range('E%s:E%s'%(rowx, rowx+1), u'Дебит', data_left_border_bold)
                sheet.merge_range('F%s:F%s'%(rowx, rowx+1), u'Кредит', data_left_border_bold)
                sheet.merge_range('G%s:G%s'%(rowx, rowx+1), u'Үлдэгдэл', data_left_border_bold)
            else:
                sheet.merge_range('A%s:A%s'%(rowx, rowx+1), u'Харилцагчийн нэр', data_left_border_bold)
                sheet.merge_range('B%s:B%s'%(rowx, rowx+1), u'Татвар', data_left_border_bold)
                sheet.merge_range('C%s:C%s'%(rowx, rowx+1), u'Данс', data_left_border_bold)
                sheet.merge_range('D%s:D%s'%(rowx, rowx+1), u'Эхний үлдэгдэл', data_left_border_bold)
                sheet.merge_range('E%s:E%s'%(rowx, rowx+1), u'Дебит', data_left_border_bold)
                sheet.merge_range('F%s:F%s'%(rowx, rowx+1), u'Кредит', data_left_border_bold)
                sheet.merge_range('G%s:G%s'%(rowx, rowx+1), u'Үлдэгдэл', data_left_border_bold)
            
            for line in partner_obj.browse(partner_id):
                if self.is_extra == True:
                    if pre_balance !=[] and pre_balance !=False or len(account_move_line_id)>=1:
                        pr_balance = 0.0
                        balance = 0.0
                        for li in pre_balance:
                            if li['partner_id'] == line.id:
                                balance += li['balance']
                                pr_balance = li['balance']
                        
                        sheet.merge_range("A%s:C%s"%(rowx, rowx), u'%s'%(line.name), data_left_border)
                        sheet.merge_range("D%s:D%s"%(rowx, rowx), u'%s'%(line.vat), data_left_border)
                        sum_debit = 0.0
                        sum_credit = 0.0
                        
                        sheet.merge_range("E%s:E%s"%(rowx, rowx), u'Эхний үлдэгдэл', data_left_border)
                        sheet.merge_range("F%s:F%s"%(rowx, rowx), balance, data_left_border)
                        rowx +=1
                        
                        for move in account_move_line_id:
                            ref = ''
                            if line.id == move.partner_id.id:
                                sheet.write("A%s"%rowx, u'%s'%move.date, data_center_border)
                                sheet.write("B%s"%rowx, u'%s'%move.journal_id.name,data_center_border)
                                invoice_id = invoice_obj.search([('id','=',move.move_id.id),('state','=','posted')])
                                if invoice_id:
                                    invoice = invoice_id
                                    ref = invoice.invoice_origin
                                sheet.write("C%s"%rowx, u'%s,%s,%s'%(move.name,move.ref,ref),data_center_border)
                                sheet.write("D%s"%rowx, u'%s'%(move.account_id.code),data_center_border)
                                
                                sheet.write("E%s"%rowx, u'%s'%move.debit, data_right)
                                sheet.write("F%s"%rowx, u'%s'%move.credit, data_right)
                                if move.debit >0.0:
                                    balance = balance+move.debit
                                    sum_debit +=move.debit
                                else:
                                    balance = balance-move.credit
                                    sum_credit +=move.credit
                                sheet.write("G%s"%rowx, u'%s'%balance,data_right)
                                rowx +=1
                        
                        sheet.merge_range("A%s:C%s"%(rowx, rowx), u'Нийт', data_right_bold)
                        sheet.merge_range("D%s:D%s"%(rowx, rowx), sum_debit, data_right_bold)
                        sheet.write("E%s"%rowx, sum_credit, data_right_bold)
                        sheet.write("F%s"%rowx, balance, data_right_bold)
                        rowx +=2
                else:
                    sum_debit = 0.0
                    sum_credit = 0.0
                    pr_balance = 0.0
                    balance = 0.0
                    if account_move_line_id:

                        sheet.merge_range("A%s:A%s"%(rowx, rowx), u'%s'%(line.name), data_left)
                        sheet.merge_range("B%s:B%s"%(rowx, rowx), u'%s'%(line.vat),  data_left)
                        if pre_balance !=[] and pre_balance !=False:
                            for li in pre_balance:
                                if li['partner_id'] == line.id:
                                    balance += li['balance']
                                    pr_balance = li['balance']
                        sheet.merge_range(rowx, rowx, 2, 2, u'%s'%(self.account_id.code),data_left)
                        sheet.merge_range(rowx, rowx, 3, 3, balance,data_right)
                        for move in account_move_line_id:
                            if move.partner_id.id == line.id:
                                if move.debit >0.0:
                                    balance = balance+move.debit
                                    sum_debit +=move.debit
                                else:
                                    balance = balance-move.credit
                                    sum_credit +=move.credit
                                    
                        sheet.write(rowx, 4, sum_debit, data_right)
                        sheet.write(rowx, 5, sum_credit, data_right)
                        sheet.write(rowx, 6, balance, data_right)
                        total_amount +=balance
                        rowx +=1   
                    else:
                        if pre_balance !=[] and pre_balance !=False:
                            for li in pre_balance:
                                if li['partner_id'] == line.id:
                                    balance = li['balance']
                                    pr_balance = li['balance']
                            sheet.merge_range('A%s:E%s'%(rowx, rowx), u'%s'%(line.name),data_right_border)
                            sheet.merge_range('A%s:E%s'%(rowx, rowx), u'%s'%(line.vat),data_right_border)
                            sheet.merge_range('A%s:E%s'%(rowx, rowx), u'%s %s'%(self.account_id.code,self.account_id.name),data_right_border)
                            sheet.merge_range('A%s:E%s'%(rowx, rowx), balance,data_right_border)
                            sheet.write('A%s'%rowx, 0.0, data_right_border)
                            sheet.write('A%s'%rowx, 0.0, data_right_border)
                            sheet.write('A%s'%rowx, balance, data_right_border)
                            total_amount +=balance
                            rowx +=1 
        #sheet.merge_range('A%s:E%s'%(rowx, rowx), u'Нийт',data_left_border)
        #sheet.merge_range('A%s:E%s'%(rowx, rowx), total_amount, data_left_border)
        #rowx +=2
        #sheet.merge_range('A%s:E%s'%(rowx, rowx), u'Дэд захирал:................................./........................../', data_left_border)
        #sheet.merge_range('A%s:E%s'%(rowx, rowx), u'Нягтлан бодогч:................................/............................../', data_left_border)
        
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


