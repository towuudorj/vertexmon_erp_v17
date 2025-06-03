# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import xlwt
from odoo.exceptions import UserError

class general_journal_report(models.TransientModel):
    """
        Ерөнхий журнал тайлан
    """
    _name = "general.journal.report"
    _description = "General journal report"
    
    
    company_id = fields.Many2one('res.company', string='Company', readonly=True, 
                                 default=lambda self: self.env.user.company_id)
    date_from = fields.Date(string="Start date", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="End date", required=True, default=fields.Date.context_today)
    fiscalyear_id = fields.Many2one('account.fiscal.year', string='Fiscal year', required=True)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                     ('all', 'All Entries')
                                    ], string='State', required=True,default='posted')
    account_ids = fields.Many2many('account.account', 'general_journal_report_rel', 'account_id', 'general_id', 
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
        
        date_str = '%s-%s' % (self.date_from,self.date_to)
        
      
        sheet.write(4, 0, u'Байгууллагын нэр: %s' % self.company_id.name, xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 220'))
        sheet.write(4, 6, u'%s' % date_str, xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        
        sheet.write_merge(3, 3, 1, 6, u'ЕРӨНХИЙ ЖУРНАЛ', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz center;font: height 280'))

        sheet.write(0, 6, u'Сангийн сайдын 2018 оны', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        sheet.write(1, 6, u'өдрийн 100 дугаар тушаалын хавсралт', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        rowx = 5
        
        sheet.write_merge(rowx, rowx+1, 0, 0, u'Д/д', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx, 1, 2, u'Баримтын', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 1, 1, u'Он сар', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 2, 2, u'Дугаар', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 3, 3, u'Гүйлгээний утга', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 4, 4, u'Харилцагч', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 5, 5, u'Дансны нэр,код', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx, 6, 7, u'Дүн', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 6, 6, u'Дебит', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 7, 7, u'Кредит', styledict['heading_xf'])
        data_right = ezxf('font: bold off; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_right = ezxf('font: bold on; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        states = ''
        if self.target_move =='posted':
            states = ['posted']
        else:
            states = ['posted','draft']
        rowx = 7
        number = 1
        account_obj = self.env['account.account']
        move_line_obj = self.env['account.move.line']
        partner_obj = self.env['res.partner']
        journal_id = self.env['account.journal'].search([('type','=','opening'),('company_id','=',self.company_id.id)])
        start_balance = 0.0
        total = 0.0
        
        
        if len(self.account_ids)==1:
            account_id = account_obj.search([('id','=',self.account_ids.id)])
        else:
            account_id = account_obj.search( [('id','in',tuple(self.account_ids.ids))])
        for line in account_id:
            balance = 0.0
            total_debit = 0.0
            total_credit = 0.0
            if len(states)==1:
                self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                        account_move as am on am.id=aml.move_id
                         where aml.date >= '%s' and aml.date <='%s' and aml.account_id = %s and am.state = '%s' and am.journal_id = %s 
                         """%(self.fiscalyear_id.date_from,self.date_from,line.id,states[0],journal_id.id))
                acc = self._cr.dictfetchall()
            else:
                self._cr.execute("""select sum(aml.debit-aml.credit) as balance from account_move_line as aml left join
                        account_move as am on am.id=aml.move_id
                         where aml.date >= '%s' and aml.date <='%s' and aml.account_id = %s and am.state in %s and am.journal_d = %s
                         """%(self.fiscalyear_id.date_from,self.date_from,line.id,tuple(states),journal_id.id))
                acc = self._cr.dictfetchall()
            if acc[0]:
                if acc[0]['balance'] == None:
                    balance = 0.0
                else:
                    balance = acc[0]['balance']
            sheet.write_merge(rowx, rowx, 0, 1, u'Дансны №', styledict['heading_xf'])
            sheet.write_merge(rowx, rowx, 2, 2, u'%s %s'%(line.code,line.name), styledict['heading_xf'])
            sheet.write_merge(rowx, rowx, 3, 4, u'Эхний үлдэгдэл', styledict['heading_xf'])
            sheet.write_merge(rowx, rowx, 5, 5, balance, data_bold_right)
            rowx +=1
            
            if len(states)==1:
                self._cr.execute("""select am.id from account_move_line AS aml 
                            left join account_move AS am ON am.id = aml.move_id 
                            left join account_journal as aj on aj.id = am.journal_id
                            left join account_account AS aa on aa.id = aml.account_id 
                            WHERE am.date >= '%s' and am.date <='%s' and 
                            aml.account_id = %s and am.state = '%s'
                            group by am.id
                            """%(self.date_from,self.date_to,line.id,states[0]))
                all = self._cr.fetchall()
            else:
                self._cr.execute("""select am.id from account_move_line AS aml 
                            left join account_move AS am ON am.id = aml.move_id 
                            left join account_journal as aj on aj.id = am.journal_id
                            left join account_account AS aa on aa.id = aml.account_id 
                            WHERE am.date >= '%s' and am.date <='%s' and 
                            aml.account_id = %s and am.state in %s
                            group by am.id"""%(self.date_from,self.date_to,line.id,tuple(states)))
                all = self._cr.fetchall()

            
            moves = []
            for i in all:
                moves.append(i[0])
            move_ids = []
            if len(moves) ==1:
                move_id = move_line_obj.search([('account_id','!=',line.id),('move_id','=',moves)])
                for lines in move_id:
                    move_ids.append(lines.id)
            else:
                move_id = move_line_obj.search([('account_id','!=',line.id),('move_id','in',moves)])
                for lines in move_id:
                    move_ids.append(lines.id)
            if len(move_ids)==1:
                ddd =  move_ids
                if ddd != False and ddd !=[]:
                    self._cr.execute("""select aa.name,aa.code,sum(aml.debit) as debit, sum(aml.credit) as credit, am.date, am.name,aml.name, aml.partner_id
                                 from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE aml.id = """+str(ddd[0])+""" group by aa.name,aa.code, am.date, am.name, aml.name, aml.partner_id order by am.date asc""")
                    line_data = self._cr.fetchall()
                else:
                    raise UserError(_(u"Таны сонгосон данс дээр гүйлгээ байхгүй байна."))
            else:
                ddd =  tuple(move_ids)
                if move_ids !=False and move_ids !=[]:
                    self._cr.execute("""select aa.name,aa.code,sum(aml.debit) as debit, sum(aml.credit) as credit, am.date, am.name,aml.name, aml.partner_id
                                 from account_move_line AS aml 
                                left join account_move AS am ON am.id = aml.move_id 
                                left join account_journal as aj on aj.id = am.journal_id
                                left join account_account AS aa on aa.id = aml.account_id 
                                WHERE aml.id in """+str(ddd)+""" group by aa.name,aa.code, am.date, am.name, aml.name, aml.partner_id order by am.date asc""")
                    line_data = self._cr.fetchall() 
                else:
                    raise UserError(_(u"Таны сонгосон данс дээр гүйлгээ байхгүй байна."))
            if line_data !=[]:
                for li in line_data:
                    sheet.write(rowx, 0, number, styledict['text_xf'])
                    sheet.write(rowx, 1, '%s'%li[4], styledict['text_xf'])
                    sheet.write(rowx, 2, '%s'%li[5], styledict['text_xf'])
                    sheet.write(rowx, 3, li[6], styledict['text_xf'])
                    if li[7]!=None:
                        partner = partner_obj.browse(li[7])
                        sheet.write(rowx, 4, partner.name, styledict['text_xf'])
                    else:
                        sheet.write(rowx, 4, '', styledict['text_xf'])
                    if li[3] > 0.0 and li[2] > 0.0:
                        tbalance =li[3]-li[2]
                        if tbalance > 0.0:
                            balance -=tbalance
                            total_credit +=tbalance
                            sheet.write_merge(rowx, rowx, 7, 7, tbalance, data_right)
                            sheet.write(rowx, 5, u'%s %s'%(li[1],li[0]), data_right)
                            sheet.write(rowx, 6,  0.0, data_right)
                        else:
                            balance +=tbalance
                            total_debit +=tbalance
                            sheet.write_merge(rowx, rowx, 7, 7, 0.0, data_right)
                            sheet.write(rowx, 5, u'%s %s'%(li[1],li[0]), data_right)
                            sheet.write(rowx, 6,  tbalance, data_right)
                    elif li[3] > 0.0 and li[2] == 0.0:
                        total_credit +=li[3]
                        sheet.write_merge(rowx, rowx, 7, 7, -li[3], data_right)
                        sheet.write(rowx, 5, u'%s %s'%(li[1],li[0]), data_right)
                        sheet.write(rowx, 6,  0.0, data_right)
                        balance -=li[3]
                    elif li[3] == 0.0 and li[2] > 0.0:
                        balance +=li[2]
                        total_debit +=li[2]
                        sheet.write(rowx, 5,  u'%s %s'%(li[1],li[0]), data_right)
                        sheet.write_merge(rowx, rowx, 6, 6, li[2], data_right)
                        sheet.write(rowx, 7, 0.0, data_right)                    
                    number += 1
                    rowx += 1
                sheet.write_merge(rowx, rowx, 0, 5, u'НИЙТ', data_right)
                sheet.write(rowx, 6, total_debit, data_right)
                sheet.write(rowx, 7, total_credit, data_right)
                rowx += 1
                sheet.write_merge(rowx, rowx, 0, 5, u'Эцсийн үлдэгдэл', data_right)
                sheet.write_merge(rowx, rowx, 6, 7, balance, data_right)
                rowx += 1
                
            
            
        inch = 1000
        sheet.col(0).width = 2 * inch
        sheet.col(1).width = 4 * inch
        sheet.col(2).width = 8 * inch
        sheet.col(3).width = 8 * inch
        sheet.col(4).width = 8 * inch
        sheet.col(5).width = 8 * inch
        sheet.col(6).width = 4 * inch
        sheet.col(7).width = 4 * inch
        sheet.col(8).width = 4 * inch
        sheet.col(9).width = 4 * inch
        sheet.row(3).height = 540
        
        
        
        sheet.write(rowx + 2, 1, u"Хөтөлсөн нягтлан бодогч: ..................................................../                                            /",
                    xlwt.easyxf('font:bold off;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write(rowx + 4, 1, u"Хянасан ерөнхий (ахлах) нягтлан бодогч: ..................................................../                                           /",
                    xlwt.easyxf('font:bold off;align:wrap off,vert centre,horiz left;font: height 180'))
        
        return {'data':book, 'directory_name':u"Ерөнхий журнал",
                'attache_name':"Ерөнхий журнал"}
        
    
    
    