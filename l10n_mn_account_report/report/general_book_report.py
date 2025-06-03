# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import xlwt


class general_book_report(models.TransientModel):
    """
        Ерөнхий дэвтэр тайлан
    """
    _name = "general.book.report"
    _description = "General book report"
    
    
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)
    date_from = fields.Date(string="Start date", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="End date", required=True, default=fields.Date.context_today)
    fiscalyear_id = fields.Many2one('account.fiscal.year', string='Fiscal year', required=True)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                     ('all', 'All Entries')
                                    ], string='State', required=True, default='posted')
    account_ids = fields.Many2many('account.account','general_book_report_rel','account_id','general_id', 
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
        sheet = book.add_sheet(u'Ерөнхий дэвтэр')
        
        
        date_str = '%s-%s' % (self.date_from,self.date_to)
        
        states = ''
        if self.target_move =='posted':
            states = ['posted']
        else:
            states = ['posted','draft']
        sheet.write(1, 0, u'Байгууллагын нэр: %s' % self.company_id.name, xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write(1, 2, u'Ерөнхий дэвтэр', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 240'))
        sheet.write(1, 3, u'( %s )' % date_str, xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))

        rowx = 3
        
        
        data_right = ezxf('font: bold off; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_right = ezxf('font: bold on; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_center = ezxf('font: bold on; align: wrap on, vert centre, horiz centre; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        
        number = 0
        account_obj = self.env['account.account']
        move_line_obj = self.env['account.move.line']
        journal_obj = self.env['account.journal']
        journal_ids = journal_obj.search([('type','!=','opening'),('company_id','=',self.company_id.id)])
        journal_st = journal_obj.search([('type','=','opening'),('company_id','=',self.company_id.id)])
        
        if len(self.account_ids)==1:
            account_id = account_obj.search([('id','=',self.account_ids.id),('company_id','=',self.company_id.id)])
            
        else:
            account_id = account_obj.search([('id','in',tuple(self.account_ids.ids),('company_id','=',self.company_id.id))])

        start_balance = 0.0
        total = 0.0
        for line in account_id:
            balance = 0.0
            if len(states)==1:
                self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                            account_move as am on am.id=aml.move_id
                             where aml.date >= '%s' and aml.date <='%s' and aml.account_id = %s and am.state = '%s' 
                             and am.journal_id = %s """%(self.fiscalyear_id.date_from,self.date_from,line.id,states[0],journal_st.id))
                acc = self._cr.dictfetchall()
            else:
                self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                            account_move as am on am.id=aml.move_id
                             where aml.date >= '%s' and aml.date <='%s' and aml.account_id = %s and am.state in %s 
                             and am.journal_id = %s"""%(self.fiscalyear_id.date_from,self.date_from,line.id,states,journal_st.id))
                acc = self._cr.dictfetchall()
            if acc[0]:
                if acc[0]['balance'] == None:
                    if len(states)>1:
                        self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                                    account_move as am on am.id=aml.move_id
                                     where aml.date >= '%s' and aml.date <='%s' and aml.account_id = %s and am.state in '%s' 
                                     and am.journal_id in %s """%(self.fiscalyear_id.date_from,self.date_from,line.id,tuple(states),tuple(journal_ids.ids)))
                        acc = self._cr.dictfetchall()
                    elif len(states)==1:
                        self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                                    account_move as am on am.id=aml.move_id
                                     where aml.date >= '%s' and aml.date <='%s' and aml.account_id = %s and am.state = '%s' 
                                     and am.journal_id in %s """%(self.fiscalyear_id.date_from,self.date_from,line.id,states[0],tuple(journal_ids.ids)))
                        acc = self._cr.dictfetchall()
  
                    if acc[0]:
                        if acc[0]['balance'] == None:
                            balance = 0.0
                        else:
                            balance = acc[0]['balance']
                else:
                    balance = acc[0]['balance']
            
            sheet.write(rowx, 0, number, data_bold_center)
            sheet.write_merge(rowx, rowx, 1, 1, u'Дансны №', data_bold_center)
            sheet.write_merge(rowx, rowx, 2, 2, u'%s %s'%(line.code,line.name), data_bold_center)
            sheet.write_merge(rowx, rowx, 3, 3, u'Эхний үлдэгдэл', data_bold_center)
            sheet.write_merge(rowx, rowx, 4, 4, balance, data_bold_right)
            rowx +=1
            
                    
            if len(states)==1:
                self._cr.execute("""select am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                 left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' and 
                                aml.account_id = %s  and am.state = '%s' and am.journal_id in %s
                                order by aml.date asc"""%(self.date_from,self.date_to,line.id,states[0],tuple(journal_ids.ids)))
                all = self._cr.fetchall()
            else:
                self._cr.execute("""select am.id from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                 left join account_account AS aa on aa.id = aml.account_id 
                                WHERE am.date >= '%s' and am.date <='%s' and 
                                aml.account_id = %s  and am.state in %s and am.journal_id in %s
                                order by aml.date asc"""%(self.date_from,self.date_to,line.id,states,tuple(journal_ids.ids  )))
                all = self._cr.fetchall()
        
            moves = []
            move_ids = []
            line_data = False
            for i in all:
                moves.append(i[0])
            if len(moves) == 1:
                move_id = move_line_obj.search([('account_id','!=',line.id),('move_id','=',moves[0])])
                if len(move_id)==1:
                    move_ids.append(move_id[0])
                else:
                    for mv in move_id:
                        move_ids.append(mv.id)
            elif len(moves) > 1:
                move_id = move_line_obj.search([('account_id','!=',line.id),('move_id','in',moves)])
                for mv in move_id:
                    move_ids.append(mv.id)
                
            if len(move_ids)==1:
                ddd =  move_ids[0]
                self._cr.execute("""select aa.name,aa.code,sum(aml.debit) as debit, sum(aml.credit) as credit
                             from account_move_line AS aml 
                            left join account_move AS am ON am.id = aml.move_id 
                            left join account_journal as aj on aj.id = am.journal_id
                            left join account_account AS aa on aa.id = aml.account_id 
                            WHERE aml.id = """+str(ddd)+" group by aa.name, aa.code order by aa.code")
                line_data = self._cr.fetchall()
            elif len(move_ids)>1:
                ddd =  tuple(move_ids)
                self._cr.execute("""select aa.name,aa.code,sum(aml.debit) as debit, sum(aml.credit) as credit
                             from account_move_line AS aml 
                            left join account_move AS am ON am.id = aml.move_id 
                            left join account_journal as aj on aj.id = am.journal_id
                            left join account_account AS aa on aa.id = aml.account_id
                            WHERE aml.id in """+str(ddd)+" group by aa.name, aa.code order by aa.code")
                line_data = self._cr.fetchall() 
                
            if line_data !=[] and line_data !=False  and move_ids !=[]:
                sheet.write_merge(rowx, rowx+1, 0, 0, u'Д/д', styledict['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 1, 1, u'Харьцсан данс', styledict['heading_xf'])
                sheet.write_merge(rowx, rowx, 2, 3, u'Гүйлгээ', styledict['heading_xf'])
                sheet.write_merge(rowx+1, rowx+1, 2, 2, u'Дебит', styledict['heading_xf'])
                sheet.write_merge(rowx+1, rowx+1, 3, 3, u'Кредит', styledict['heading_xf'])
                sheet.write_merge(rowx, rowx+1, 4, 4, u'Үлдэгдэл', styledict['heading_xf'])
                rowx +=2
                debit = 0.0
                credit = 0.0
                for i in line_data:
                    number += 1
                    sheet.write(rowx, 0, number, styledict['text_xf'])
                    sheet.write(rowx, 1, u'%s %s'%(i[1],i[0]), styledict['text_xf'])
                    sheet.write(rowx, 2, i[3], data_right)
                    sheet.write(rowx, 3, i[2], data_right)
                    if i[3] > 0.0:
                        balance +=i[3]
                        debit +=i[3]
                    if i[2] > 0.0:
                        balance -=i[2]
                        credit +=i[2]
                    sheet.write(rowx, 4, balance, data_right)
                    rowx += 1
                sheet.write(rowx, 0, '', styledict['text_xf'])
                sheet.write(rowx, 1, '', styledict['text_xf'])
                sheet.write(rowx, 2, debit, data_right)
                sheet.write(rowx, 3, credit, data_right)
                sheet.write(rowx, 4, '', data_right)
                
            rowx +=2
            
        inch = 1000
        sheet.col(0).width = 1 * inch
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
        
        return {'data':book, 'directory_name':u"Ерөнхий дэвтэр",
                'attache_name':"Ерөнхий дэвтэр"}
        

    