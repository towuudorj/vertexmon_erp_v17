# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta, datetime
import xlwt

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

class general_journal_report_two(models.TransientModel):
    """
        Ерөнхий журнал тайлан 2
    """
    _name = "general.journal.report.two"
    _description = "General journal report 2"
    
    
    company_id = fields.Many2one('res.company', string='Company', readonly=True, 
                                 default=lambda self: self.env.user.company_id)
    date_start = fields.Date(string="Start date", required=True, default=fields.Date.context_today)
    date_end = fields.Date(string="End date", required=True, default=fields.Date.context_today)
    fiscalyear_id = fields.Many2one('account.fiscal.year', string='Fiscal year', required=True)
    is_sales = fields.Boolean(string='Sale')
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                     ('all', 'All Entries')
                                    ], string='State', required=True, default='posted')
    account_ids = fields.Many2many('account.account', 'general_journal_report_two_rel', 'account_id', 'general_id', 
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
        sheet = book.add_sheet(u'Ерөнхий журнал')
        
        date_str = '%s - %s' % (self.date_start,self.date_end)

         
        sheet.write(4, 0, u'Байгууллагын нэр: %s' % self.company_id.name, xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 220'))
        sheet.write(4, 8, u'%s' % date_str, xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        sheet.write_merge(3, 3, 1, 8, u'ЕРӨНХИЙ ЖУРНАЛ', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz center;font: height 240'))
        sheet.write(0, 8, u'Сангийн сайдын 2018 оны', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        sheet.write(1, 8, u'өдрийн 100 дугаар тушаалын хавсралт', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        rowx = 6
        
        sheet.write_merge(rowx, rowx+1, 0, 0, u'Д/д', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx, 1, 2, u'Баримтын', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 1, 1, u'Он сар', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 2, 2, u'Дугаар', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 3, 3, u'Гүйлгээний утга', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 4, 4, u'Харилцагч', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 5, 5, u'Дансны нэр,код', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx, 6, 8, u'Дүн', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 6, 6, u'Дебит', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 7, 7, u'Кредит', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 8, 8, u'Үлдэгдэл', styledict['heading_xf'])
        
        data_right = ezxf('font: bold off; align: wrap on, vert centre, horiz right; font: height 180;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_right = ezxf('font: bold on; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        states = ''
        if self.target_move =='posted':
            states = ['posted']
        else:
            states = ['posted','draft']
        rowx = 8
        number = 1
        account_obj = self.env['account.account']
        move_line_obj = self.env['account.move.line']
        move_obj = self.env['account.move']
        partner_obj = self.env['res.partner']
        journal_id = self.env['account.journal'].search([('type','=','opening'),('company_id','=',self.company_id.id)])
        ojournal_id = self.env['account.journal'].search([('type','!=','opening'),('type','!=','salary'),('company_id','=',self.company_id.id)])
        salary_journal_id = self.env['account.journal'].search([('type','=','salary'),('company_id','=',self.company_id.id)])
        start_balance = 0.0
        total = 0.0
        
        
        if len(self.account_ids)==1:
            account_id = account_obj.search([('id','=',self.account_ids.id),('company_id','=',self.company_id.id)])
        else:
            account_id = account_obj.search( [('id','in',tuple(self.account_ids.ids)),('company_id','=',self.company_id.id)])
        for line in account_id:
            balance = 0.0
            total_debit = 0.0
            total_credit = 0.0
            if len(states)==1:
                if self.fiscalyear_id.date_start == self.date_start:
                    self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                            account_move as am on am.id=aml.move_id
                             where aml.date >= '%s' and aml.date <='%s' and aml.account_id = %s and am.state = '%s' and am.journal_id = %s 
                             """%(self.fiscalyear_id.date_start,self.date_start,line.id,states[0],journal_id.id))
                    acc = self._cr.dictfetchall()
                else:
                    self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                            account_move as am on am.id=aml.move_id
                             where aml.date >= '%s' and aml.date <'%s' and aml.account_id = %s and am.state = '%s' and am.journal_id = %s 
                             """%(self.fiscalyear_id.date_start,self.date_start,line.id,states[0],journal_id.id))
                    acc = self._cr.dictfetchall()
            else:
                if self.fiscalyear_id.date_start == self.date_start:
                    self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                            account_move as am on am.id=aml.move_id
                             where aml.date >= '%s' and aml.date <='%s' and aml.account_id = %s and am.state in %s and am.journal_d = %s
                             """%(self.fiscalyear_id.date_start,self.date_start,line.id,tuple(states),journal_id.id))
                    acc = self._cr.dictfetchall()
                else:
                    self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                            account_move as am on am.id=aml.move_id
                             where aml.date >= '%s' and aml.date <'%s' and aml.account_id = %s and am.state in %s and am.journal_d = %s
                             """%(self.fiscalyear_id.date_start,self.date_start,line.id,tuple(states),journal_id.id))
                    acc = self._cr.dictfetchall()
            if acc[0]:
                if acc[0]['balance'] == None:
                    balance = 0.0
                else:
                    balance = acc[0]['balance']
            sheet.write_merge(rowx, rowx, 0, 1, u'Дансны №', styledict['heading_xf'])
            sheet.write_merge(rowx, rowx, 2, 2, u'%s %s'%(line.code,line.name), styledict['heading_xf'])
            sheet.write_merge(rowx, rowx, 3, 4, u'Эхний үлдэгдэл', styledict['heading_xf'])
            sheet.write_merge(rowx, rowx, 8, 8, balance, data_bold_right)
            rowx +=1
            
            self._cr.execute("""select am.id from account_move_line AS aml 
                        left join account_move AS am ON am.id = aml.move_id 
                        left join account_journal as aj on aj.id = am.journal_id
                        left join account_account AS aa on aa.id = aml.account_id 
                        WHERE am.date >= '%s' and am.date <='%s' and
                        aml.account_id = %s and am.state = '%s'
                        group by am.id order by am.date asc
                        """%(self.date_start,self.date_end,line.id,states[0]))
            move_line_ids = self._cr.fetchall()
        
            move_id = []
            for ml in move_line_ids:
                move_id.append(ml[0])
                
            
            accounts = []
                
            account_obj = self.env['account.account']
            #Esreg bichiltiin  dansnuudiig oloh - acc_id
            if len(move_id) == 1:
                self._cr.execute(""" select aml.account_id from account_move as mv
                                              left join account_move_line as aml on aml.move_id = mv.id
                                              where aml.move_id = %s and aml.account_id != %s
                                              group by aml.account_id"""%(move_id[0],line.id))
                acc_id = self._cr.fetchall()
                for ac in acc_id:
                    if ac[0]!=None:
                        acc_ids = account_obj.search([('id','=',ac[0])])
                        if acc_ids.code not in accounts:
                            accounts.append(acc_ids.code)
            elif len(move_id) > 1:
                self._cr.execute("""  select aml.account_id from account_move as mv
                                      left join account_move_line as aml on aml.move_id = mv.id
                                      where aml.move_id in """+str(tuple(move_id))+"""  and aml.account_id != """+str(line.id)+"""
                                      group by aml.account_id """)
                acc_id = self._cr.fetchall()
                
                for ac in acc_id:
                    if ac[0]!=None:
                        acc_ids = account_obj.search([('id','=',ac[0])])
                        if acc_ids.code not in accounts:
                            accounts.append(acc_ids.code)
            
                
                
            
            debitn = 0.0
            creditn = 0.0
            data_dict = []
            all_salary_credit = []
            all_credit = False
            all_debit = False
            if len(move_id) >1:
                if len(states)==1:
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit), aml.account_id   from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' and
                                aml.debit > 0.0 and aml.credit = 0.0 and
                                aml.account_id = %s and am.state = '%s'  and am.journal_id in %s  and am.id in %s
                                group by am.id, aml.account_id  order by am.date asc
                                """%(self.date_start,self.date_end,line.id,states[0],tuple(ojournal_id.ids),tuple(move_id)))
                    all_debit = self._cr.fetchall()
                    
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit), aml.account_id   from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and aml.debit = 0.0 and aml.credit > 0.0 and
                                aml.account_id = %s and am.state = '%s'  and am.journal_id in %s  and am.id in %s
                                group by am.id, aml.account_id   order by am.date asc
                                """%(self.date_start,self.date_end,line.id,states[0],tuple(ojournal_id.ids),tuple(move_id)))
                    all_credit = self._cr.fetchall()
                    
                    self._cr.execute("""select aml.account_id,sum(aml.debit) as amount,am.date,aml.partner_id,am.name,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and am.state = '%s'  and am.journal_id in %s  and am.id in %s and aml.debit >0.0
                                group by am.date,aml.partner_id,am.name,aml.account_id,am.id order by amount desc
                                """%(self.date_start,self.date_end,states[0],tuple(ojournal_id.ids),tuple(move_id)))
                    all_debit_oth = self._cr.fetchall()
                    
                    self._cr.execute("""select aml.account_id,sum(aml.credit) as amount,am.date,aml.partner_id,am.name,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and am.state = '%s'  and am.journal_id in %s  and am.id in %s and aml.credit >0.0
                                group by am.date,aml.partner_id,am.name,aml.account_id, am.id order by amount desc
                                """%(self.date_start,self.date_end,states[0],tuple(ojournal_id.ids),tuple(move_id)))
                    all_credit_oth = self._cr.fetchall()
                else:
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit), aml.account_id    from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and aml.debit > 0.0 and aml.credit = 0.0 and
                                aml.account_id = %s and am.state in %s  and am.journal_id in %s  and am.id in %s
                                group by am.id, aml.account_id   order by am.date asc"""%(self.date_start,self.date_end,line.id,tuple(states),tuple(ojournal_id.ids),tuple(move_id)))
                    all_debit = self._cr.fetchall()
                    
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit), aml.account_id    from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and aml.debit = 0.0 and aml.credit > 0.0 and
                                aml.account_id = %s and am.state in %s  and am.journal_id in %s  and am.id in %s
                                group by am.id, aml.account_id   order by am.date asc"""%(self.date_start,self.date_end,line.id,tuple(states),tuple(ojournal_id.ids),tuple(move_id)))
                    all_credit = self._cr.fetchall()
                    
                    self._cr.execute("""select aml.account_id,aml.debit,aml.credit,am.date,aml.partner_id,am.name ,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s'  
                                and am.state in %s and am.journal_id in %s and am.id in %s
                                group by am.date,aml.partner_id,am.name,aml.account_id,am.id,aml.debit,aml.credit order by am.date asc
                                """%(self.date_start,self.date_end,tuple(states),tuple(ojournal_id.ids),tuple(move_id)))
                    all_debit_oth = self._cr.fetchall()
                    
                    self._cr.execute("""select aml.account_id,aml.debit, aml.credit,am.date,aml.partner_id,am.name,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                 and am.state in %s and am.journal_id in %s and am.id in %s
                                group by am.date,aml.partner_id,am.name,aml.account_id,am.id,aml.debit,aml.credit order by am.date asc
                                """%(self.date_start,self.date_end,tuple(states),tuple(ojournal_id.ids),tuple(move_id)))
                    all_credit_oth = self._cr.fetchall()
            elif len(move_id)==1:
                if len(states)==1:
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit), aml.account_id   from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' and
                                aml.debit > 0.0 and aml.credit = 0.0 and
                                aml.account_id = %s and am.state = '%s'  and am.journal_id in %s  and am.id = %s
                                group by am.id, aml.account_id   order by am.date asc
                                """%(self.date_start,self.date_end,line.id,states[0],tuple(ojournal_id.ids),move_id[0]))
                    all_debit = self._cr.fetchall()
                    
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit), aml.account_id   from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and aml.debit = 0.0 and aml.credit > 0.0 and
                                aml.account_id = %s and am.state = '%s'  and am.journal_id in %s  and am.id = %s
                                group by am.id, aml.account_id   order by am.date asc
                                """%(self.date_start,self.date_end,line.id,states[0],tuple(ojournal_id.ids),move_id[0]))
                    all_credit = self._cr.fetchall()
                    
                    self._cr.execute("""select aml.account_id,sum(aml.debit) as amount,am.date,aml.partner_id,am.name,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and am.state = '%s'  and am.journal_id in %s  and am.id = %s and aml.debit >0.0
                                group by am.date,aml.partner_id,am.name,aml.account_id,am.id order by amount desc
                                """%(self.date_start,self.date_end,states[0],tuple(ojournal_id.ids),move_id[0]))
                    all_debit_oth = self._cr.fetchall()
                    
                    self._cr.execute("""select aml.account_id,sum(aml.credit) as amount,am.date,aml.partner_id,am.name,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and am.state = '%s'  and am.journal_id in %s  and am.id = %s and aml.credit >0.0
                                group by am.date,aml.partner_id,am.name,aml.account_id, am.id order by amount desc
                                """%(self.date_start,self.date_end,states[0],tuple(ojournal_id.ids),move_id[0]))
                    all_credit_oth = self._cr.fetchall()
                else:
                    self._cr.execute("""select am.id,sum(aml.debit), sum(aml.credit), aml.account_id  from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and aml.debit > 0.0 and aml.credit = 0.0 and
                                aml.account_id = %s and am.state in %s  and am.journal_id in %s  and am.id = %s
                                group by am.id, aml.account_id   order by am.date asc"""%(self.date_start,self.date_end,line.id,tuple(states),tuple(ojournal_id.ids),move_id[0]))
                    all_debit = self._cr.fetchall()
                    
                    self._cr.execute("""select am.id, sum(aml.debit), sum(aml.credit), aml.account_id  from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                and aml.debit = 0.0 and aml.credit > 0.0 and
                                aml.account_id = %s and am.state in %s  and am.journal_id in %s  and am.id = %s
                                group by am.id, aml.account_id order by am.date asc"""%(self.date_start,self.date_end,line.id,tuple(states),tuple(ojournal_id.ids),move_id[0]))
                    all_credit = self._cr.fetchall()
                    
                    self._cr.execute("""select aml.account_id,aml.debit,aml.credit,am.date,aml.partner_id,am.name ,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s'  
                                and am.state in %s and am.journal_id in %s and am.id = %s
                                group by am.date,aml.partner_id,am.name,aml.account_id,am.id,aml.debit,aml.credit order by am.date asc
                                """%(self.date_start,self.date_end,tuple(states),tuple(ojournal_id.ids),move_id[0]))
                    all_debit_oth = self._cr.fetchall()
                    
                    self._cr.execute("""select aml.account_id,aml.debit, aml.credit,am.date,aml.partner_id,am.name,am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' 
                                 and am.state in %s and am.journal_id in %s and am.id = %s
                                group by am.date,aml.partner_id,am.name,aml.account_id,am.id,aml.debit,aml.credit order by am.date asc
                                """%(self.date_start,self.date_end,tuple(states),tuple(ojournal_id.ids),move_id[0]))
                    all_credit_oth = self._cr.fetchall()
            days = []
            idate = datetime.strptime(str(self.date_start),DATE_FORMAT)
            while idate <= datetime.strptime(str(self.date_end),DATE_FORMAT):
                days.append(idate)
                idate += timedelta(days = 1)
                
            
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
                    
                #===============================================================
                # self._cr.execute("""
                #                 SELECT l.id, l.date, m.name, l.name||(case when m.narration is not null then m.narration else '' end), 
                #                (case when l.amount_currency <> 0 and l.amount_currency is not null then abs(l.credit - l.debit) / l.amount_currency else 0 end), 
                #                coalesce(l.amount_currency,0), l.currency_id, coalesce(l.debit, 0), coalesce(l.credit,0), 
                #                (select array_to_string(array(select (case when l2.debit > 0 then '' else '' end)||a2.code 
                #                    from account_move_line l2 join account_account a2 on l2.account_id = a2.id where l2.move_id = l.move_id 
                #                    and l2.id <> l.id and l2.account_id <> l.account_id and l2.debit=l.credit), ', '))
                #                FROM account_move_line l 
                #                JOIN account_move m ON l.move_id = m.id 
                #                JOIN account_account a ON l.account_id = a.id 
                #                AND m.date >= '%s' AND m.date <= '%s'
                #                AND m.state='%s'
                #                AND l.company_id = %s
                #                AND l.account_id = %s 
                #                AND l.journal_id = %s
                #                ORDER BY l.credit, m.name, m.date, m.ref
                #                 """%(self.date_start, self.date_end, states[0], self.company_id.id, line.id,salary_journal_id.id))
                # all_salary_credits = self._cr.fetchall()
                # 
                # 
                # if all_salary_credits!=[]:
                #     all_salary_credit = all_salary_credits
                #===============================================================
                
            
            for ndate in days:
                if all_salary_credit!=[]:
                    tcbalance = 0.0
                    cibalance = 0.0
                    count = 1
                    for sl in all_salary_credit:
                        
                        if sl[1] == ndate.date():
                            acc = sl[5].split(',')
                            
                            #for aaa in accounts:

                            tcbalance +=round(sl[4],2)
                            debitn +=round(sl[4],2)
                            balance -=round(sl[4],2)
                            
                            creditn +=round(sl[3], 2)
                            cibalance +=round(sl[3], 2)
                            balance +=round(sl[3], 2)
                            
                            #for new_acc in acc:
                            #    if new_acc==aaa:
                            
                            account = account_obj.search([('code','=',acc[0])],limit=1,order='id desc')
                            sheet.write(rowx, 0, number, styledict['text_xf'])
                            sheet.write(rowx, 1, '%s'%sl[1], styledict['text_xf'])
                            sheet.write(rowx, 2, '%s'%sl[2], styledict['text_xf'])
                            sheet.write(rowx, 3, '', styledict['text_xf'])
                            sheet.write(rowx, 4, account.name, styledict['text_xf'])
                            sheet.write(rowx, 5, account.code, styledict['text_xf'])
                            sheet.write(rowx, 6, sl[3], data_right)
                            sheet.write(rowx, 7, sl[4], data_right)
                            sheet.write(rowx, 8, balance, data_right)
                            rowx += 1
                            number +=1
                            
                            
                
                if all_credit !=False:
                    for cli in all_credit:
                        tcbalance = round(cli[2],2)
                        count = 1
                        for ci in all_debit_oth:
                            if cli[0] == ci[5] and ndate.date() == ci[2]:
                                cibalance = 0.0
                                 
                                #print("credit amount",ci[1],cli[2],cibalance,round(tcbalance,2),ci[0],line.id)
                                if ci[1] <=cli[2] and ci[0]!=line.id and round(tcbalance,2) > 0.0:
                                    if round(tcbalance,2) > ci[1]:
                                        tcbalance -=round(ci[1],2)
                                        cibalance = ci[1]
                                    else:
                                        if cibalance==0.0:
                                            cibalance = round(tcbalance,2)
                                            tcbalance -=round(tcbalance,2)
                                     
                                elif ci[0] == line.id and ci[1] <=cli[2] and round(tcbalance,2)>0.0:
                                     if round(tcbalance,2) > ci[1]:
                                        cibalance = ci[1]
                                        tcbalance -=round(ci[1],2)
                                     else:
                                        cibalance = tcbalance
                                        tcbalance -=round(tcbalance,2)
                                         
                                elif ci[0] == line.id and ci[1] >cli[2]:
                                    if count==1:
                                        if round(tcbalance,2) >cli[2]:
                                            cibalance = cli[2]
                                            tcbalance -=round(cli[2],2)
                                            count +=1
                                        else:
                                            cibalance = round(tcbalance,2)
                                            tcbalance -=round(tcbalance,2)
                                            count +=1
                                     
                                elif ci[1] > cli[2] and line.id!=ci[0]:
                                    if count==1:
                                        cibalance = cli[2]
                                        tcbalance -=round(cli[2],2)
                                        count +=1
                                         
                                if ci[1] > 0.0:
                                    if cibalance !=0.0:
                                        debitn +=cibalance
                                        balance -=cibalance
                                        account = account_obj.browse(ci[0])
                                        partner = ''
                                        if ci[4]!=None:
                                            partner = partner_obj.browse(ci[3]).name
                                        sheet.write(rowx, 0, number, styledict['text_xf'])
                                        sheet.write(rowx, 1, '%s'%ci[2], styledict['text_xf'])
                                        sheet.write(rowx, 2, '%s'%ci[4], styledict['text_xf'])
                                        sheet.write(rowx, 3, partner, styledict['text_xf'])
                                        sheet.write(rowx, 4, account.name, styledict['text_xf'])
                                        sheet.write(rowx, 5, account.code, styledict['text_xf'])
                                        sheet.write(rowx, 6, 0, data_right)
                                        sheet.write(rowx, 7, cibalance, data_right)
                                        sheet.write(rowx, 8, balance, data_right)
                                        rowx += 1
                                        number +=1
                                    
                if all_debit !=False:
                    for li in all_debit:
                        tbalance = round(li[1],2)
                        count = 1
                        for i in all_credit_oth:
                            if i[5]==li[0] and ndate.date()==i[2]:
                                ibalance = 0.0
                                #print("debit amount",i[1],li[1],tbalance,ibalance)
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
                                    #if count==1:
                                        if round(tbalance,2) >=i[1]:
                                            ibalance = i[1]
                                            tbalance -=round(i[1],2)
                                            #count +=1
                                        else:
                                            ibalance = round(tbalance,2)
                                            tbalance -=round(tbalance,2)
                                            #count +=1
                                     
                                elif i[1] > li[1] and i[0]!=line.id:
                                     
                                    if count==1:
                                        tbalance -=round(li[1],2)
                                        ibalance = li[1]
                                        count +=1
                                 
                                 
                                if i[1] >0.0:
                                    if ibalance !=0.0:
                                        creditn +=ibalance
                                        balance +=ibalance
                                        account = account_obj.browse(i[0])
                                        partner = ''
                                        if i[3]!=None:
                                            partner = partner_obj.browse(i[3]).name
                                        sheet.write(rowx, 0, number, styledict['text_xf'])
                                        sheet.write(rowx, 1, '%s'%i[2], styledict['text_xf'])
                                        sheet.write(rowx, 2, '%s'%i[4], styledict['text_xf'])
                                        sheet.write(rowx, 3, partner, styledict['text_xf'])
                                        sheet.write(rowx, 4, account.name, styledict['text_xf'])
                                        sheet.write(rowx, 5, account.code, styledict['text_xf'])
                                        sheet.write(rowx, 6, ibalance, data_right)
                                        sheet.write(rowx, 7, 0, data_right)
                                        sheet.write(rowx, 8, balance, data_right)
                                        rowx += 1
                                        number +=1



                    
            sheet.write_merge(rowx, rowx, 0, 5, u'НИЙТ', data_right)
            sheet.write(rowx, 6, creditn, data_right)
            sheet.write(rowx, 7,  debitn , data_right)
            sheet.write(rowx, 8, balance, data_right)
            rowx += 3

            
            
        inch = 1000
        sheet.col(0).width = 1 * inch
        sheet.col(1).width = 3 * inch
        sheet.col(2).width = 7 * inch
        sheet.col(3).width = 8 * inch
        sheet.col(4).width = 8 * inch
        sheet.col(5).width = 3 * inch
        sheet.col(6).width = 4 * inch
        sheet.col(7).width = 4 * inch
        sheet.col(8).width = 4 * inch
        sheet.col(9).width = 5 * inch
        sheet.row(3).height = 540
        
        
        
        sheet.write(rowx + 2, 1, u"Хөтөлсөн нягтлан бодогч: ..................................................../                                            /",
                    xlwt.easyxf('font:bold off;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write(rowx + 4, 1, u"Хянасан ерөнхий (ахлах) нягтлан бодогч: ..................................................../                                           /",
                    xlwt.easyxf('font:bold off;align:wrap off,vert centre,horiz left;font: height 180'))
        
        return {'data':book, 'directory_name':u"Ерөнхий журнал",
                'attache_name':"Ерөнхий журнал"}
        
    
    
    
        
    
    
    