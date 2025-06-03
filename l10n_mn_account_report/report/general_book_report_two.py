# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import xlwt


class general_book_report(models.TransientModel):
    """
        Ерөнхий дэвтэр тайлан 2
    """
    _name = "general.book.report.two"
    _description = "General book report 2"
    
    
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)
    date_start = fields.Date(string="Start date", required=True, default=fields.Date.context_today)
    date_end = fields.Date(string="End date", required=True, default=fields.Date.context_today)
    fiscalyear_id = fields.Many2one('account.fiscal.year', string='Fiscal year',required=True)
    is_sales = fields.Boolean(string='Sales', default=False)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                     ('all', 'All Entries')
                                    ], string='State', required=True, default='posted')
    account_ids = fields.Many2many('account.account','general_book_report_two_rel','account_id','general_id',
                                   string='Account', required=True)


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
        context= dict(self._context)
        styledict = self.get_easyxf_styles()
        ezxf = xlwt.easyxf
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet(u'Ерөнхий дэвтэр 2')
        date_str = '%s - %s' % (self.date_start,self.date_end)
        states = ''
        if self.target_move =='posted':
            states = ['posted']
        else:
            states = ['posted','draft']
        sheet.write(1, 0, u'Байгууллагын нэр: %s' % self.company_id.name, xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write(1, 2, u'Ерөнхий дэвтэр', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 260'))
        sheet.write(1, 4, u'%s' % date_str, xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))

        rowx = 3
        
        
        data_right = ezxf('font: bold off; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_right = ezxf('font: bold on; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_center = ezxf('font: bold on; align: wrap on, vert centre, horiz centre; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        
        number = 0
        account_obj = self.env['account.account']
        move_line_obj = self.env['account.move.line']
        move_obj = self.env['account.move']
        journal_obj = self.env['account.journal']
        journal_id = journal_obj.search([('type','!=','salary'),('type','!=','opening'),('company_id','=',self.company_id.id)])
        journal_st = journal_obj.search([('type','=','opening'),('company_id','=',self.company_id.id)])
        salary_journal_id = journal_obj.search([('type','=','salary'),('company_id','=',self.company_id.id)])
        
        if len(self.account_ids.ids)==1:
            account_id = account_obj.search([('id','=',self.account_ids.id),('company_id','=',self.company_id.id)])
            
        else:
            account_id = account_obj.search([('id','in',tuple(self.account_ids.ids),('company_id','=',self.company_id.id))])

        
        for line in account_id:
            #ehnii vldegdel oloh - acc = balance
            start_balance = 0.0
            total = 0.0
            total_db = 0.0
            total_cr = 0.0
            total_balance = 0.0
            balance = 0.0
            if len(states)==1:
                if self.fiscalyear_id.date_start == self.date_start:
                    self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                            account_move as am on am.id=aml.move_id
                             where aml.date >= '%s' and aml.date <='%s' and aml.account_id = %s and am.state = '%s' and am.journal_id = %s 
                             """%(self.fiscalyear_id.date_start,self.date_start,line.id,states[0],journal_st.id))
                    acc = self._cr.dictfetchall()
                else:
                    self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                            account_move as am on am.id=aml.move_id
                             where aml.date >= '%s' and aml.date <'%s' and aml.account_id = %s and am.state = '%s' and am.journal_id = %s 
                             """%(self.fiscalyear_id.date_start,self.date_start,line.id,states[0],journal_st.id))
                    acc = self._cr.dictfetchall()
            else:
                if self.fiscalyear_id.date_start == self.date_start:
                    self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                            account_move as am on am.id=aml.move_id
                             where aml.date >= '%s' and aml.date <='%s' and aml.account_id = %s and am.state in %s and am.journal_d = %s
                             """%(self.fiscalyear_id.date_start,self.date_start,line.id,tuple(states),journal_st.id))
                    acc = self._cr.dictfetchall()
                else:
                    self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                            account_move as am on am.id=aml.move_id
                             where aml.date >= '%s' and aml.date <'%s' and aml.account_id = %s and am.state in %s and am.journal_d = %s
                             """%(self.fiscalyear_id.date_start,self.date_start,line.id,tuple(states),journal_st.id))
                    acc = self._cr.dictfetchall()
            if acc[0]:
                if acc[0]['balance'] == None:
                    balance = 0.0
                else:
                    balance = acc[0]['balance']
            
            sheet.write(rowx, 0, '', data_bold_center)
            sheet.write_merge(rowx, rowx, 1, 1, u'Дансны №', data_bold_center)
            sheet.write_merge(rowx, rowx, 2, 2, u'%s %s'%(line.code,line.name), data_bold_center)
            sheet.write_merge(rowx, rowx, 3, 3, u'Эхний үлдэгдэл', data_bold_center)
            sheet.write_merge(rowx, rowx, 4, 4, balance, data_bold_right)
            rowx +=1
            
            #Songoson dansnii bvh ajil gvilgeed duudah - all
            if len(states)==1:
                self._cr.execute("""select am.id from account_move_line AS aml 
                        left join account_move AS am ON am.id = aml.move_id 
                        left join account_journal as aj on aj.id = am.journal_id
                        left join account_account AS aa on aa.id = aml.account_id 
                        WHERE am.date >= '%s' and am.date <='%s' and
                        aml.account_id = %s and am.state = '%s'
                        group by am.id order by am.date asc
                                    """%(self.date_start,self.date_end,line.id,states[0]))
                all = self._cr.dictfetchall()
            else:
                self._cr.execute("""select am.id from account_move_line AS aml 
                        left join account_move AS am ON am.id = aml.move_id 
                        left join account_journal as aj on aj.id = am.journal_id
                        left join account_account AS aa on aa.id = aml.account_id 
                        WHERE am.date >= '%s' and am.date <='%s' and
                        aml.account_id = %s and am.state = '%s'
                        group by am.id order by am.date asc"""%(self.date_start,self.date_end,line.id,states))
                all = self._cr.dictfetchall()
        
            move_ids = []
            accounts = []
            line_data = False
            for i in all:
                move_ids.append(i['id'])
            #Esreg bichiltiin  dansnuudiig oloh - acc_id
            if len(move_ids) == 1:
                self._cr.execute(""" select aml.account_id from account_move as mv
                                              left join account_move_line as aml on aml.move_id = mv.id
                                              where aml.move_id = %s
                                              group by aml.account_id"""%(move_ids[0]))
                acc_id = self._cr.fetchall()
                for ac in acc_id:
                    if ac[0]!=None:
                        accounts.append(ac[0])
            elif len(move_ids) > 1:
                self._cr.execute("""  select aml.account_id from account_move as mv
                                      left join account_move_line as aml on aml.move_id = mv.id
                                      where aml.move_id in """+str(tuple(move_ids))+""" 
                                      group by aml.account_id """)
                acc_id = self._cr.fetchall()
                
                for ac in acc_id:
                    if ac[0]!=None:
                        accounts.append(ac[0])

                
                
            
            
            sheet.write_merge(rowx, rowx+1, 0, 0, u'Д/д', styledict['heading_xf'])
            sheet.write_merge(rowx, rowx+1, 1, 1, u'Харьцсан данс', styledict['heading_xf'])
            sheet.write_merge(rowx, rowx, 2, 3, u'Гүйлгээ', styledict['heading_xf'])
            sheet.write_merge(rowx+1, rowx+1, 2, 2, u'Дебит', styledict['heading_xf'])
            sheet.write_merge(rowx+1, rowx+1, 3, 3, u'Кредит', styledict['heading_xf'])
            sheet.write_merge(rowx, rowx+1, 4, 4, u'Үлдэгдэл', styledict['heading_xf'])
            rowx +=2
            all_debit = []
            all_credit = []
            all_debit_oth = []
            all_credit_oth = []
            all_salary_credit = []
            if len(move_ids) >1:
                if len(states)==1:
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit) from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' and
                                aml.debit > 0.0 and aml.credit = 0.0 and
                                aml.account_id = %s and am.state = '%s'  and am.journal_id in %s  and am.id in %s
                                group by am.id order by am.date asc
                                """%(self.date_start,self.date_end,line.id,states[0],tuple(journal_id.ids),tuple(move_ids)))
                    all_debits = self._cr.fetchall()
                    
                    
                    
                    
                    if all_debits!=[]:
                        all_debit = all_debits
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit) from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and aml.debit = 0.0 and aml.credit > 0.0 and
                                aml.account_id = %s and am.state = '%s'  and am.journal_id in %s  and am.id in %s
                                group by am.id order by am.date asc
                                """%(self.date_start,self.date_end,line.id,states[0],tuple(journal_id.ids),tuple(move_ids)))
                    all_credits = self._cr.fetchall()
                    if all_credits!=[]:
                        all_credit = all_credits
                    self._cr.execute("""select aml.account_id,sum(aml.debit) as amount,am.date,aml.partner_id,am.name,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and am.state = '%s'  and am.journal_id in %s  and am.id in %s and aml.debit >0.0
                                group by am.date,aml.partner_id,am.name,aml.account_id,am.id order by amount desc
                                """%(self.date_start,self.date_end,states[0],tuple(journal_id.ids),tuple(move_ids)))
                    all_debit_oths = self._cr.fetchall()
                    if all_debit_oths!=[]:
                        all_debit_oth = all_debit_oths
                    self._cr.execute("""select aml.account_id,sum(aml.credit) as amount,am.date,aml.partner_id,am.name,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and am.state = '%s'  and am.journal_id in %s  and am.id in %s and aml.credit >0.0
                                group by am.date,aml.partner_id,am.name,aml.account_id, am.id order by amount desc
                                """%(self.date_start,self.date_end,states[0],tuple(journal_id.ids),tuple(move_ids)))
                    all_credit_oths = self._cr.fetchall()
                    if all_credit_oths !=[]:
                        all_credit_oth = all_credit_oths
                else:
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit)  from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and aml.debit > 0.0 and aml.credit = 0.0 and
                                aml.account_id = %s and am.state in %s  and am.journal_id in %s  and am.id = %s
                                group by am.id order by am.date asc
                                """%(self.date_start,self.date_end,line.id,tuple(states),tuple(journal_id.ids),mv))
                    all_debits = self._cr.fetchall()
                    if all_debits!=[]:
                        all_debit.append(all_debits[0])
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit)  from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and aml.debit = 0.0 and aml.credit > 0.0 and
                                aml.account_id = %s and am.state in %s  and am.journal_id in %s  and am.id = %s
                                group by am.id order by am.date asc"""%(self.date_start,self.date_end,line.id,tuple(states),tuple(journal_id.ids),mv))
                    all_credits = self._cr.fetchall()
                    if all_credits!=[]:
                        all_credit.append(all_credits[0])
                    self._cr.execute("""select aml.account_id,aml.debit,aml.credit,am.date,aml.partner_id,am.name ,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s'  
                                and am.state in %s and am.journal_id in %s and am.id = %s
                                group by am.date,aml.partner_id,am.name,aml.account_id,am.id,aml.debit,aml.credit order by am.date asc
                                """%(self.date_start,self.date_end,tuple(states),tuple(journal_id.ids),mv))
                    all_debit_oths = self._cr.fetchall()
                    if all_debit_oths!=[]:
                        all_debit_oth.append(all_debit_oths[0])
                    self._cr.execute("""select aml.account_id,aml.debit, aml.credit,am.date,aml.partner_id,am.name,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                 and am.state in %s and am.journal_id in %s and am.id = %s
                                group by am.date,aml.partner_id,am.name,aml.account_id,am.id,aml.debit,aml.credit order by am.date asc
                                """%(self.date_start,self.date_end,tuple(states),tuple(journal_id.ids),mv))
                    all_credit_oths = self._cr.fetchall()
                    if all_credit_oths!=[]:
                        all_credit_oth.append(all_credit_oths[0])
            elif len(move_ids)==1:
                if len(states)==1:
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit) from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' and
                                aml.debit > 0.0 and aml.credit = 0.0 and
                                aml.account_id = %s and am.state = '%s'  and am.journal_id in %s  and am.id = %s
                                group by am.id order by am.date asc
                                """%(self.date_start,self.date_end,line.id,states[0],tuple(journal_id.ids),move_ids[0]))
                    all_debits = self._cr.fetchall()
                    if all_debits!=[]:
                        all_debit = all_debits
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit) from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and aml.debit = 0.0 and aml.credit > 0.0 and
                                aml.account_id = %s and am.state = '%s'  and am.journal_id in %s  and am.id = %s
                                group by am.id order by am.date asc
                                """%(self.date_start,self.date_end,line.id,states[0],tuple(journal_id.ids),move_ids[0]))
                    all_credits = self._cr.fetchall()
                    if all_credits!=[]:
                        all_credit = all_credits
                    self._cr.execute("""select aml.account_id,sum(aml.debit) as amount,am.date,aml.partner_id,am.name,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and am.state = '%s'  and am.journal_id in %s  and am.id = %s and aml.debit >0.0
                                group by am.date,aml.partner_id,am.name,aml.account_id,am.id order by amount desc
                                """%(self.date_start,self.date_end,states[0],tuple(journal_id.ids),move_ids[0]))
                    all_debit_oths = self._cr.fetchall()
                    if all_debit_oths!=[]:
                        all_debit_oth = all_debit_oths
                    self._cr.execute("""select aml.account_id,sum(aml.credit) as amount,am.date,aml.partner_id,am.name,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and am.state = '%s'  and am.journal_id in %s  and am.id = %s and aml.credit >0.0
                                group by am.date,aml.partner_id,am.name,aml.account_id, am.id order by amount desc
                                """%(self.date_start,self.date_end,states[0],tuple(journal_id.ids),move_ids[0]))
                    all_credit_oths = self._cr.fetchall()
                    if all_credit_oths !=[]:
                        all_credit_oth = all_credit_oths
                
            if line.user_type_id.internal_group == 'expense':
                self._cr.execute(""" 
                                SELECT l2.id, l.date, m.name, l.debit, l.credit,a.code
                               FROM account_move_line l 
                               INNER JOIN account_move_line l2 on l2.move_id = l.move_id
                               INNER JOIN account_move m on m.id=l2.move_id
                               INNER JOIN account_account a on l2.account_id = a.id
                               and l2.id <> l.id and l2.account_id <> l.account_id and l.debit = l2.credit
                               and l.name = l2.name
                               and l.debit >0.0
                               and l.credit =0.0
                               AND m.date >= '%s' AND m.date <= '%s'
                               AND m.state='%s'
                               AND l.company_id = %s
                               AND l.account_id = %s 
                               AND l.journal_id = %s
                               group by l2.id, l.date, l.debit, a.code, l.credit, m.name
                                """%(self.date_start, self.date_end, states[0], self.company_id.id, line.id,salary_journal_id.id))
                all_salary_credits = self._cr.fetchall()
                
                
                if all_salary_credits!=[]:
                    all_salary_credit = all_salary_credits
                
            else:
                
                self._cr.execute(""" 
                                SELECT l2.id, l.date, m.name, l.debit, l.credit, a.code
                               FROM account_move_line l 
                               INNER JOIN account_move_line l2 on l2.move_id = l.move_id
                               INNER JOIN account_move m on m.id=l2.move_id
                               INNER JOIN account_account a on l2.account_id = a.id
                               and l2.id <> l.id and l2.account_id <> l.account_id and l.debit = l2.credit
                               and l.name = l2.name
                               AND m.date >= '%s' AND m.date <= '%s'
                               AND m.state='%s'
                               AND l.company_id = %s
                               AND l.account_id = %s 
                               AND m.journal_id = %s
                               group by l2.id, l.date, l.debit, a.code, l.credit, m.name
                                """%(self.date_start, self.date_end, states[0], self.company_id.id, line.id,salary_journal_id.id))
                all_salary_credits = self._cr.fetchall()
                
                
                if all_salary_credits!=[]:
                    all_salary_credit = all_salary_credits
                
            for acc_ids in account_obj.browse(accounts):
                debitn = 0.0
                creditn = 0.0
                number += 1
                count = 1
                if all_salary_credit!=[]:
                    tcbalance = 0.0
                    cibalance = 0.0
                    for sl in all_salary_credit:
                        acc = sl[5].split(',')
                        accs = []
                        
                        account = account_obj.search([('code','=',acc[0])],limit=1)
                        accs.append(account.code)
                            

                            
                        
                        if  acc_ids.code in accs:
                            tcbalance +=round(sl[4],2)
                            debitn +=round(sl[4],2)
                            balance -=round(sl[4],2)
                            
                            creditn +=round(sl[3], 2)
                            cibalance +=round(sl[3], 2)
                            balance +=round(sl[3], 2)
                            
                            
                            
                                
                            
                
                #print("aaaaaaaaaaaaaaaaaa",all_salary_credit)
                if all_credit!=[]:
                    for cli in all_credit:
                        tcbalance = round(cli[2],2)
                        count = 1
                        
                        for ci in all_debit_oth:
                            if cli[0] == ci[5]:
                                cibalance = 0.0
                                if ci[1] <=cli[2] and ci[0]!=line.id and round(tcbalance,2)>0.0:
                                    if round(tcbalance,2) > ci[1]:
                                        tcbalance -=round(ci[1],2)
                                        cibalance = ci[1]
                                    else:
                                        if cibalance==0.0:
                                            cibalance = round(tcbalance,2)
                                            tcbalance -=round(tcbalance,2)
                                    
                                elif ci[0]==line.id and ci[1] <=cli[2] and round(tcbalance,2)>0.0:
                                    if round(tcbalance,2) > ci[1]:
                                        cibalance = ci[1]
                                        tcbalance -=round(ci[1],2)
                                    else:
                                        cibalance = round(tcbalance,2)
                                        tcbalance -=round(tcbalance,2)
                                        
                                elif ci[0]==line.id and ci[1] >cli[2]:
                                    if count==1:
                                        if tcbalance >=cli[2]:
                                            cibalance = cli[2]
                                            tcbalance -=round(cli[2],2)
                                            count +=1
                                        else:
                                            cibalance = tcbalance
                                            tcbalance -=round(tcbalance,2)
                                            count +=1
                                    
                                elif ci[1] > cli[2] and line.id!=ci[0]:
                                    if count==1:
                                        cibalance = cli[2]
                                        tcbalance -=round(cli[2],2)
                                        count +=1
                               
                                if ci[1] > 0.0  and ci[0]==acc_ids.id:
                                    if cibalance !=0.0:
                                        debitn +=cibalance
                                        balance -=cibalance

                                   
                if all_debit!=[]:
                    for li in all_debit:
                        tbalance = round(li[1],2)
                        count = 1
                        for i in all_credit_oth:
                            if i[5]==li[0]:
                                ibalance = 0.0
                                if i[1] <=li[1] and i[0]!=line.id and round(tbalance,2)!=0.0:
                                    if round(tbalance,2) >= i[1]:
                                        tbalance -=round(i[1],2)
                                        ibalance = i[1]
                                    else:
                                        if ibalance == 0.0:
                                            
                                            ibalance = round(tbalance,2)
                                            tbalance -=round(tbalance,2)
                                        
                                elif i[0]==line.id and i[1] >li[1]:
                                    if count==1:
                                        ibalance = li[1]
                                        tbalance -=round(li[1],2)
                                        count +=1
                                        
                                elif i[0]==line.id and i[1] <=li[1] and round(tbalance,2)!=0.0:
                                        if tbalance >=i[1]:
                                            ibalance = i[1]
                                            tbalance -=round(i[1],2)
                                        else:
                                            ibalance = tbalance
                                            tbalance -=round(tbalance,2)
                                    
                                elif i[1] > li[1] and i[0]!=line.id:
                                    if count==1:
                                        tbalance -=round(li[1],2)
                                        ibalance = li[1]
                                        count +=1
                                        
                                if i[1] >0.0 and i[0]==acc_ids.id:
                                    if ibalance !=0.0:
                                        creditn +=ibalance
                                        balance +=ibalance

                        

                if creditn > 0.0 or debitn > 0.0:
                    sheet.write(rowx, 0, number, styledict['text_xf'])
                    sheet.write(rowx, 1, u'%s %s'%(acc_ids.code,acc_ids.name), styledict['text_xf'])
                    sheet.write(rowx, 2, creditn, data_right)
                    sheet.write(rowx, 3, debitn, data_right)
                    sheet.write(rowx, 4, balance, data_right)
                    total_db +=debitn
                    total_cr +=creditn
                    total_balance = balance
                    rowx += 1
            sheet.write_merge(rowx, rowx, 0, 1, u'НИЙТ', data_right)
            sheet.write(rowx, 2, total_cr, data_right)
            sheet.write(rowx, 3, total_db, data_right)
            sheet.write(rowx, 4, total_balance, data_right)
            
            rowx += 3
                                
        inch = 1000
        sheet.col(0).width = 2 * inch
        sheet.col(1).width = 10 * inch
        sheet.col(2).width = 11 * inch
        sheet.col(3).width = 9 * inch
        sheet.col(4).width = 4 * inch
        sheet.col(5).width = 4 * inch
        sheet.col(6).width = 4 * inch
        sheet.col(7).width = 4 * inch
        sheet.col(8).width = 4 * inch
        sheet.col(9).width = 4 * inch
        sheet.row(4).height = 640
        
        
        
        sheet.write(rowx + 2, 1, u"Зөвшөөрсөн: ..................................................../                                            /",
                    xlwt.easyxf('font:bold off;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write(rowx + 4, 1, u"Хөтөлсөн ня-бо: ..................................................../                                           /",
                    xlwt.easyxf('font:bold off;align:wrap off,vert centre,horiz left;font: height 180'))
        
        return {'data':book, 'directory_name':u"Ерөнхий дэвтэр 2",
                'attache_name':"Ерөнхий дэвтэр 2"}
        

    