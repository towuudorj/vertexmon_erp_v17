# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta, datetime
import xlwt, json
from odoo.tools import date_utils
import io
import json
import xlsxwriter

class ProductStockAccountDetailReport(models.TransientModel):
    """
        Барааны материалын дэлгэрэнгүй тайлан
    """
    _name = "product.stock.account.detail.report"
    _description = "Stock Account Report - Mongolia"
    
    
    company_id = fields.Many2one('res.company', string=u'Компани',readonly=True,
                                default=lambda self: self.env.user.company_id)
    start_date = fields.Date(string=u'Эхлэх огноо',required=True,
                            default=fields.Date.context_today)
    end_date = fields.Date(string=u'Дуусах огноо',required=True,
                            default=fields.Date.context_today)
    category_id = fields.Many2one('product.category', string=u'Барааны ангилал',
                                    required=True)
    product_id = fields.Many2one('product.product', string=u'Бараа')
    is_sale_price = fields.Boolean(string=u'Зарах үнэ харах эсэх')
    is_total_qty = fields.Boolean(string=u'Нийт зарах үнэ харах эсэх')
    acc_pro_id = fields.Many2many('account.account','account_stock_product_detail_rel','acc_pro_id','account_id', string=u'Барааны данс')
    acc_income_pro_id = fields.Many2many('account.account','account_stock_income_product_rel','acc_income_pro_id','account_id', string=u'Барааны орлого')
    acc_expense_pro_id = fields.Many2many('account.account','account_stock_expense_product_rel','acc_expense_pro_id','account_id', string=u'Барааны зарлага')

    

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'categ_id':self.categ_id.id,
            'product_id': self.product_id.id,
            'is_sale_price': self.is_sale_price,
            'is_total_qty':self.is_total_qty,
            'acc_pro_id': self.acc_pro_id.ids,
            'acc_income_pro_id': self.acc_income_pro_id.ids,
            'acc_expense_pro_id': self.acc_expense_pro_id.ids
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'product.stock.account.detail.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'account_stock_product_detail_report',}
        }
    

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({
                                    'align': 'right', 
                                    'font_size': 12
                                    })
        head_title = workbook.add_format({
                                    'align': 'center', 
                                    'font_size': 16,
                                    'bold': True
                                    })
        
        rowx = 1
        sheet.merge_range('A%s:B%s'%(rowx, rowx), u'Байгууллагын нэр: %s' % (self.company_id.name,), ezxf('font:bold on;align:wrap off,vert centre,horiz left;font: height 180'))
        sheet.merge_range('A%s:B%s'%(rowx, rowx), u'Барааны материалын дэлгэрэнгүй тайлан', ezxf('font: bold on; align: wrap off, vert centre, horiz left;font: height 200'))
        sheet.merge_range('A%s:B%s'%(rowx, rowx), u'Тайлант хугацаа: %s - %s'%(self.start_date,self.end_date) , ezxf('font:bold on;align:wrap off,vert centre,horiz right;font: height 180'))
        

        

    
    
    def get_export_data(self):
        ''' Тайлангийн загварыг боловсруулж өгөгдлүүдийг
            тооцоолж байрлуулна.
        '''
        product_obj = self.env['product.product']
        category_obj = self.env['product.category']
        category_id = False
        product_id = False
        f_account_ids = False
        income_ids = False
        expense_ids = False
        if self.acc_pro_id !=[]:
            f_account_ids = self.acc_pro_id
        if self.acc_income_pro_id !=[]:
            income_ids = self.acc_income_pro_id
        if self.acc_expense_pro_id !=[]:
            expense_ids = self.acc_expense_pro_id
        if self.category_id:
            category_id = self.category_id.id
        if self.product_id:
            product_id = self.product_id.id
        
        ezxf = xlwt.easyxf
        styles = self.get_easyxf_styles()
        
        book = xlwt.Workbook(encoding='utf8')

        rowx = 4
        if self.is_sale_price == True:
            sheet.write_merge(rowx, rowx+2, 0, 0, u'Д/д', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+2, 1, 1, u'Барааны нэр', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+2, 2, 2, u'Барааны код', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+2, 3, 3, u'Дотоод код', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+2, 4, 4, u'Барааны хэмжих нэгж', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+1, 5, 7, u'Барааны эхний үлдэгдэл', styles['heading_xf'])
            sheet.write(rowx+2, 5, u'Тоо хэмжээ', styles['heading_xf'])
            sheet.write(rowx+2, 6, u'Зарах үнэ', styles['heading_xf'])
            sheet.write(rowx+2, 7, u'Нийт үнэ', styles['heading_xf'])
            sheet.write_merge(rowx, rowx, 8, 13, u'Барааны орлого', styles['heading_xf'])
            sheet.write_merge(rowx+1, rowx+1, 8, 10, u'Худалдан авалт орлого', styles['heading_xf'])
            sheet.write(rowx+2, 8, u'Тоо хэмжээ', styles['heading_xf'])
            sheet.write(rowx+2, 9, u'Нэгж үнэ', styles['heading_xf'])
            sheet.write(rowx+2, 10, u'Нийт үнэ', styles['heading_xf'])
            sheet.write_merge(rowx+1, rowx+1, 11, 14, u'Бусад орлого', styles['heading_xf'])
            sheet.write(rowx+2, 11, u'Тоо хэмжээ', styles['heading_xf'])
            sheet.write(rowx+2, 12, u'Нэгж үнэ', styles['heading_xf'])
            sheet.write(rowx+2, 13, u'Нийт үнэ', styles['heading_xf'])
            sheet.write(rowx+2, 14, u'Нийт орлогын тоо', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+1, 15, 17, u'Барааны зарлага', styles['heading_xf'])
            sheet.write(rowx+2, 15, u'Тоо хэмжээ', styles['heading_xf'])
            sheet.write(rowx+2, 16, u'Нэгж үнэ', styles['heading_xf'])
            sheet.write(rowx+2, 17, u'Нийт үнэ', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+1, 18, 20, u'Барааны эцсийн үлдэгдэл', styles['heading_xf'])
            sheet.write(rowx+2, 18, u'Тоо хэмжээ', styles['heading_xf'])
            sheet.write(rowx+2, 19, u'Нэгж үнэ', styles['heading_xf'])
            sheet.write(rowx+2, 20, u'Нийт үнэ', styles['heading_xf'])
        else:
            sheet.write_merge(rowx, rowx+2, 0, 0, u'Д/д', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+2, 1, 1, u'Барааны нэр', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+2, 2, 2, u'Барааны код', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+2, 3, 3, u'Дотоод код', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+2, 4, 4, u'Барааны хэмжих нэгж', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+1, 5, 7, u'Барааны эхний үлдэгдэл', styles['heading_xf'])
            sheet.write(rowx+2, 5, u'Тоо хэмжээ', styles['heading_xf'])
            sheet.write(rowx+2, 6, u'Нэгж үнэ', styles['heading_xf'])
            sheet.write(rowx+2, 7, u'Нийт үнэ', styles['heading_xf'])
            sheet.write_merge(rowx, rowx, 8, 13, u'Барааны орлого', styles['heading_xf'])
            sheet.write_merge(rowx+1, rowx+1, 8, 10, u'Худалдан авалт орлого', styles['heading_xf'])
            sheet.write(rowx+2, 8, u'Тоо хэмжээ', styles['heading_xf'])
            sheet.write(rowx+2, 9, u'Нэгж үнэ', styles['heading_xf'])
            sheet.write(rowx+2, 10, u'Нийт үнэ', styles['heading_xf'])
            sheet.write_merge(rowx+1, rowx+1, 11, 14, u'Бусад орлого', styles['heading_xf'])
            sheet.write(rowx+2, 11, u'Тоо хэмжээ', styles['heading_xf'])
            sheet.write(rowx+2, 12, u'Нэгж үнэ', styles['heading_xf'])
            sheet.write(rowx+2, 13, u'Нийт үнэ', styles['heading_xf'])
            sheet.write(rowx+2, 14, u'Нийт орлогын тоо', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+1, 15, 17, u'Барааны зарлага', styles['heading_xf'])
            sheet.write(rowx+2, 15, u'Тоо хэмжээ', styles['heading_xf'])
            sheet.write(rowx+2, 16, u'Нэгж үнэ', styles['heading_xf'])
            sheet.write(rowx+2, 17, u'Нийт үнэ', styles['heading_xf'])
            sheet.write_merge(rowx, rowx+1, 18, 20, u'Барааны эцсийн үлдэгдэл', styles['heading_xf'])
            sheet.write(rowx+2, 18, u'Тоо хэмжээ', styles['heading_xf'])
            sheet.write(rowx+2, 19, u'Нэгж үнэ', styles['heading_xf'])
            sheet.write(rowx+2, 20, u'Нийт үнэ', styles['heading_xf'])
            
            
        rowx += 3
        datas = False
        income = []
        expense = []
        f_balance = []
        move_line_obj = self.env['account.move.line']
        journal_obj = self.env['account.journal']
        journal = journal_obj.search([('type','=','opening'),('company_id','=',self.company_id.id)],limit=1)
        
        if product_id !=False and f_account_ids !=False:          
            #Эхний үлдэгдэл
            # Барааны орлого
            

            
            move_line_id = move_line_obj.search( [('account_id','in',f_account_ids.ids),('company_id','=',self.company_id.id),('date','<=',self.start_date),('product_id','=',product_id),('journal_id','=',journal.id)])
            if move_line_id:
                # Нээлтийн журналд жил бүр шинэ бичилт нэмэгддэг тул хамгийн сүүлийн
                # (start_date-аас өмнөх хамгийн ойрын) бичилтийг л авна, эс бөгөөс
                # өмнөх бүх жилийн эхний үлдэгдэл давхар нэмэгдэнэ.
                opening_date = max(move_line_id.mapped('date'))
                f_balance = move_line_id.filtered(lambda l: l.date == opening_date)
            
            
            if income_ids !=False:
                    # Барааны худалдан авалтын орлого                  
                    income_move_line_id = move_line_obj.search([('account_id','in',income_ids.ids),('company_id','=',self.company_id.id),('date','>=',self.start_date),('date','<=',self.end_date),('product_id','=',product_id),('journal_id','!=',journal.id)])
                    if income_move_line_id:
                        income = income_move_line_id


            if expense_ids !=False:
                # Барааны зарлага
                expense_move_line_id = move_line_obj.search([('account_id','in',expense_ids.ids),('company_id','=',self.company_id.id),('date','>=',self.start_date),('date','<=',self.end_date),('product_id','=',product_id),('journal_id','!=',journal.id)])            
                if expense_move_line_id:
                    expense = expense_move_line_id
            
        elif product_id == False and f_account_ids !=False:
            #Эхний үлдэгдэл
            #print("laaaa",f_account_ids.id)
            if len(f_account_ids)==1:
                # Барааны орлого
                move_line_id = move_line_obj.search( [('account_id','=',f_account_ids.id),('company_id','=',self.company_id.id),('date','<=',self.start_date),('journal_id','=',journal.id)])
                if move_line_id:
                    opening_date = max(move_line_id.mapped('date'))
                    f_balance = move_line_id.filtered(lambda l: l.date == opening_date)
                
                
                if income_ids !=False:
                    # Барааны худалдан авалтын орлого
                    income_move_line_id = move_line_obj.search( [('account_id','=',income_ids.id),('company_id','=',self.company_id.id),('date','>=',self.start_date),('date','<=',self.end_date),('journal_id','!=',journal.id)])
                    if income_move_line_id:
                        income =income_move_line_id
    
                        
                if expense_ids !=False:
                    # Барааны зарлага
                    expense_move_line_id = move_line_obj.search( [('account_id','=',expense_ids.id),('company_id','=',self.company_id.id),('date','>=',self.start_date),('date','<=',self.end_date),('journal_id','!=',journal.id)])            
                    if expense_move_line_id:
                        expense = expense_move_line_id
            else:
                # Барааны орлого
                move_line_id = move_line_obj.search( [('account_id','in',f_account_ids.ids),('company_id','=',self.company_id.id),('date','<=',self.start_date),('journal_id','=',journal.id)])
                if move_line_id:
                    opening_date = max(move_line_id.mapped('date'))
                    move_line_id = move_line_id.filtered(lambda l: l.date == opening_date)
                    f_balance = move_line_id
                
                
                if income_ids !=False:
                    # Барааны худалдан авалтын орлого
                    income_move_line_id = move_line_obj.search( [('account_id','in',income_ids.ids),('company_id','=',self.company_id.id),('date','>=',self.start_date),('date','<=',self.end_date),('journal_id','!=',journal.id)])
                    if income_move_line_id:
                        income = income_move_line_id
    
                        
                if expense_ids !=False:
                    # Барааны зарлага
                    expense_move_line_id = move_line_obj.search( [('account_id','in',expense_ids.ids),('company_id','=',self.company_id.id),('date','>=',self.start_date),('date','<=',self.end_date),('journal_id','!=',journal.id)])            
                    if expense_move_line_id:
                        expense = expense_move_line_id
                
            
            
        product = False
        if product_id:
            product = product_obj.search([('id','=',product_id),('categ_id','=',category_id),('active','in',(True,False))],order='name asc')
        else:
            categ_id = category_obj.search([('parent_id','=',category_id)])
            if categ_id:
                categ_ids = category_obj.search([('parent_id','in',tuple(categ_id.ids))])
                if categ_ids:
                    categ_idss = category_obj.search([('parent_id','in',tuple(categ_ids.ids))])
                    if categ_idss:
                        product = product_obj.search([('categ_id','in',tuple(categ_idss.ids))],order='name asc')
                    else:
                        product = product_obj.search([('categ_id','in',tuple(categ_ids.ids))],order='name asc')
                else:
                    product = product_obj.search([('categ_id','in',tuple(categ_id.ids))],order='name asc')
            else:
                product = product_obj.search([('categ_id','=',category_id)],order='name asc')
        num = 0
        f_total_amount = 0.0
        f_total_unit = 0.0
        total_income_qty = 0.0
        total_income_amount= 0.0
        total_income_unit = 0.0
        
        total_purchase_qty = 0.0
        total_purchase_amount = 0.0
        total_purchase_unit = 0.0
        
        total_ref_income_qty = 0.0
        total_ref_income_amount = 0.0
        total_ref_income_unit = 0.0
        
        total_expense_qty = 0.0
        total_expense_amount = 0.0
        total_expense_unit = 0.0
        
        total_ref_expense_qty = 0.0
        total_ref_expense_amount = 0.0
        total_ref_expense_unit = 0.0
        
        total_act_qty = 0.0
        total_act_amount = 0.0
        total_act_unit = 0.0
        
        total_end_amount = 0.0
        total_end_unit = 0.0
        total_income_list_price = 0.0
        f_total_qty = 0.0
        total_end_qty = 0.0
        end_total_standard_price = 0.0
        end_total_list_price = 0.0
        for line in product:
            num +=1
            f_balance_qty = 0.0
            f_balance_amount = 0.0
            f_balance_unit = 0.0
            f_expense_qty = 0.0
            f_expense_price = 0.0
            
            purchase_qty = 0.0
            purchase_amount = 0.0
            purchase_unit = 0.0
            
            income_qty = 0.0
            income_amount = 0.0
            income_unit = 0.0
            ref_income_amount = 0.0
            ref_income_qty = 0.0
            ref_income_unit = 0.0
            expense_qty = 0.0
            expense_amount = 0.0
            expense_unit = 0.0
            ref_expense_qty = 0.0
            ref_expense_amount = 0.0
            ref_expense_unit = 0.0
            act_amount = 0.0
            act_qty = 0.0
            act_unit = 0.0
            end_qty =0.0
            end_unit = 0.0
            seri = ''
            if f_balance!=[]:
                for f_inc in f_balance:
                    if line.id==f_inc.product_id.id:
                        if f_inc.move_id.state !='cancel':
                            if f_inc.move_id.state !='draft':
                                #if f_inc.quantity != 0.0:
                                    if f_inc.credit != f_inc.debit:
                                        if f_inc.debit:
                                            f_balance_qty += f_inc.quantity
                                        if f_inc.credit:
                                            f_balance_qty -= f_inc.quantity
                                        f_balance_amount +=f_inc.debit
                                    else:
                                        f_balance_qty += f_inc.quantity
                                        f_balance_amount +=f_inc.debit
                        
            if income!=[]:
                for p_inc in income:
                    if line.id==p_inc.product_id.id:
                        if p_inc.move_id.state !='cancel':
                            if p_inc.move_id.state !='draft':
                                #if p_inc.quantity != 0.0:
                                if p_inc.account_id.id == p_inc.product_id.categ_id.property_stock_account_input_categ_id.id:
                                    if  p_inc.debit == 0.0 and  p_inc.credit >0.0 :
                                        purchase_qty += p_inc.quantity
                                        purchase_amount +=p_inc.credit
                                        income_qty -= p_inc.quantity
                                        income_amount -=p_inc.credit
                                else:
                                    if  p_inc.debit > 0.0 and  p_inc.credit == 0.0:
                                        income_qty += p_inc.quantity
                                        income_amount +=p_inc.debit
                            
            if expense !=[]:
                for exp in expense:
                    if line.id==exp.product_id.id:
                        if exp.move_id.state !='cancel':
                            if exp.move_id.state !='draft':
                          #      if exp.quantity != 0.0:
                                if exp.account_id.id != exp.product_id.categ_id.property_stock_account_input_categ_id.id:
                                    if exp.credit and exp.debit==0.0:
                                        if exp.quantity <0.0:
                                            expense_qty +=exp.quantity*(-1)
                                        expense_amount +=exp.credit
                            
                        
            end_qty = f_balance_qty+income_qty+purchase_qty-expense_qty
            uom_name = ''
            if line.uom_id.name=='Unit(s)':
                uom_name = u'Нэгж'
            if f_balance_amount > 0.0 and f_balance_qty:
                f_balance_unit = f_balance_amount/f_balance_qty
                
            
            if income_amount>0.0 and income_qty>0.0:
                income_unit = income_amount/income_qty
            
            if purchase_amount >0.0 and purchase_qty >0.0:
                purchase_unit = purchase_amount/purchase_qty
            
            if expense_amount > 0.0 and expense_qty>0.0:
                expense_unit = expense_amount/expense_qty

            if end_qty >0.0 and f_balance_amount > 0.0:
                end_unit = (f_balance_amount+income_amount+purchase_amount-expense_amount)/end_qty
                
            
            
            
                
            sheet.write(rowx, 0, u'%s'%num, data_center)
            sheet.write(rowx, 1, u'%s'%line.name, data_left)
            sheet.write(rowx, 2, u'%s'%line.barcode or '', data_center)
            sheet.write(rowx, 3, u'%s'%line.default_code or '', data_center)
            sheet.write(rowx, 4, u'%s'%(uom_name), data_center)
            sheet.write(rowx, 5, f_balance_qty, data_right)
            sheet.write(rowx, 6, f_balance_unit, data_right)
            sheet.write(rowx, 7, f_balance_amount, data_right)
            
            sheet.write(rowx, 8, purchase_qty, data_right)
            sheet.write(rowx, 9, purchase_unit, data_right)
            sheet.write(rowx, 10, purchase_amount, data_right)
            sheet.write(rowx, 11, income_qty, data_right)
            sheet.write(rowx, 12, income_unit, data_right)
            sheet.write(rowx, 13, income_amount, data_right)
            sheet.write(rowx, 14, expense_qty, data_right)
            sheet.write(rowx, 15, expense_unit, data_right)
            sheet.write(rowx, 16, expense_amount, data_right)
            sheet.write(rowx, 17, end_qty, data_right)
            sheet.write(rowx, 18, end_unit, data_right)
            sheet.write(rowx, 19, f_balance_amount+income_amount+purchase_amount-expense_amount, data_right)
            f_total_qty +=f_balance_qty
            f_total_unit +=f_balance_unit
            f_total_amount +=f_balance_amount
            total_income_qty +=income_qty
            total_income_amount +=income_amount
            total_income_unit +=income_unit
            
            total_ref_income_qty += ref_income_qty
            total_ref_income_unit += ref_income_unit
            total_ref_income_amount += ref_income_amount
            
            total_purchase_amount += purchase_amount
            total_purchase_qty +=purchase_qty
            total_purchase_unit +=purchase_unit
            
            total_expense_qty +=expense_qty
            total_expense_amount +=expense_amount
            total_expense_unit +=expense_unit
            
            total_ref_expense_qty +=ref_expense_qty
            total_ref_expense_amount +=ref_expense_amount
            total_ref_expense_unit +=ref_expense_unit
            
            total_act_qty +=act_qty
            total_act_amount +=act_amount
            total_act_unit +=act_unit
            
            total_end_qty +=end_qty
            total_end_amount +=(f_balance_amount+income_amount+purchase_amount-expense_amount)
            total_end_unit +=end_unit
            
            
            rowx +=1
        sheet.write_merge(rowx, rowx, 0, 4, u'НИЙТ', data_center)
        sheet.write(rowx, 5, f_total_qty, data_right)
        sheet.write(rowx, 6, f_total_unit, data_right)
        sheet.write(rowx, 7, f_total_amount, data_right)
        sheet.write(rowx, 8, total_purchase_qty, data_right)
        sheet.write(rowx, 9, total_purchase_unit, data_right)
        sheet.write(rowx, 10, total_purchase_amount, data_right)
        sheet.write(rowx, 11, total_income_qty, data_right)
        sheet.write(rowx, 12, total_income_unit, data_right)
        sheet.write(rowx, 13, total_income_amount, data_right)
        sheet.write(rowx, 14, total_expense_qty, data_right)
        sheet.write(rowx, 15, total_expense_unit, data_right)
        sheet.write(rowx, 16, total_expense_amount, data_right)
        sheet.write(rowx, 17, total_end_qty, data_right)
        sheet.write(rowx, 18, total_end_unit, data_right)
        sheet.write(rowx, 19, total_end_amount, data_right)

        inch = 1000
        sheet.col(0).width = 1 * inch
        sheet.col(1).width = 12 * inch
        sheet.col(2).width = 4 * inch
        sheet.col(3).width = 2 * inch
        sheet.col(4).width = 2 * inch
        sheet.col(5).width = 3 * inch
        sheet.col(6).width = 3 * inch
        sheet.col(7).width = 2 * inch
        sheet.col(8).width = 3 * inch
        sheet.col(9).width = 3 * inch
        sheet.col(10).width = 2 * inch
        sheet.col(11).width = 3 * inch
        sheet.col(12).width = 3 * inch
        sheet.col(13).width = 2 * inch
        sheet.col(14).width = 3 * inch
        sheet.col(15).width = 3 * inch
        sheet.row(4).height = 640

        return {'data':book, 'directory_name':u'Борлуулалт хийгдээгүй барааны тайлан',
                'attache_name':'Борлуулалт хийгдээгүй барааны тайлан'}