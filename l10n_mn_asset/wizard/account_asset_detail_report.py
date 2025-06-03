# -*- coding: utf-8 -*-
from datetime import timedelta, datetime
from odoo import fields, models, _
import xlwt

class AccountAssetDetailReport(models.TransientModel):
    """
        Үндсэн хөрөнгийн дэлгэрэнгүй тайлан
    """
    _inherit = "abstract.report.excel"
    _name = "account.asset.detail.report"
    _description = "Asset detial Report - Mongolia"
    
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    start_date = fields.Date(string='Start date', required=True)
    end_date = fields.Date(string='End date', required=True)
    fiscalyear_id = fields.Many2one('account.fiscal.year', string='Fiscal year', required=True)
    category_id = fields.Many2one('account.asset.category', string='Asset category')
    owner_id = fields.Many2one('hr.employee', string='Owner')
    is_balance = fields.Boolean(string='Is balance')
    

    def get_export_data(self):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''

        company = self.env['res.company'].browse(self.company_id.id)
        ezxf = xlwt.easyxf
        styles = self.get_easyxf_styles()
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet(u'Үндсэн хөрөнгийн тайлан')
        sheet.portrait = False
        data_style = ezxf('font: bold off; align: wrap on, vert centre, horiz centre; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold = ezxf('font: bold on; align: wrap on, vert centre, horiz centre; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_right = ezxf('font: bold off; align: wrap on, vert centre, horiz right; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_left = ezxf('font: bold off; align: wrap on, vert centre, horiz left; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_bold_left = ezxf('font: bold on; align: wrap on, vert centre, horiz left; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        data_center = ezxf('font: bold off; align: wrap on, vert centre, horiz center; font: height 200;borders: left thin, right thin, top thin, bottom thin;','#,##0.00_);(#,##0.00)')
        sheet.write(0, 0, u'Байгууллагын нэр: %s' % (company.name,), ezxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.write_merge(3, 3, 0, 18, u'Үндсэн хөрөнгийн дэлгэрэнгүй тайлан', ezxf('font: bold on; align: wrap off, vert centre, horiz centre;font: height 250'))
        sheet.write_merge(0, 0, 14, 17,  u'Санхүү Эдийн Засгийн сайдын 2002 оны', ezxf('font:bold on;align:wrap off,vert centre,horiz centre;font: height 180'))
        sheet.write_merge(1, 1, 14, 17,  u'191 тоот тушаалаар батлав.', ezxf('font:bold on;align:wrap off,vert centre,horiz center;font: height 180'))
        sheet.write_merge(4, 4, 16, 17, u'Дэлгэрэнгүй бүртгэл', ezxf('font: bold on; align: wrap off, vert centre, horiz left;font: height 150'))
        sheet.write_merge(5, 5, 16, 17, u'ҮХ-1 №....', ezxf('font: bold on; align: wrap off, vert centre, horiz centre;font: height 150'))
        sheet.write(5, 7, u'Тайлант %s - %s'%(self.start_date,self.end_date) , ezxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))
        rowx = 7
        sheet.write_merge(rowx, rowx+1, 0, 0, u'Д/д', styles['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 1, 1, u'Дансны дугаар', styles['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 2, 2, u'Үндсэн хөрөнгийн нэр', styles['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 3, 3, u'Хөрөнгийн дугаар', styles['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 4, 4, u'Ашиглалтанд орсон он сар өдөр', styles['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 5, 5, u'Ашиглах жил', styles['heading_xf'])
        sheet.write_merge(rowx, rowx, 6, 7, u'Эхний үлдэгдэл', styles['heading_xf'])
        sheet.write(rowx+1, 6, u'Тоо', styles['heading_xf'])
        sheet.write(rowx+1, 7, u'Өртөг', styles['heading_xf'])
        sheet.write_merge(rowx, rowx , 8, 9, u'Орлого', styles['heading_xf'])
        sheet.write(rowx+1, 8, u'Тоо', styles['heading_xf'])
        sheet.write(rowx+1, 9, u'Өртөг', styles['heading_xf'])
        sheet.write_merge(rowx, rowx , 10, 11, u'Зарлага', styles['heading_xf'])
        sheet.write(rowx+1, 10, u'Тоо', styles['heading_xf'])
        sheet.write(rowx+1, 11, u'Өртөг', styles['heading_xf'])
        sheet.write_merge(rowx, rowx, 12, 13, u'Эцсийн үлдэгдэл', styles['heading_xf'])
        sheet.write(rowx+1, 12, u'Тоо', styles['heading_xf'])
        sheet.write(rowx+1, 13, u'Өртөг', styles['heading_xf'])
        sheet.write_merge(rowx, rowx, 14, 17, u'Элэгдэл', styles['heading_xf'])
        sheet.write(rowx+1, 14, u'Хуримтдлагдсан', styles['heading_xf'])
        sheet.write(rowx+1, 15, u'Сарын', styles['heading_xf'])
        sheet.write(rowx+1, 16, u'Хасагдсанд ногдох', styles['heading_xf'])
        sheet.write(rowx+1, 17, u'Элэгдлийн дүн', styles['heading_xf'])
        sheet.write_merge(rowx, rowx+1, 18, 18, u'Үлдэгдэл өртөг', styles['heading_xf'])
        rowx +=2
        for col in range(0,19):
            sheet.write(rowx, col, col+1,styles['heading_xf'])
        
        rowx = 10
        asset_obj = self.env['account.asset.asset']
        
        asset_capital_obj = self.env['account.asset.asset.capitalization']
        if self.category_id:
            asset_id = asset_obj.search([('company_id','=',self.company_id.id),('category_id','=',self.category_id.id),('state','!=','draft')],order='date asc')
        else:
            asset_id = asset_obj.search([('company_id','=',self.company_id.id),('state','!=','draft')],order='date asc')
        
        num = 0
        first_balance = 0.0
        first_qty = 0.0
        
        income_balance = 0.0
        income_qty = 0.0
        
        expense_balance = 0.0
        expense_qty = 0.0
        
        last_balance = 0.0
        last_qty = 0.0
        
        in_dep_balance = 0.0
        month_balance = 0.0
        drop_balance = 0.0
        dep_balance = 0.0
        total_balance_amount = 0.0
        
        if asset_id:
            for line in asset_id:
                if self.is_balance == True:
                    if line.value_residual > 0.0:
                        balance_amount = 0.0
                        write_off_amount = 0.0
                        deprecation_amount = 0.0
                        month_deprecation_amount = 0.0
                        act_amount = 0.0
                        capital_amount = 0.0
                        num +=1
                        sheet.write(rowx, 0, '%s'%num,data_center)
                        sheet.write(rowx, 1, line.category_id.name,data_left)
                        sheet.write(rowx, 2, line.name,data_left)
                        sheet.write(rowx, 3, line.code,data_left)
                        sheet.write(rowx, 4, '%s'%line.date,data_left)
                        sheet.write(rowx, 5, line.method_number/12,data_left)
                        sheet.write(rowx, 6, 1,data_left)
                        if line.date <= self.start_date:
                            sheet.write(rowx, 7, line.value,data_right)
                            sheet.write(rowx, 8, 1,data_right)
                        else:
                            sheet.write(rowx, 7, 0,data_right)
                            sheet.write(rowx, 8, 0,data_right)
                        asset_cap_id = asset_capital_obj.search( [('asset_id','=',line.id)])
                        
                        first_balance +=line.value
                        first_qty +=1
                        
                        
                        if asset_cap_id:
                            for cap in asset_capital_obj.browse( asset_cap_id.id):
                                capital_amount += cap.amount
                        else:
                            if line.date >= self.start_date:
                                capital_amount +=line.value
                                
                        income_balance +=capital_amount
                        income_qty +=1
                        act_amount = line.value_residual
                        sheet.write(rowx, 9, capital_amount,data_right)
                        sheet.write(rowx, 10, 1,data_left)
                        sheet.write(rowx, 11, act_amount,data_right)
                        
                        expense_balance +=act_amount
                        expense_qty +=1
                        
                        sheet.write(rowx, 12, 1,data_left)
                        total_amount = line.value+capital_amount-act_amount
                        
                        last_balance +=total_amount
                        last_qty +=1
                        sheet.write(rowx, 13, total_amount,data_right)
                        for lis in line.depreciation_line_ids:
                            for history in lis.move_id.line_ids:
                                if history.date < self.start_date:
                                    deprecation_amount +=history.debit
                        in_dep_balance +=deprecation_amount
                        sheet.write(rowx, 14, deprecation_amount,data_right)                
                        for dep in line.depreciation_line_ids:
                            if dep.move_check == True:
                                if dep.depreciation_date >= self.start_date and dep.depreciation_date<=self.end_date:
                                    month_deprecation_amount += dep.amount
                                    
                        month_balance +=month_deprecation_amount
                        sheet.write(rowx, 15, month_deprecation_amount,data_right)
                        if line.state == 'close':
                            write_off = 0.0
                            self._cr.execute("""SELECT
                                   SUM(l.debit-l.credit) AS amount
                                FROM
                                    account_move_line l
                                WHERE
                                    l.asset_id = %s GROUP BY l.asset_id """, (line.id,))
                            res=self._cr.dictfetchall()
                            if res !=[]:
                                for lines in res:
                                    write_off = lines['amount']
                            write_off_amount = line.value_residual
                        drop_balance +=write_off_amount
                        sheet.write(rowx, 16, write_off_amount,data_right)
                        last_amount = deprecation_amount+month_deprecation_amount-write_off_amount
                        sheet.write(rowx, 17, last_amount,data_right)
                        dep_balance +=last_amount
                        if line.state=='close':                          
                            balance_amount = 0.0
                        else:
                            balance_amount = total_amount-last_amount
                        sheet.write(rowx, 18, balance_amount,data_right)
                        total_balance_amount += balance_amount
                        rowx +=1
                else:
                
                    balance_amount = 0.0
                    write_off_amount = 0.0
                    deprecation_amount = 0.0
                    deprecation_amounts = 0.0
                    month_deprecation_amount = 0.0
                    act_amount = 0.0
                    capital_amount = 0.0
                    in_amount = 0.0
                    first_value = 0.0
                    
                    
                    num +=1
                    sheet.write(rowx, 0, '%s'%num,data_center)
                    sheet.write(rowx, 1, line.category_id.name,data_left)
                    sheet.write(rowx, 2, line.name,data_left)
                    sheet.write(rowx, 3, line.code,data_left)
                    sheet.write(rowx, 4, '%s'%line.date,data_left)
                    sheet.write(rowx, 5, line.method_number/12,data_left)
                    
                    if line.date <=self.start_date:
                        fact_amounts = 0.0
                        fact_amount = 0.0
                        fact_amountsd =0.0
                        if self.fiscalyear_id.date_start == self.start_date:
                            if line.state=='close':
                                if line.scrap_date <= self.start_date:
                                    first_value = 0.0
                                else:
                                    first_value = line.value
                                
                            else:
                                #or dep in line.depreciation_line_ids:
                                #        if dep.move_check == True:
                                #            if dep.depreciation_date < self.start_date:
                                #                fact_amountsd += dep.amount
                                first_value = line.value
                        else:
                            
                            first_value = line.value
                        first_balance +=first_value
                        first_qty +=1
                        count = 1
                        sheet.write(rowx, 6, count, data_left)
                        sheet.write(rowx, 7, first_value,data_right)
                        sheet.write(rowx, 8, 0,data_right)
                    else:
                        count = 0
                        sheet.write(rowx, 6, count, data_left)
                        sheet.write(rowx, 7, 0,data_right)
                        sheet.write(rowx, 8, 0,data_right)
                    asset_cap_id = asset_capital_obj.search( [('asset_id','=',line.id)])
                    
                    
                    
                    
                    if asset_cap_id:
                        for cap in asset_capital_obj.browse( asset_cap_id.id):
                            capital_amount += cap.amount
                        
                    else:
                        if line.date > self.start_date and line.date <= self.end_date:
                            in_amount +=line.value
                                
                    income_balance +=capital_amount+in_amount
                    income_qty +=1
                    
                    sheet.write(rowx, 9, capital_amount+in_amount,data_right)
                    
                    if line.state=='close':
                        act_amounts = 0.0
                        if self.fiscalyear_id.date_start == self.start_date:
                            if line.scrap_date <= self.start_date:
                                for dep in line.depreciation_line_ids:
                                        if dep.depreciation_date<=self.end_date:
                                            act_amounts += dep.amount
                                act_amountd = line.value - act_amounts
                            else:
                                act_amountd = line.value
                           # print("addddddddddddddddddddfff",act_amountd)
                            if int(act_amountd) == 0.0:
                                #if line.is_closed == True:
                                    act_amount = 0.0
                            else:
                                act_amount = act_amountd
                        else:
                            if line.scrap_date <= self.end_date:
                                for dep in line.depreciation_line_ids:
                                    if dep.depreciation_date<=self.end_date:
                                            act_amounts += dep.amount
                            act_amountd = line.value - act_amounts
                            if int(act_amountd) == 0.0:
                                act_amount = line.value
                            else:
                                act_amount = 0.0
                    if act_amount == 0.0:
                        sheet.write(rowx, 10, 0,data_left)
                    else:
                        sheet.write(rowx, 10, 1,data_left)
                        expense_qty +=1
                    
                    sheet.write(rowx, 11, act_amount,data_right)
                    
                    expense_balance +=act_amount
                    
                    
                    sheet.write(rowx, 12, 1,data_left)
                    total_amount = 0.0
                    if first_value == 0.0:
                        #print("aaaaaaaaaaaaaaaaaaaaaaaaaaaa dsdssssssssssssssss",in_amount,line.name)
                        if in_amount == 0.0:
                            total_amount = 0.0
                        else:
                            total_amount = first_value+capital_amount+in_amount-act_amount
                    else:
                        total_amount = first_value+capital_amount+in_amount-act_amount
                    
                    last_balance +=total_amount
                    last_qty +=1
                    #print("aaaaaaaaaaaaaaaaaaaaaaaaaaaadddd",total_amount,line.name)
                    sheet.write(rowx, 13, total_amount,data_right)
                    if line.state == 'close':
                        for lis in line.depreciation_line_ids:
                            if lis.move_check == True:
                                for history in lis.move_id.line_ids:
                                    if history.date < self.start_date:
                                        if lis.move_id.state != 'cancel':
                                            deprecation_amount +=history.debit
                        #print("aaaaadddddddddddddddddddddddd",line.value, deprecation_amount)
                        act_amountds = line.value - deprecation_amount
                        if int(act_amountds) == 0.0:
                            if line.scrap_date <=self.start_date:
                                deprecation_amount = 0.0
                                deprecation_amounts = 0.0
                            else:
                                deprecation_amount = deprecation_amount
                                deprecation_amounts = deprecation_amount
                        else:
                            if line.scrap_date <=self.start_date:
                                deprecation_amount = 0.0
                                deprecation_amounts = 0.0
                            else:
                                deprecation_amount = deprecation_amount
                                deprecation_amounts = deprecation_amount

                            
                    else:
                        for lis in line.depreciation_line_ids:
                            if lis.move_check == True:
                                for history in lis.move_id.line_ids:
                                    if lis.move_id.state != 'cancel':
                                        if history.date < self.start_date:
                                            deprecation_amount +=history.debit
                    #print("aaaaaaaaaaaaaaaaaaaa",)
                    if total_amount == 0.0:
                        deprecation_amount = deprecation_amount
                        in_dep_balance +=deprecation_amount
                    else:
                        deprecation_amount = deprecation_amount
                        in_dep_balance +=deprecation_amount
                    sheet.write(rowx, 14, deprecation_amount,data_right)                
                    for lis in line.depreciation_line_ids:
                       # for history in lis.move_id.line_ids:
                           # if history.move_id.state =='posted':
                            if lis.depreciation_date >=self.start_date and lis.depreciation_date <=self.end_date:
                                month_deprecation_amount +=lis.amount
                                
                    month_balance +=month_deprecation_amount
                    
                    sheet.write(rowx, 15, month_deprecation_amount,data_right)
                    if line.state == 'close':
                        write_off = 0.0
                        self._cr.execute("""SELECT
                               SUM(l.debit-l.credit) AS amount
                            FROM
                                account_move_line l
                                left join account_move am
                                on am.id = l.move_id
                            WHERE
                                l.asset_id = %s
                                and am.date <= %s GROUP BY l.asset_id """, (line.id,self.end_date))
                        res=self._cr.dictfetchall()
                        if res !=[]:
                            for lines in res:
                                write_off = lines['amount']
                                
                        #print("aaaaaaaaaaaaaaaaaaaaaaaaaa",write_off_amount,total_amount,line.name,deprecation_amounts,month_deprecation_amount,deprecation_amount)
                        if round(write_off_amount,2) == round(total_amount,2):
                            if deprecation_amounts > 0.0:
                                write_off_amount = month_deprecation_amount + deprecation_amounts
                            else:
                                write_off_amount = month_deprecation_amount + deprecation_amount
                        else:
                            for dep in line.depreciation_line_ids:
                                if dep.move_check == True:
                                    if dep.depreciation_date >= self.start_date and dep.depreciation_date<= self.end_date:
                                            if deprecation_amounts >0.0:
                                                write_off_amount = month_deprecation_amount + deprecation_amounts
                                            else:
                                                write_off_amount = month_deprecation_amount + deprecation_amount
                                    else:
                                            write_off_amount = 0.0
                                else:
                                    if deprecation_amounts > 0.0:
                                        write_off_amount = month_deprecation_amount + deprecation_amount
                                    else:
                                        write_off_amount = month_deprecation_amount + deprecation_amount
                        
                    
                    if line.state == 'close':
                        if line.scrap_date <= self.start_date:
                            sheet.write(rowx, 16, 0.0,data_right)
                            #drop_balance = 0.0
                        else:
                            sheet.write(rowx, 16, write_off_amount,data_right)
                            drop_balance += write_off_amount
                    else:
                        sheet.write(rowx, 16, write_off_amount,data_right)
                        drop_balance +=write_off_amount
                    #print("aaaaaaaaaaaaaaaaaaaaaaaa",write_off_amount,deprecation_amounts,month_deprecation_amount)
                    if deprecation_amounts >0.0:
                        last_amount = deprecation_amounts + month_deprecation_amount-write_off_amount
                    else:
                        last_amount = deprecation_amount + month_deprecation_amount-write_off_amount
                    sheet.write(rowx, 17, last_amount,data_right)
                    dep_balance +=last_amount
                    if line.state == 'close':
                        bal_amounts = 0.0
                        for dep in line.depreciation_line_ids:
                            if dep.move_check == True:
                                if dep.depreciation_date >= self.start_date and dep.depreciation_date<=self.end_date:
                                    bal_amounts += dep.amount
                        act_amountd = line.value - bal_amounts
                        if act_amountd == 0.0:
                            balance_amount = 0.0
                        else:
                            if write_off_amount > 0.0:
                                balance_amount = total_amount
                            else:
                                balance_amount = total_amount-last_amount
                        
                    else:
                        #balance_amount = total_amount-last_amount
                        if write_off_amount > 0.0:
                            balance_amount = 0.0
                        else:
                            balance_amount = total_amount-last_amount
                    sheet.write(rowx, 18, balance_amount,data_right)
                    total_balance_amount += balance_amount
                    rowx +=1
                
            sheet.write_merge(rowx, rowx, 0, 5, 'НИЙТ',data_right)
            sheet.write(rowx, 6, first_qty,data_right)
            sheet.write(rowx, 7, first_balance,data_right)
            sheet.write(rowx, 8, income_qty,data_right)
            sheet.write(rowx, 9, income_balance,data_right)
            sheet.write(rowx, 10, expense_qty,data_right)
            sheet.write(rowx, 11, expense_balance,data_right)
            sheet.write(rowx, 12, last_qty,data_right)
            sheet.write(rowx, 13, last_balance,data_right)
            sheet.write(rowx, 14, in_dep_balance,data_right)
            sheet.write(rowx, 15, month_balance,data_right)
            sheet.write(rowx, 16, drop_balance,data_right)
            sheet.write(rowx, 17, dep_balance,data_right)
            sheet.write(rowx, 18, total_balance_amount,data_right)
                
    
        sheet.write(rowx + 3, 4, u'Хөтөлсөн нягтлан бодогч....................................../\
                                                 /', ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 180'))
        sheet.write(rowx + 5, 4, u'Хянасан ерөнхий (ахлах) нягтлан бодогч....................................../\
                                                 /', ezxf('font: bold off; align: wrap off, vert centre, horiz left;font: height 180'))
    
        inch = 1000
        sheet.col(0).width = 1 * inch
        sheet.col(1).width = 8 * inch
        sheet.col(2).width = 7 * inch
        sheet.col(3).width = 3 * inch
        sheet.col(4).width = 4 * inch
        sheet.col(5).width = 3 * inch
        sheet.col(6).width = 2 * inch
        sheet.col(7).width = 4 * inch
        sheet.col(8).width = 2 * inch
        sheet.col(9).width = 4 * inch
        sheet.col(10).width = 2 * inch
        sheet.col(11).width = 4 * inch
        sheet.col(12).width = 2 * inch
        sheet.col(13).width = 4 * inch
        sheet.col(14).width = 4 * inch
        sheet.col(15).width = 4 * inch
        sheet.col(16).width = 4 * inch
        sheet.col(17).width = 4 * inch
        sheet.col(18).width = 4 * inch
        sheet.col(19).width = 4 * inch
        sheet.row(3).height = 350
        sheet.row(8).height = 700

        return {'data':book, 'directory_name':u'Үндсэн хөрөнгийн дэлгэрэнгүй тайлан',
                'attache_name':'Үндсэн хөрөнгийн дэлгэрэнгүй тайлан'}
    