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
        return self.env['account.journal'].search([('type','!=','situation'),('company_id','=',company_id.id)])
    

    
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
        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 2, 30)
        sheet.set_column(3, 10, 15)

        company = self.env['res.company'].browse(data['company_id'])
        fiscal_id = self.env['account.fiscal.year'].browse(data['fiscalyear_id'])
        account_id = False
        journal_obj = self.env['account.journal']
        account_move_line_obj = self.env['account.move.line']
        account_move = self.env['account.move']
        account_obj = self.env['account.account']

        partner_obj = self.env['res.partner']
        if data['result_selection']=='customer':
            account_type = ['asset_receivable']
        elif data['result_selection']=='supplier':
            account_type = ['liability_payable']
        else:
            account_type = ['asset_receivable','liability_payable']
        
        f_journal = []
        if fiscal_id.date_from == data['start_date']:
            date_start = fiscal_id.date_from
            journal_id = journal_obj.search([('type','=','opening'),('company_id','=',data['company_id'])])
            f_journal.append(journal_id.id)
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
        self._cr.execute("select id,name from res_partner where parent_id is null group by id order by name")
        partner_parent_id = self._cr.dictfetchall()
        partner_id = []
        move_state = ['draft','posted']
        if data['target_move'] == 'posted':
            move_state = ['posted']
        if data['account_id']:
            account_id = [data['account_id']]
        else:
            account_id = account_obj.search( [('account_type','in',account_type)]).ids
        if data['partner_id']:
            partner_id = [data['partner_id']]                        
        else:
            if self.is_transaction:
                self._cr.execute(""" select aml.partner_id,rp.name, aml.debit,aml.credit as amount from account_move as am left join
                                account_move_line as aml on aml.move_id = am.id left join 
                                res_partner as rp on rp.id=aml.partner_id where aml.partner_id is not null and
                                aml.account_id = %s and am.date >='%s' and am.date <='%s' and 
                                am.state = 'posted' and am.company_id = %s
                                group by aml.partner_id,rp.name,aml.debit,aml.credit order by rp.name asc"""%(account_id,fiscal_id.date_from,data['end_date'], data['company_id']))
                partner_ids = self._cr.dictfetchall()
                for li in partner_ids:
                    if li['amount'] != 0.0 and li['amount'] !=None or li['debit'] !=0.0 and li['debit']!=None:
                        if li['partner_id'] not in partner_id:
                            partner_id.append(li['partner_id'])
               
            else:
                if len(account_id)==1:
                    self._cr.execute(""" select aml.partner_id,rp.name from account_move as am left join
                                account_move_line as aml on aml.move_id = am.id left join 
                                res_partner as rp on rp.id=aml.partner_id where aml.partner_id is not null and
                                am.date >='%s' and am.date <='%s' and aml.account_id=%s and 
                                    am.state = 'posted' and am.company_id = %s 
                                group by aml.partner_id,rp.name order by rp.name asc"""%
                                (fiscal_id.date_from,data['end_date'],account_id, data['company_id']))
                    parts = self._cr.dictfetchall()
                    partner_id = [p['partner_id'] for p in parts]
                else:
                    self._cr.execute(""" select aml.partner_id,rp.name from account_move as am left join
                                account_move_line as aml on aml.move_id = am.id left join 
                                res_partner as rp on rp.id=aml.partner_id where aml.partner_id is not null and
                                am.date >='%s' and am.date <='%s' and aml.account_id in %s and 
                                    am.state = 'posted' and am.company_id = %s 
                                group by aml.partner_id,rp.name order by rp.name asc"""%
                                (fiscal_id.date_from,data['end_date'],tuple(account_id), data['company_id']))
                    parts = self._cr.dictfetchall()
                    for p in parts:
                        partner_id = [p['partner_id'] for p in parts]
        
        sheet.merge_range("A1:C1", u'Байгууллагын нэр: %s' % (data['company_name']), head)
        sheet.merge_range("A2:J2", u'Харилцагчийн дэвтэр', head)
        sheet.merge_range("H3:K3", u'Тайлант хугацаа: %s - %s'%(data['start_date'],data['end_date']) , head)
        
        rowx = 0
        col = 0
        num = 0
        four = 0
        rowx = 4

        move_obj = self.env['account.move']
        pre_balance = False
        journals = self.env['account.journal'].search([])
        journal = []
        for j_ids in journals:
            journal.append(j_ids.id)
        journal_ids = []
        
        for jr_ids in journal_obj.browse(data['account_journal_ids']):
            journal_ids.append(jr_ids.id)
        if data['account_journal_ids']:
            if len(partner_id)==1:
                if len(move_state)==1:
                    move = move_obj.search( [('state','=',move_state[0]),('company_id','=', data['company_id']),('date','>=',date_start),('date','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                else:
                    move = move_obj.search( [('state','in',tuple(move_state)),('company_id','=', data['company_id']),('date','>=',date_start),('date','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                move_ids = []
                for mv in move:
                    move_ids.append(mv.id)
                if len(account_id)==1:
                    account_move_line_id = account_move_line_obj.search( [('move_id','in',tuple(move_ids)),('partner_id','=',partner_id[0]),('account_id','=',account_id[0]),('date','>',data['start_date']),('date','<=',data['end_date'])],order="date asc")
                else:
                    account_move_line_id = account_move_line_obj.search( [('move_id','in',tuple(move_ids)),('partner_id','=',partner_id[0]),('account_id','in',tuple(account_id)),('date','>',data['start_date']),('date','<=',data['end_date'])],order="date asc")

                if len(f_journal)==1:
                    if len(account_id)==1:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id, ml.currency_id, ml.account_id
                                    from account_move_line as ml left join account_move as am on am.id=ml.move_id where 
                                    am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                    and am.journal_id = %s and ml.account_id = %s 
                                    and am.company_id = %s group by ml.partner_id, ml.currency_id, ml.account_id
                                    """%(fiscal_id.date_from,data['start_date'],partner_id[0],f_journal[0],account_id[0], data['company_id']))
                        pre_balance = self._cr.dictfetchall()
                    else:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id, ml.currency_id, ml.account_id
                                        from account_move_line as ml left join account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                        and am.journal_id = %s and ml.account_id in %s 
                                        and am.company_id = %s group by ml.partner_id, ml.currency_id, ml.account_id
                                        """%(fiscal_id.date_from,data['start_date'],partner_id[0],f_journal[0],tuple(account_id), data['company_id']))
                        pre_balance = self._cr.dictfetchall()
                else:
                    if len(account_id)==1:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id, ml.currency_id, ml.account_id
                                        from account_move_line as ml left join account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                        and am.journal_id in %s and ml.account_id = %s and 
                                        am.company_id = %s group by ml.partner_id, ml.currency_id, ml.account_id
                                        """%(fiscal_id.date_from,data['start_date'],
                                                        partner_id[0],
                                                        tuple(f_journal),account_id[0], data['company_id']))
                        pre_balance = self._cr.dictfetchall()
                    else:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id, ml.currency_id, ml.account_id
                                        from account_move_line as ml left join account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                        and am.journal_id in %s and ml.account_id in %s and 
                                        am.company_id = %s group by ml.partner_id, ml.currency_id, ml.account_id
                                        """%(fiscal_id.date_from,data['start_date'],
                                                        partner_id[0],
                                                        tuple(f_journal),tuple(account_id), data['company_id']))
                        pre_balance = self._cr.dictfetchall()
            else:
                if len(move_state)==1:
                    move = move_obj.search( [('state','=',move_state[0]),('date','>=',date_start),('date','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                else:
                    move = move_obj.search( [('state','in',tuple(move_state)),('date','>=',date_start),('date','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                move_ids = []
                for mv in move:
                    move_ids.append(mv.id)
                if len(account_id)==1:
                    account_move_line_id = account_move_line_obj.search([('move_id','in',tuple(move_ids)),('partner_id','in',tuple(partner_id)),('account_id','=',account_id[0]),('date','>',data['start_date']),('date','<=',data['end_date'])],order="date asc")
                else:
                    account_move_line_id = account_move_line_obj.search([('move_id','in',tuple(move_ids)),('partner_id','in',tuple(partner_id)),('account_id','in',tuple(account_id)),('date','>',data['start_date']),('date','<=',data['end_date'])],order="date asc")

                if len(f_journal)==1:
                    if len(partner_id) >1:
                        if len(account_id)>1:
                            self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.currency_id, ml.partner_id, ml.account_id from account_move_line as ml 
                                            left join account_move as am on am.id=ml.move_id where 
                                            am.date>= '%s' and am.date<='%s' and ml.partner_id in %s and am.state='posted'
                                            and am.journal_id =  %s and ml.account_id in %s and
                                            am.company_id = %s group by ml.partner_id, ml.currency_id, ml.account_id
                                            """%(fiscal_id.date_from,data['start_date'],
                                                            tuple(partner_id),
                                                            f_journal[0],tuple(account_id), data['company_id']))
                            pre_balance = self._cr.dictfetchall()
                        else:
                            self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.currency_id, ml.partner_id, ml.account_id from account_move_line as ml 
                                            left join account_move as am on am.id=ml.move_id where 
                                            am.date>= '%s' and am.date<='%s' and ml.partner_id in %s and am.state='posted'
                                            and am.journal_id =  %s and ml.account_id = %s and
                                            am.company_id = %s group by ml.partner_id, ml.currency_id, ml.account_id
                                            """%(fiscal_id.date_from,data['start_date'],
                                                            tuple(partner_id),
                                                            f_journal[0],data['account_id'], data['company_id']))
                            pre_balance = self._cr.dictfetchall()
                    else:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.currency_id, ml.partner_id, ml.account_id from account_move_line as ml 
                                        left join account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date<='%s' and am.state='posted'
                                        and am.journal_id =  %s and ml.account_id = %s and
                                        am.company_id = %s group by ml.partner_id, ml.currency_id, ml.account_id
                                        """%(fiscal_id.date_from,data['start_date'],
                                                        
                                                         f_journal[0],data['account_id'], data['company_id']))
                        pre_balance = self._cr.dictfetchall()
                else:
                    if len(partner_id) > 1:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id, ml.account_id, ml.currency_id from account_move_line as ml 
                                        left join account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date<='%s' and ml.partner_id in %s and am.state='posted'
                                        and am.journal_id in  %s and ml.account_id = %s and
                                        am.company_id = %s 
                                        group by ml.partner_id, ml.account_id, ml.currency_id
                                        """%(fiscal_id.date_from,data['start_date'],
                                                          tuple(partner_id),
                                                         tuple(f_journal),data['account_id'], data['company_id']))
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
                if len(account_id)==1:
                    account_move_line_id = account_move_line_obj.search( [('move_id','in',tuple(move_ids)),('partner_id','=',partner_id),('account_id','=',account_id[0]),('date','>',data['start_date']),('date','<=',data['end_date'])],order="date asc")
                else:
                    account_move_line_id = account_move_line_obj.search( [('move_id','in',tuple(move_ids)),('partner_id','=',partner_id),('account_id','in',tuple(account_id)),('date','>',data['start_date']),('date','<=',data['end_date'])],order="date asc")

                
                if move_id:
                    if len(f_journal)==1:
                        if len(account_id)==1:
                            self._cr.execute("""select sum(ml.debit-ml.credit) as balance, ml.currency_id, ml.partner_id, ml.account_id from account_move_line as ml 
                                                left join account_move as am am.id=ml.move_id where 
                                            am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                            and ml.move_id in %s and ml.journal_id = %s and ml.account_id = %s and
                                            am.company_id = %s 
                                            group by ml.partner_id, ml.currency_id, ml.account_id
                                            """%(fiscal_id.date_from,data['start_date'],
                                                            partner_id[0],tuple(move_id),
                                                            f_journal[0],account_id[0], data['company_id']))
                            pre_balance = self._cr.dictfetchall()
                        else:
                            self._cr.execute("""select sum(ml.debit-ml.credit) as balance, ml.currency_id, ml.partner_id, ml.account_id from account_move_line as ml 
                                            left join account_move as am am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                        and ml.move_id in %s and ml.journal_id = %s and ml.account_id = %s and
                                        am.company_id = %s 
                                        group by ml.partner_id, ml.currency_id, ml.account_id
                                        """%(fiscal_id.date_from,data['start_date'],
                                                          partner_id[0],tuple(move_id),
                                                          f_journal[0],tuple(account_id), data['company_id']))
                        pre_balance = self._cr.dictfetchall()
                    else:
                        if len(account_id)==1:
                            self._cr.execute("""select sum(ml.debit-ml.credit) as balance, ml.currency_id, ml.partner_id, ml.account_id from account_move_line as ml 
                                            left join account_move as am on am.id=ml.move_id where 
                                            am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                            and ml.move_id in %s and ml.journal_id in %s and ml.account_id = %s and
                                            am.company_id = %s
                                            group by ml.partner_id, ml.currency_id, ml.account_id
                                            """%(fiscal_id.date_from,data['start_date'],
                                                            partner_id[0],tuple(move_id),
                                                            tuple(f_journal),account_id[0], data['company_id']))
                            pre_balance = self._cr.dictfetchall()
                        else:
                            self._cr.execute("""select sum(ml.debit-ml.credit) as balance, ml.currency_id, ml.partner_id, ml.account_id from account_move_line as ml 
                                            left join account_move as am on am.id=ml.move_id where 
                                            am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                            and ml.move_id in %s and ml.journal_id in %s and ml.account_id in %s and
                                            am.company_id = %s
                                            group by ml.partner_id, ml.currency_id, ml.account_id
                                            """%(fiscal_id.date_from,data['start_date'],
                                                            partner_id[0],tuple(move_id),
                                                            tuple(f_journal),tuple(account_id), data['company_id']))
                            pre_balance = self._cr.dictfetchall()
            else:
                if len(move_state)==1:
                    move_id = move_obj.search( [('state','=',move_state[0]),('date','>=',date_start),('date','<=',data['start_date']),('journal_id','in',tuple(journal_ids))])
                else:
                    move_id = move_obj.search( [('state','in',tuple(move_state)),('date','>=',date_start),('date','<=',data['start_date']),('journal_id','in',tuple(journal_ids))])
                if len(move_state)==1:
                    move = move_obj.search( [('state','=',move_state[0]),('date','>=',date_start),('date','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                else:
                    move = move_obj.search( [('state','in',tuple(move_state)),('date','>=',date_start),('date','<=',data['end_date']),('journal_id','in',tuple(journal_ids))])
                move_ids = []
                for mv in move:
                    move_ids.append(mv.id)
                if len(account_id)==1:
                    account_move_line_id = account_move_line_obj.search( [('move_id','in',tuple(move_ids)),('partner_id','in',tuple(partner_id)),('account_id','=',account_id),('date','>',data['start_date']),('date','<=',data['end_date'])],order="date asc")
                else:
                    account_move_line_id = account_move_line_obj.search( [('move_id','in',tuple(move_ids)),('partner_id','in',tuple(partner_id)),('account_id','in',tuple(account_id)),('date','>',data['start_date']),('date','<=',data['end_date'])],order="date asc")

                if move_id: 
                    if len(f_journal)==1:
                        if len(account_id)==1:
                            self._cr.execute("""select sum(ml.debit-ml.credit) as balance, ml.currency_id, ml.partner_id, ml.account_id from account_move_line as ml 
                                            account_move as am on am.id=ml.move_id where 
                                            am.date>= '%s' and am.date <='%s' and ml.account_id = %s and ml.partner_id in %s 
                                            and ml.move_id in %s and ml.journal_id = %s and ml.account_id = %s and am.state='posted' 
                                            and am.company_id = %s group by ml.partner_id, ml.currency_id, ml.account_id
                                            """%(fiscal_id.date_from,data['start_date'],
                                                            account_id,tuple(partner_id),tuple(move_id),
                                                            f_journal[0],account_id[0], data['company_id']))
                            pre_balance = self._cr.dictfetchall()
                        else:
                            self._cr.execute("""select sum(ml.debit-ml.credit) as balance, ml.currency_id, ml.partner_id, ml.account_id from account_move_line as ml 
                                            account_move as am on am.id=ml.move_id where 
                                            am.date>= '%s' and am.date <='%s' and ml.account_id = %s and ml.partner_id in %s 
                                            and ml.move_id in %s and ml.journal_id = %s and ml.account_id = %s and am.state='posted' 
                                            and am.company_id = %s group by ml.partner_id, ml.currency_id, ml.account_id
                                            """%(fiscal_id.date_from,data['start_date'],
                                                            account_id,tuple(partner_id),tuple(move_id),
                                                            f_journal[0],tuple(account_id), data['company_id']))
                            pre_balance = self._cr.dictfetchall()
                    else:
                        if len(account_id)==1:
                            self._cr.execute("""select sum(ml.debit-ml.credit) as balance, ml.currency_id, ml.partner_id, ml.account_id from account_move_line as ml left join
                                            account_move as am on am.id=ml.move_id where 
                                            am.date>= '%s' and am.date <='%s' and ml.account_id = %s and ml.partner_id in %s 
                                            and ml.move_id in %s and ml.journal_id in %s and ml.account_id = %s and am.state='posted' 
                                            and am.company_id = %s group by ml.partner_id, ml.currency_id, ml.account_id
                                            """%(fiscal_id.date_from,data['start_date'],
                                                            account_id,tuple(partner_id),tuple(move_id),
                                                            tuple(f_journal),account_id[0], data['company_id']))
                            pre_balance = self._cr.dictfetchall()
                        else:
                            self._cr.execute("""select sum(ml.debit-ml.credit) as balance, ml.currency_id, ml.partner_id, ml.account_id from account_move_line as ml left join
                                        account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.account_id = %s and ml.partner_id in %s 
                                        and ml.move_id in %s and ml.journal_id in %s and ml.account_id in %s and am.state='posted' 
                                        and am.company_id = %s group by ml.partner_id, ml.currency_id, ml.account_id
                                        """%(fiscal_id.date_from,data['start_date'],
                                                          account_id,tuple(partner_id),tuple(move_id),
                                                          tuple(f_journal),tuple(account_id), data['company_id']))
                            pre_balance = self._cr.dictfetchall()
        
            
        
        invoice_obj = self.env['account.move']
        total_amount = 0
        if partner_id:
            if data['is_extra'] == True:
                sheet.merge_range("A%s:A%s"%(rowx, rowx+1), u'Огноо', data_bold_center)
                sheet.merge_range("B%s:B%s"%(rowx, rowx+1), u'Журнал', data_bold_center)
                sheet.merge_range("C%s:C%s"%(rowx, rowx+1), u'Сурвалж', data_bold_center)
                sheet.merge_range("D%s:D%s"%(rowx, rowx+1), u'Данс', data_bold_center)
                sheet.merge_range("E%s:E%s"%(rowx, rowx+1), u'Валют', data_bold_center)
                sheet.merge_range("F%s:F%s"%(rowx, rowx+1), u'Дебит', data_bold_center)
                sheet.merge_range("G%s:G%s"%(rowx, rowx+1), u'Валютаарх дүн', data_bold_center)
                sheet.merge_range("H%s:H%s"%(rowx, rowx+1), u'Кредит', data_bold_center)
                sheet.merge_range("I%s:I%s"%(rowx, rowx+1), u'Валютаарх дүн', data_bold_center)
                sheet.merge_range("J%s:J%s"%(rowx, rowx+1), u'Үлдэгдэл', data_bold_center)
                sheet.merge_range("K%s:K%s"%(rowx, rowx+1), u'Валютаарх дүн', data_bold_center)
            else:
                sheet.merge_range("A%s:A%s"%(rowx, rowx+1), u'Харилцагчийн нэр', data_bold_center)
                sheet.merge_range("B%s:B%s"%(rowx, rowx+1), u'Татвар төлөгчийн дугаар', data_bold_center)
                sheet.merge_range("C%s:C%s"%(rowx, rowx+1), u'Данс', data_bold_center)
                sheet.merge_range("D%s:D%s"%(rowx, rowx+1), u'Эхний үлдэгдэл', data_bold_center)
                sheet.merge_range("E%s:E%s"%(rowx, rowx+1), u'Валют', data_bold_center)
                sheet.merge_range("F%s:F%s"%(rowx, rowx+1), u'Дебит', data_bold_center)
                sheet.merge_range("G%s:G%s"%(rowx, rowx+1), u'Валютаарх дүн', data_bold_center)
                sheet.merge_range("H%s:H%s"%(rowx, rowx+1), u'Кредит', data_bold_center)
                sheet.merge_range("I%s:I%s"%(rowx, rowx+1), u'Валютаарх дүн', data_bold_center)
                sheet.merge_range("J%s:J%s"%(rowx, rowx+1), u'Үлдэгдэл', data_bold_center)
                sheet.merge_range("K%s:K%s"%(rowx, rowx+1), u'Валютаарх дүн', data_bold_center)
            rowx = 6
            for line in partner_obj.browse(partner_id):
                for acc in account_obj.browse(account_id):
                    if data['is_extra'] == True:
                        if pre_balance !=[] and pre_balance !=False or len(account_move_line_id)>=1:
                            pr_balance = 0.0
                            balance = 0.0
                            for li in pre_balance:
                                if li['partner_id'] == line.id and li['account_id'] == acc.id:
                                    if li['balance'] < 0.0:
                                        balance += li['balance']*(-1)
                                    else:
                                        balance += li['balance']
                                    #balance += li['balance']
                                    pr_balance = li['balance']
                            
                            
                            sum_debit = 0.0
                            sum_credit = 0.0
                            
                            
                            
                            currency_balance = 0
                            currency_sum_debit = 0
                            currency_sum_credit = 0
                            total_currency_balance = 0
                            sheet.merge_range("A%s:B%s"%(rowx, rowx), u'%s'%(line.name),data_left)
                            sheet.write("C%s"%rowx, u'%s'%(line.vat),data_left)
                            sheet.write("D%s"%rowx, u'%s'%(acc.code),data_left)
                            sheet.write("E%s"%rowx, u'Эхний үлдэгдэл',data_left)
                            sheet.write("F%s"%rowx, balance, data_left)
                            rowx +=1
                            for move in account_move_line_id:
                                ref = ''
                                if line.id == move.partner_id.id and move.account_id.id == acc.id:
                                    sheet.write("A%s"%rowx, u'%s'%move.date, data_center)
                                    sheet.write("B%s"%rowx, u'%s'%move.journal_id.name,data_center)
                                    invoice_id = invoice_obj.search([('id','=',move.move_id.id),('state','=','posted')])
                                    if invoice_id:
                                        invoice = invoice_id
                                        ref = invoice.invoice_origin
                                    sheet.write("C%s"%rowx, u'%s,%s,%s'%(move.name,move.ref,ref),data_center)
                                    sheet.write("D%s"%rowx, u'%s'%(move.account_id.code),data_center)
                                    sheet.write("E%s"%rowx, u'%s'%(move.currency_id.name),data_center)
                                    
                                    sheet.write("F%s"%rowx, move.debit,data_right)
                                    if move.currency_id.id !=move.company_id.currency_id.id:
                                        sheet.write("G%s"%rowx, move.amount_currency,data_right)
                                    else:
                                        sheet.write("G%s"%rowx, 0,data_right)
                                    
                                    sheet.write("H%s"%rowx, move.credit,data_right)
                                    if move.currency_id.id !=move.company_id.currency_id.id:
                                        sheet.write("I%s"%rowx, move.amount_currency,data_right)
                                    else:
                                        sheet.write("I%s"%rowx, 0,data_right)
                                
                                    if move.debit >0.0:
                                        if move.account_id.account_type == 'liability_payable':
                                            balance = balance-move.debit
                                            sum_debit +=move.debit
                                            if move.currency_id.id !=move.company_id.currency_id.id:
                                                currency_balance -= move.amount_currency
                                                currency_sum_debit += move.amount_currency
                                        else:
                                            balance = balance+move.debit
                                            sum_debit +=move.debit
                                            if move.currency_id.id !=move.company_id.currency_id.id:
                                                currency_balance += move.amount_currency
                                                currency_sum_debit += move.amount_currency
                                    else:
                                        if move.account_id.account_type == 'liability_payable':
                                            balance = balance+move.credit
                                            sum_credit +=move.credit
                                            if move.currency_id.id !=move.company_id.currency_id.id:
                                                currency_balance += move.amount_currency
                                                currency_sum_credit += move.amount_currency
                                        else:
                                            balance = balance-move.credit
                                            sum_credit +=move.credit
                                            if move.currency_id.id !=move.company_id.currency_id.id:
                                                currency_balance -= move.amount_currency
                                                currency_sum_credit += move.amount_currency
                                    sheet.write("J%s"%rowx, balance,data_right)
                                    sheet.write("K%s"%rowx, currency_balance,data_right)
                                    rowx +=1
                                    total_currency_balance += currency_balance

                            
                            sheet.merge_range("A%s:E%s"%(rowx, rowx), u'Нийт',data_right_bold)
                            sheet.write("F%s"%rowx, sum_debit,data_right_bold)
                            sheet.write("G%s"%rowx, currency_sum_debit,data_right_bold)
                            sheet.write("H%s"%rowx, sum_credit, data_right_bold)
                            sheet.write("I%s"%rowx, currency_sum_credit,data_right_bold)
                            sheet.write("J%s"%rowx, balance, data_right_bold)
                            sheet.write("K%s"%rowx, total_currency_balance,data_right_bold)
                            rowx +=2
                    else:
                        currency_obj = self.env['res.currency']
                        sum_debit = 0.0
                        sum_credit = 0.0
                        pr_balance = 0.0
                        balance = 0.0
                        currency_balance = 0
                        currency_sum_debit = 0
                        currency_sum_credit = 0
                        currency = False
                        if account_move_line_id:
                            
                            

                            if pre_balance !=[] and pre_balance !=False:
                                for li in pre_balance:
                                    if li['partner_id'] == line.id and li['account_id'] == acc.id:
                                        if li['balance'] < 0.0:
                                            balance += li['balance']*(-1)
                                        else:
                                            balance += li['balance']
                                        #balance += li['balance']
                                        currency = currency_obj.browse(li['currency_id']).name
                                        pr_balance = li['balance']
                            
                            for move in account_move_line_id:
                                if move.account_id.id == acc.id:
                                    if move.partner_id.id == line.id:
                                        if move.debit >0.0:
                                            #balance = balance+move.debit
                                            if move.account_id.account_type == 'liability_payable':
                                                sum_debit +=move.debit
                                                if move.currency_id.id !=move.company_id.currency_id.id:
                                                    currency_balance -= move.amount_currency
                                                    currency_sum_debit += move.amount_currency
                                            else:
                                                sum_debit +=move.debit
                                                if move.currency_id.id !=move.company_id.currency_id.id:
                                                    currency_balance += move.amount_currency
                                                    currency_sum_debit += move.amount_currency
                                        else:
                                            #balance = balance-move.credit
                                            if move.account_id.account_type == 'liability_payable':
                                                sum_credit -=move.credit
                                                if move.currency_id.id !=move.company_id.currency_id.id:
                                                    currency_balance += move.amount_currency
                                                    currency_sum_credit += move.amount_currency
                                            else:
                                                sum_credit +=move.credit
                                                if move.currency_id.id !=move.company_id.currency_id.id:
                                                    currency_balance -= move.amount_currency
                                                    currency_sum_credit += move.amount_currency
                            if balance == 0.0 and sum_debit == 0.0 and sum_credit == 0.0:
                                continue
                            else:
                                sheet.write("A%s"%rowx, u'%s'%(line.name),data_left)
                                sheet.write("B%s"%rowx, u'%s'%(line.vat),data_left)
                                sheet.write("C%s"%rowx, u'%s'%(acc.code),data_left)
                                #if balance < 0.0:
                                #    balance = balance*(-1)
                                #    currency_balance = currency_balance*(-1)
                                sheet.write("D%s"%rowx, balance,data_right)
                                sheet.write("E%s"%rowx, currency or 'MNT',data_right)
                                sheet.write("F%s"%rowx, sum_debit,data_right)
                                sheet.write("G%s"%rowx, currency_sum_debit,data_right)
                                sheet.write("H%s"%rowx, sum_credit,data_right)
                                sheet.write("I%s"%rowx, currency_sum_credit,data_right)
                                balance = balance - sum_credit + sum_debit
                                sheet.write("J%s"%rowx, balance, data_right)
                                sheet.write("K%s"%rowx, currency_balance, data_right)
                                total_amount +=balance
                                rowx +=1   
                        else:
                            if pre_balance !=[] and pre_balance !=False:
                                for li in pre_balance:
                                    if li['partner_id'] == line.id and li['account_id'] == account_id:
                                        if li['balance'] < 0.0:
                                            
                                            balance += li['balance']*(-1)
                                        else:
                                            balance += li['balance']
                                        #balance = li['balance']
                                        pr_balance = li['balance']
                                sheet.write("A%s"%rowx, u'%s'%(line.name),data_left)
                                sheet.write("B%s"%rowx, u'%s'%(line.vat),data_left)
                                sheet.write("C%s"%rowx, u'%s %s'%(acc.code,acc.name),data_left)
                                sheet.write("D%s"%rowx, balance,data_right)
                                sheet.write("E%s"%rowx, 0.0,data_right)
                                sheet.write("F%s"%rowx, 0.0,data_right)
                                sheet.write("G%s"%rowx, balance, data_right)
                                total_amount +=balance
                                rowx +=1 
        sheet.merge_range("A%s:I%s"%(rowx, rowx), u'Нийт',data_bold_left)
        sheet.write("J%s"%rowx, total_amount,data_right_bold)
        rowx +=2
        sheet.merge_range("A%s:E%s"%(rowx, rowx),  u'Дэд захирал:................................./........................../', data_center_no_border)
        sheet.merge_range("A%s:E%s"%(rowx+1, rowx+1),  u'Нягтлан бодогч:................................/............................../', data_center_no_border)
        



        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


