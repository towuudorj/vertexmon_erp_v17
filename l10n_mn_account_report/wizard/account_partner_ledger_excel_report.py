# -*- coding: utf-8 -*-

import io
import json
import xlsxwriter
from odoo import fields, models
from odoo.tools import date_utils

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
    period_id = fields.Many2one('account.period', string='Period')
    account_journal_ids = fields.Many2many('account.journal', 'account_partner_new_ledger_excel_journal_rel', 'account_id', 'journal_id',
                                           string='Journals', default=_get_all_journal) 

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'account_ids': self.account_ids.ids
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
        company = self.env['res.company'].browse(self.company_id.id)
        fiscal_id = self.fiscalyear_id
        account_id = False
        journal_obj = self.env['account.journal']
        account_move_line_obj = self.env['account.move.line']
        account_move = self.env['account.move']
        partner_obj = self.env['res.partner']
        if self.result_selection=='customer':
            account_type = ['receivable']
        elif self.result_selection=='supplier':
            account_type = ['payable']
        else:
            account_type = ['receivable','payable']
        
        f_journal = []
        if fiscal_id.date_start == self.start_date:
            date_start = fiscal_id.date_start
            journal_id = journal_obj.search([('type','=','opening'),('company_id','=',self.company_id.id)],limit=1)
            f_journal.append(journal_id.id)
        else:
            date_start = self.start_date
            journal_id = journal_obj.search([('type','=','opening'),('company_id','=',self.company_id.id)],limit=1)
            move_id = account_move.search([('date','=',self.start_date),('journal_id','=',journal_id.id),('state','=','posted'),('company_id','=',self.company_id.id)])
            if move_id.id !=False:
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
            account_id = account_obj.search( [('type','in',account_type)])
            
        if self.partner_id:
            partner_id.append(self.partner_id.id)
        else:
            if self.is_transaction:
                self._cr.execute(""" select aml.partner_id,rp.name, aml.debit,aml.credit as amount from account_move as am left join
                               account_move_line as aml on aml.move_id = am.id left join 
                               res_partner as rp on rp.id=aml.partner_id where aml.partner_id is not null and
                               aml.account_id = %s and am.date >='%s' and am.date <='%s' and 
                               am.state = 'posted'
                               group by aml.partner_id,rp.name,aml.debit,aml.credit order by rp.name asc"""%(account_id,fiscal_id.date_start,self.end_date))
                partner_ids = self._cr.dictfetchall()
                for li in partner_ids:
                    if li['amount'] != 0.0 and li['amount'] !=None or li['debit'] !=0.0 and li['debit']!=None:
                        if li['partner_id'] not in partner_id:
                            partner_id.append(li['partner_id'])
               
            else:
                self._cr.execute(""" select aml.partner_id,rp.name from account_move as am left join
                            account_move_line as aml on aml.move_id = am.id left join 
                            res_partner as rp on rp.id=aml.partner_id where aml.partner_id is not null and
                            am.date >='%s' and am.date <='%s' and aml.account_id=%s and 
                             am.state = 'posted'
                            group by aml.partner_id,rp.name order by rp.name asc"""%
                            (fiscal_id.date_start,self.end_date,account_id))
                parts = self._cr.dictfetchall()
                partner_id = [p['partner_id'] for p in parts]
                

        #print ('OOOOOO', partner_id)
            
        
                    

        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet(u'Харилцагчийн дэвтэр')
        ezxf = xlwt.easyxf
        styles = self.get_easyxf_styles()
        data_style = ezxf('font: bold on; align: wrap on, vert centre, horiz centre; font: height 300;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold = ezxf('font: bold on; align: wrap on, vert centre, horiz centre; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_right = ezxf('font: bold off; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_right_bold = ezxf('font: bold on; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_left = ezxf('font: bold off; align: wrap on, vert centre, horiz left; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_no_border_left = ezxf('font: bold on; align: wrap on, vert centre, horiz left; font: height 200;','#,##0.00_);(#,##0.00)')
        data_bold_left = ezxf('font: bold on; align: wrap on, vert centre, horiz left; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_center = ezxf('font: bold off; align: wrap on, vert centre, horiz center; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_center_no_border = ezxf('font: bold off; align: wrap on, vert centre, horiz center; font: height 200;','#,##0.00_);(#,##0.00)')
        sheet.write(0, 0, u'Байгууллагын нэр: %s' % (company.name,), ezxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 280'))
        sheet.write_merge(1, 1, 0, 6, u'Харилцагчийн дэвтэр', ezxf('font: bold on; align: wrap off, vert centre, horiz centre;font: height 280'))
        sheet.write_merge(2, 2, 0, 6, u'Тайлант хугацаа: %s - %s'%(self.start_date,self.end_date) , ezxf('font:bold off;align:wrap off,vert centre,horiz right;font: height 240'))
        
        
        rowx = 0
        col = 0
        num = 0
        four = 0
        rowx = 4

        account_obj = self.env['account.account']
        move_obj = self.env['account.move']
        pre_balance = False
        journals = self.env['account.journal'].search([])
        journal = []
        for j_ids in journals:
            journal.append(j_ids.id)
        journal_ids = []
        for jr_ids in self.account_journal_ids:
            journal_ids.append(jr_ids.id)
        if self.filter=='filter_date':
            if len(partner_id)==1:
                if len(move_state)==1:
                    move = move_obj.search( [('state','=',move_state[0]),('date','>=',date_start),('date','<=',self.end_date),('journal_id','in',tuple(journal_ids))])
                else:
                    move = move_obj.search( [('state','in',tuple(move_state)),('date','>=',date_start),('date','<=',self.end_date),('journal_id','in',tuple(journal_ids))])
                move_ids = []
                for mv in move:
                    move_ids.append(mv.id)
                account_move_line_id = account_move_line_obj.search( [('move_id','in',tuple(move_ids)),('partner_id','=',partner_id[0]),('account_id','=',self.account_id.id),('date','>',self.start_date),('date','<=',self.end_date)],order="date asc")
                if len(f_journal)==1:
                    self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id 
                                    from account_move_line as ml left join account_move as am on am.id=ml.move_id where 
                                    am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                    and am.journal_id = %s and ml.account_id = %s group by ml.partner_id
                                    """%(fiscal_id.date_start,self.start_date,partner_id[0],f_journal[0],self.account_id.id))
                    pre_balance = self._cr.dictfetchall()
                else:
                    self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id 
                                    from account_move_line as ml left join account_move as am on am.id=ml.move_id where 
                                    am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                    and am.journal_id in %s and ml.account_id = %s group by ml.partner_id
                                    """%(fiscal_id.date_start,self.start_date,
                                                      partner_id[0],
                                                      tuple(f_journal),self.account_id.id))
                    pre_balance = self._cr.dictfetchall()
            else:
                if len(move_state)==1:
                    move = move_obj.search( [('state','=',move_state[0]),('date','>=',date_start),('date','<=',self.end_date),('journal_id','in',tuple(journal_ids))])
                else:
                    move = move_obj.search( [('state','in',tuple(move_state)),('date','>=',date_start),('date','<=',self.end_date),('journal_id','in',tuple(journal_ids))])
                move_ids = []
                for mv in move:
                    move_ids.append(mv.id)
                account_move_line_id = account_move_line_obj.search([('move_id','in',tuple(move_ids)),('partner_id','in',tuple(partner_id)),('account_id','=',self.account_id.id),('date','>',self.start_date),('date','<=',self.end_date)],order="date asc")
                if len(f_journal)==1:
                    self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id from account_move_line as ml 
                                    left join account_move as am on am.id=ml.move_id where 
                                    am.date>= '%s' and am.date<='%s' and ml.partner_id in %s and am.state='posted'
                                    and am.journal_id =  %s and ml.account_id = %s group by ml.partner_id
                                    """%(fiscal_id.date_start,self.start_date,
                                                      tuple(partner_id),
                                                     f_journal[0],self.account_id.id))
                    pre_balance = self._cr.dictfetchall()
                else:
                    if len(partner_id) > 1:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id from account_move_line as ml 
                                        left join account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date<='%s' and ml.partner_id in %s and am.state='posted'
                                        and am.journal_id in  %s and ml.account_id = %s group by ml.partner_id
                                        """%(fiscal_id.date_start,self.start_date,
                                                          tuple(partner_id),
                                                         tuple(f_journal),self.account_id.id))
                        pre_balance = self._cr.dictfetchall()

             
                
        else:
            if len(partner_id)==1:
                if len(move_state)==1:
                    move_id = move_obj.search( [('state','=',move_state[0]),('date','>=',date_start),('date','<=',self.start_date),('journal_id','in',tuple(journal_ids))])
                else:
                    move_id = move_obj.search( [('state','in',tuple(move_state)),('date','>=',date_start),('date','<=',self.start_date),('journal_id','in',tuple(journal_ids))])
                if len(move_state)==1:
                    move = move_obj.search( [('state','=',move_state[0]),('date','>=',date_start),('period_id','<=',self.end_date),('journal_id','in',tuple(journal_ids))])
                else:
                    move = move_obj.search( [('state','in',tuple(move_state)),('date','>=',date_start),('period_id','<=',self.end_date),('journal_id','in',tuple(journal_ids))])
                move_ids = []
                for mv in move:
                    move_ids.append(mv.id)
                account_move_line_id = account_move_line_obj.search( [('move_id','in',tuple(move_ids)),('partner_id','=',partner_id),('account_id','=',self.account_id.id),('date','>',self.start_date),('date','<=',self.end_date)],order="date asc")
                if move_id:
                    if len(f_journal)==1:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id from account_move_line as ml 
                                            left join account_move as am am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                        and ml.move_id in %s and ml.journal_id = %s and ml.account_id = %s group by ml.partner_id
                                        """%(fiscal_id.date_start,self.start_date,
                                                          partner_id[0],tuple(move_id),
                                                          f_journal[0],self.account_id.id))
                        pre_balance = self._cr.dictfetchall()
                    else:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id from account_move_line as ml 
                                        left join account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.partner_id = %s and am.state='posted'
                                        and ml.move_id in %s and ml.journal_id in %s and ml.account_id = %s group by ml.partner_id
                                        """%(fiscal_id.date_start,self.start_date,
                                                          partner_id[0],tuple(move_id),
                                                          tuple(f_journal),self.account_id.id))
                        pre_balance = self._cr.dictfetchall()
            else:
                if len(move_state)==1:
                    move_id = move_obj.search( [('state','=',move_state[0]),('date','>=',date_start),('date','<=',self.start_date),('journal_id','in',tuple(journal_ids))])
                else:
                    move_id = move_obj.search( [('state','in',tuple(move_state)),('date','>=',date_start),('date','<=',self.start_date),('journal_id','in',tuple(journal_ids))])
                if len(move_state)==1:
                    move = move_obj.search( [('state','=',move_state[0]),('date','>=',date_start),('date','<=',self.end_date),('journal_id','in',tuple(journal_ids))])
                else:
                    move = move_obj.search( [('state','in',tuple(move_state)),('date','>=',date_start),('date','<=',self.end_date),('journal_id','in',tuple(journal_ids))])
                move_ids = []
                for mv in move:
                    move_ids.append(mv.id)
                account_move_line_id = account_move_line_obj.search( [('move_id','in',tuple(move_ids)),('partner_id','in',tuple(partner_id)),('account_id','=',self.account_id.id),('date','>',self.start_date),('date','<=',self.end_date)],order="date asc")
                if move_id: 
                    if len(f_journal)==1:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id from account_move_line as ml 
                                        account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.account_id = %s and ml.partner_id in %s 
                                        and ml.move_id in %s and ml.journal_id = %s and ml.account_id = %s and am.state='posted' group by ml.partner_id 
                                        """%(fiscal_id.date_start,self.start_date,
                                                          account_id,tuple(partner_id),tuple(move_id),
                                                          f_journal[0],self.account_id.id))
                        pre_balance = self._cr.dictfetchall()
                    else:
                        self._cr.execute("""select sum(ml.debit-ml.credit) as balance,ml.partner_id from account_move_line as ml left join
                                        account_move as am on am.id=ml.move_id where 
                                        am.date>= '%s' and am.date <='%s' and ml.account_id = %s and ml.partner_id in %s 
                                        and ml.move_id in %s and ml.journal_id in %s and ml.account_id = %s and am.state='posted' group by ml.partner_id 
                                        """%(fiscal_id.date_start,self.start_date,
                                                          account_id,tuple(partner_id),tuple(move_id),
                                                          tuple(f_journal),self.account_id.id))
                        pre_balance = self._cr.dictfetchall()
        
            
        
        invoice_obj = self.env['account.move']
        total_amount = 0
        if partner_id:
            if self.is_extra == True:
                sheet.write_merge(rowx, rowx+1, 0, 0, u'Огноо', styles['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 1, 1, u'Журнал', styles['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 2, 2, u'Сурвалж', styles['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 3, 3, u'Данс', styles['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 4, 4, u'Дебит', styles['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 5, 5, u'Кредит', styles['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 6, 6, u'Үлдэгдэл', styles['heading_xf'])
            else:
                sheet.write_merge(rowx, rowx+1, 0, 0, u'Харилцагчийн нэр', styles['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 1, 1, u'Татвар', styles['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 2, 2, u'Данс', styles['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 3, 3, u'Эхний үлдэгдэл', styles['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 4, 4, u'Дебит', styles['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 5, 5, u'Кредит', styles['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 6, 6, u'Үлдэгдэл', styles['heading_xf'])
            rowx = 6
            for line in partner_obj.browse(partner_id):
                if self.is_extra == True:
                    if pre_balance !=[] and pre_balance !=False or len(account_move_line_id)>=1:
                        pr_balance = 0.0
                        balance = 0.0
                        for li in pre_balance:
                            if li['partner_id'] == line.id:
                                balance += li['balance']
                                pr_balance = li['balance']
                        
                        sheet.write_merge(rowx, rowx, 0, 2, u'%s'%(line.name),data_bold_no_border_left)
                        sheet.write_merge(rowx, rowx, 3, 3, u'%s'%(line.vat),data_bold_no_border_left)
                        sum_debit = 0.0
                        sum_credit = 0.0
                        
                        sheet.write_merge(rowx, rowx, 4, 5, u'Эхний үлдэгдэл',data_bold_no_border_left)
                        sheet.write_merge(rowx, rowx, 6, 6, balance,data_bold_no_border_left)
                        rowx +=1
                        
                        for move in account_move_line_id:
                            ref = ''
                            if line.id == move.partner_id.id:
                                sheet.write(rowx, 0, u'%s'%move.date,data_center)
                                sheet.write(rowx, 1, u'%s'%move.journal_id.name,data_center)
                                invoice_id = invoice_obj.search([('id','=',move.move_id.id),('state','=','posted')])
                                if invoice_id:
                                    invoice = invoice_id
                                    ref = invoice.invoice_origin
                                sheet.write(rowx, 2, u'%s,%s,%s'%(move.name,move.ref,ref),data_center)
                                sheet.write(rowx, 3, u'%s'%(move.account_id.code),data_center)
                                
                                sheet.write(rowx, 4, u'%s'%move.debit,data_right)
                                sheet.write(rowx, 5, u'%s'%move.credit,data_right)
                                if move.debit >0.0:
                                    balance = balance+move.debit
                                    sum_debit +=move.debit
                                else:
                                    balance = balance-move.credit
                                    sum_credit +=move.credit
                                sheet.write(rowx, 6, u'%s'%balance,data_right)
                                rowx +=1
                        
                        sheet.write_merge(rowx, rowx, 0, 3, u'Нийт',data_right_bold)
                        sheet.write_merge(rowx, rowx, 4, 4, sum_debit,data_right_bold)
                        sheet.write(rowx, 5, sum_credit, data_right_bold)
                        sheet.write(rowx, 6, balance, data_right_bold)
                        rowx +=2
                else:
                    sum_debit = 0.0
                    sum_credit = 0.0
                    pr_balance = 0.0
                    balance = 0.0
                    if account_move_line_id:

                        sheet.write_merge(rowx, rowx, 0, 0, u'%s'%(line.name),data_left)
                        sheet.write_merge(rowx, rowx, 1, 1, u'%s'%(line.vat),data_left)
                        if pre_balance !=[] and pre_balance !=False:
                            for li in pre_balance:
                                if li['partner_id'] == line.id:
                                    balance += li['balance']
                                    pr_balance = li['balance']
                        sheet.write_merge(rowx, rowx, 2, 2, u'%s'%(self.account_id.code),data_left)
                        sheet.write_merge(rowx, rowx, 3, 3, balance,data_right)
                        for move in account_move_line_id:
                            if move.partner_id.id == line.id:
                                if move.debit >0.0:
                                    balance = balance+move.debit
                                    sum_debit +=move.debit
                                else:
                                    balance = balance-move.credit
                                    sum_credit +=move.credit
                                    
                        sheet.write(rowx, 4, sum_debit,data_right)
                        sheet.write(rowx, 5, sum_credit,data_right)
                        sheet.write(rowx, 6, balance, data_right)
                        total_amount +=balance
                        rowx +=1   
                    else:
                        if pre_balance !=[] and pre_balance !=False:
                            for li in pre_balance:
                                if li['partner_id'] == line.id:
                                    balance = li['balance']
                                    pr_balance = li['balance']
                            sheet.write_merge(rowx, rowx, 0, 0, u'%s'%(line.name),data_left)
                            sheet.write_merge(rowx, rowx, 1, 1, u'%s'%(line.vat),data_left)
                            sheet.write_merge(rowx, rowx, 2, 2, u'%s %s'%(self.account_id.code,self.account_id.name),data_left)
                            sheet.write_merge(rowx, rowx, 3, 3, balance,data_right)
                            sheet.write(rowx, 4, 0.0,data_right)
                            sheet.write(rowx, 5, 0.0,data_right)
                            sheet.write(rowx, 6, balance, data_right)
                            total_amount +=balance
                            rowx +=1 
        sheet.write_merge(rowx, rowx, 0, 5, u'Нийт',data_bold_left)
        sheet.write_merge(rowx, rowx, 6, 6, total_amount,data_right_bold)
        rowx +=2
        sheet.write_merge(rowx, rowx, 0, 6, u'Дэд захирал:................................./........................../', data_center_no_border)
        sheet.write_merge(rowx+1, rowx+1, 0, 6, u'Нягтлан бодогч:................................/............................../', data_center_no_border)
        
        inch = 1000
        sheet.col(0).width = 4*inch
        sheet.col(1).width = 6*inch
        sheet.col(2).width = 6*inch
        sheet.col(3).width = 4*inch
        sheet.col(4).width = 6*inch
        sheet.col(5).width = 4*inch
        sheet.col(6).width = 4*inch
        sheet.col(7).width = 4*inch
        sheet.row(4).height = 500
        sheet.row(1).height = 500

        
        return {'data':book, 'directory_name':u'Харилцагчийн дэвтэр', 
                'attache_name':u'Харилцагчийн дэвтэр'}


