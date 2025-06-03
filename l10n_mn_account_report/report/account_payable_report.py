# -*- coding: utf-8 -*-


from odoo import api, fields, models
from datetime import timedelta, datetime
import xlwt
from odoo import tools, _


class AccountPayableReport(models.TransientModel):
    """
        Бэлэн мөнгөний гүйлгээ тайлан
    """
    _name = "account.payable.report"
    _description = "Account payable report"
    
    
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    start_date = fields.Date(string="Start date", required=True)
    end_date = fields.Date(string="End date", required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')
                                    ], string='State', required=True, default='posted')
    

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
        styledict = self.get_easyxf_styles()
        
        ezxf = xlwt.easyxf
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet(u'Account payable')
        
        date_str = '%s-%s' % (
            datetime.strptime(str(self.start_date), '%Y-%m-%d').strftime('%Y.%m.%d'),
            datetime.strptime(str(self.end_date), '%Y-%m-%d').strftime('%Y.%m.%d')
        )
        
        sheet.write_merge(0, 0, 0, 1, u'НХМаягт МХ-4', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write_merge(0, 0, 2, 7, u'Сангийн сайдын 2018 оны 5-р сарын 8-ны', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        sheet.write_merge(1, 1, 2, 7, u'өдрийн 100 дугаар тушаалын хавсралт', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        sheet.write_merge(3, 3, 1, 6, u'АВЛАГЫН ДАНСНЫ ДЭЛГЭРЭНГҮЙ БҮРТГЭЛ', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz center;font: height 280'))
        sheet.write(5, 0, u'Байгууллагын нэр: %s' % self.company_id.name, xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write(5, 7, u'Дэлгэрэнгүй бүртгэл АВ-1', xlwt.easyxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        rowx = 7
        
        sheet.write_merge(rowx, rowx+1, 0, 0, u'Д/д', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 1, 1, u'Он сар өдөр', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 2, 2, u'Журналын төрөл,дугаар', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 3, 3, u'Гүйлгээний утга', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx, 4, 5, u'Гүйлгээний дүн', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 4, 4, u'Дебит', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 5, 5, u'Кредит', styledict['heading_xf'])
        sheet.write_merge(rowx, rowx, 6, 7, u'Үлдэгдэл', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 6, 6, u'Дебит', styledict['heading_xf'])
        sheet.write_merge(rowx+1, rowx+1, 7, 7, u'Кредит', styledict['heading_xf'])
        data_right = ezxf('font: bold off; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_right = ezxf('font: bold on; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        
        if self.payable_receivable_type == 'payable':
            type = ['payable']
        
        account_type = []
        if len(type)==1:
            account_type_id = account_type_obj.search([('type','=',type[0])])
            for typ in account_type_id:
                account_type.append(typ.id)
        accounts = []
        if len(account_type)==1:
            account = account_obj.search([('user_type_id','=',account_type[0])])
            for acc in account:
                for ac in self.account_id:
                    if acc.id == ac.id:
                        accounts.append(acc.id)
        else:
            account = account_obj.search([('user_type_id','in',tuple(account_type))])
            for acc in account:
                for ac in self.account_id:
                    if acc.id == ac.id:
                        accounts.append(acc.id)

        
            
        inch = 1000
        sheet.col(0).width = 1 * inch
        sheet.col(1).width = 4 * inch
        sheet.col(2).width = 6 * inch
        sheet.col(3).width = 7 * inch
        sheet.col(4).width = 5 * inch
        sheet.col(5).width = 4 * inch
        sheet.col(6).width = 4 * inch
        sheet.col(7).width = 4 * inch
        sheet.col(8).width = 4 * inch
        sheet.col(9).width = 4 * inch
        sheet.row(3).height = 540
        
        
        
        sheet.write(rowx + 3, 1, u"Нягтлан бодогч: ..................................................../                                            /",
                    xlwt.easyxf('font:bold off;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write(rowx + 5, 1, u"Мөнгөний нярав: ..................................................../                                           /",
                    xlwt.easyxf('font:bold off;align:wrap off,vert centre,horiz left;font: height 180'))
        
        return {'data':book, 'directory_name':"Ажил гүйлгээ",
                'attache_name':"Ажил гүйлгээ"}
        
