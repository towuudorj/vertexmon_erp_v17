# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta, datetime
import xlwt, json
from odoo.tools import date_utils
import io
import json
import xlsxwriter

class ProductSummaryReport(models.TransientModel):
    """
        Барааны материалын хураангуй тайлан
    """
    _name = "product.summary.report"
    _description = "Stock summary Report - Mongolia"
    
    
    
    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                default=lambda self: self.env.user.company_id)
    is_transection = fields.Boolean(string=u'Гүйлгээтэй эсэх', default=True)
    is_warehouse = fields.Boolean(string=u'Агуулахаар татах', default=True)
    location_ids = fields.Many2one('stock.location', string=u'Байрлал')
    start_date = fields.Date(string=u'Эхлэх огноо', required=True,
                                    default=fields.Date.context_today)
    end_date = fields.Date(string=u'Дуусах огноо', required=True,
                                    default=fields.Date.context_today)
    categ_id = fields.Many2one('product.category', string=u'Барааны ангилал')
    product_id = fields.Many2one('product.product', string=u'Бараа')
    warehouse_ids = fields.Many2many('stock.warehouse','stock_warehouse_product_summary_rel','report_id','warehouse_ids', string=u'Агуулах')
    


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'location_ids':self.location_ids.ids,
            'warehouse_ids': self.warehouse_ids.ids,
            'categ_id':self.categ_id.id,
            'product_id': self.product_id.id,
            'is_transection':self.is_transection,
            'is_warehouse':self.is_warehouse

        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'product.summary.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'account_move'}
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
        txt_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'bold': True
                                })
        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        data_left_bold = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'bold': True,
                                    })
        
        data_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        data_center_bold = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'bold': True,
                                    })


        product_obj = self.env['product.product']
        category_obj = self.env['product.category']
        category_id = False
        product_id = False
        if data['categ_id']:
            category_id = data['categ_id']
        if data['product_id']:
            product_id = data['product_id']

        
        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' %(data['company_name']), head_title)
        
        sheet.merge_range('A2:M2', u'Барааны материалын товчоо тайлан', head_title)
        
        sheet.merge_range('J3:M3', u'Тайлант хугацаа: %s - %s'%(data['start_date'],data['end_date']), head_title )

        rowx = 4
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 20, 15)

        sheet.merge_range('A%s:A%s'%(rowx, rowx+1), u'Д/д', data_center_bold)
        sheet.merge_range('B%s:B%s'%(rowx, rowx+1), u'Барааны нэр', data_center_bold)
        sheet.merge_range('C%s:C%s'%(rowx, rowx+1), u'Барааны код', data_center_bold)
        sheet.merge_range('D%s:D%s'%(rowx, rowx+1), u'Дотоод код', data_center_bold)
        sheet.merge_range('E%s:E%s'%(rowx, rowx+1), u'Барааны хэмжих нэгж', data_center_bold)
        sheet.merge_range('F%s:G%s'%(rowx, rowx), u'Барааны эхний үлдэгдэл', data_center_bold)
        sheet.write('F%s'%(rowx+1), u'Тоо', data_center_bold)
        sheet.write('G%s'%(rowx+1), u'Нийт өртөг', data_center_bold)
        sheet.merge_range('H%s:I%s'%(rowx, rowx), u'Барааны орлого', data_center_bold)
        sheet.write('H%s'%(rowx+1), u'Тоо', data_center_bold)
        sheet.write('I%s'%(rowx+1), u'Нийт өртөг', data_center_bold)
        sheet.merge_range('J%s:K%s'%(rowx, rowx), u'Барааны зарлага', data_center_bold)
        sheet.write('J%s'%(rowx+1), u'Тоо', data_center_bold)
        sheet.write('K%s'%(rowx+1), u'Нийт өртөг', data_center_bold)
        sheet.merge_range('L%s:M%s'%(rowx, rowx), u'Барааны эцсийн үлдэгдэл', data_center_bold)
        sheet.write('L%s'%(rowx+1), u'Тоо', data_center_bold)
        sheet.write('M%s'%(rowx+1), u'Нийт өртөг', data_center_bold)
        

        rowx += 2

                    

        
        wh_obj = self.env['stock.warehouse']
        loc_obj = self.env['stock.location']
        loc_ids = []

        rowx = 6
        
        if data['is_warehouse'] == True:
            if len(data['warehouse_ids'])==1:
                wh_id = wh_obj.browse(data['warehouse_ids'][0])
                loc_ids.append(wh_id.lot_stock_id.id)
            else:

                for wh in data['warehouse_ids']:
                    wh_id = wh_obj.browse(wh)
                    for li in wh_id:
                        loc_ids.append(li.lot_stock_id.id)
            print ("loggg",loc_ids)
            
            #loc_id = wh_id.lot_stock_id.id
            # if len(str(loc_id))==1:
            #    loc_ids.append(loc_id)
            #else:
            #    if loc_id:
            #        for line in loc_id:
            #            loc_ids.append(line.id)
            #            if line.child_ids:
            #                for lin in line.child_ids:
            #                    loc_ids.append(lin.id)
            #                    if lin.child_ids:
            #                        for lins in lin.child_ids:
            #                            loc_ids.append(lins.id)
        else:
            loc_ids.append(data['location_ids'])
        
        for wht in loc_ids:
            
            datas = False
            purchase_income = []
            customer_income = []
            sale_expense = []
            customer_expense = []
            internal_income = []
            internal_expense = []
            manu_income = []
            expense = []
            f_income = []
            f_expense = []
            sale_expo = []
            product = []
            num = 0
            f_standard_price = 0.0
            f_list_price = 0.0
            total_income_pur_qty = 0.0
            total_income_manu_qty = 0.0
            total_income_oth_qty = 0.0
            total_expense_sale_qty= 0.0
            total_expense_manu_qty = 0.0
            total_qty_income_qty = 0.0
            total_end_oth_qty = 0.0
            total_end_manu_qty = 0.0
            total_expense_qty = 0.0
            total_qty_exp_qty = 0.0
            total_manu_income_qty = 0.0
            total_income_list_price = 0.0
            f_total_qty = 0.0
            total_end_qty = 0.0
            total_income_qty = 0.0
            total_oth_qty = 0.0
            total_income_cus_qty = 0.0
            total_expense_cust_qty = 0.0
            total_qty = 0.0
            total_income_int_qty = 0.0
            total_expo_qty = 0.0
            total_exp_int_qty = 0.0
            total_price_unit = 0.0
            total_sum_price = 0.0
            total_all_price = 0.0
            products = False
            wh = self.env['stock.location'].browse(wht)
            if product_id:
                product = product_obj.search([('id','=',product_id)],order='name asc').id
            else:
                if category_id:
                    categ_id = category_obj.search( [('parent_id','=',category_id)])
                    if categ_id:
                        for categ in categ_id:
                            categ_ids = category_obj.search( [('parent_id','=',categ.id)])
                            if categ_ids:
                                for cats in categ_ids:
                                    categ_idss = category_obj.search( [('parent_id','=',cats.id)])
                                    if categ_idss:
                                        for catss in categ_idss:
                                            product_ids = product_obj.search([('categ_id','=',catss.id)],order='name asc')
                                            for pr in product_ids:
                                                product.append(pr.id)
                    else:
                        product_ids = product_obj.search([('categ_id','=',category_id)],order='name asc')
                        for pr in product_ids:
                            product.append(pr.id)
                
                else:
                    if data['is_transection'] == True:
                        if len(loc_ids)==1:
                            self._cr.execute("""select mv.product_id from stock_move as mv 
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                left join stock_location as src_id on mv.location_id = src_id.id 
                                where src_id.id = %s  or dest_id.id = %s group by mv.product_id"""%(wh.id,wh.id))
                            products = self._cr.dictfetchall()
                            if products:
                                for line in products:
                                    product.append(line['product_id'])
                        else:
                            self._cr.execute("""select mv.product_id from stock_move as mv 
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                left join stock_location as src_id on mv.location_id = src_id.id 
                                where src_id.id = %s  or dest_id.id = %s group by mv.product_id"""%(wh.id,wh.id))
                            products = self._cr.dictfetchall()
                            if products:
                                for line in products:
                                    product.append(line['product_id'])
                    else:
                        product_ids = product_obj.search([],order='name asc')
                        for pr in product_ids:
                            product.append(pr.id)


            income = []
            expense = []
            f_balance = []
            move_line_obj = self.env['account.move.line']
            journal_obj = self.env['account.journal']
            journal = journal_obj.search([('type','=','opening'),('company_id','=',data['company_id'])],limit=1)
            f_account_ids = 2930
            income_ids = 2930
            expense_ids = 2930
            
            if product_id !=False and f_account_ids !=False:          
                #Эхний үлдэгдэл
                # Барааны орлого
                self._cr.execute("""select ml.debit, ml.credit, ml.quantity, ml.product_id from 
                    account_move_line as ml left join account_move as am on am.id = ml.move_id 
                    left join stock_picking as sp on sp.name = am.name
                    left join stock_move as mv on mv.picking_id = sp.id
                    where sp.location_dest_id = %s and am.company_id = %s
                    and am.date = '%s' and ml.product_id = %s and am.journal_id = %s
                    group by ml.debit, ml.credit, ml.quantity, ml.product_id
                    """%(wh.id,data['company_id'],data['start_date'],product_id,journal.id))
                f_balance = self._cr.dictfetchall()
                print ("f_balance",f_balance)
                #move_line_id = move_line_obj.search( [('account_id','=',f_account_ids),('company_id','=',data['company_id']),('date','<=',data['start_date']),('product_id','=',product_id),('journal_id','=',journal.id)])
                #if move_line_id:
                #    f_balance = move_line_id
                
                
                if income_ids !=False:
                        # Барааны худалдан авалтын орлого                  
                        income_move_line_id = move_line_obj.search([('account_id','=',income_ids),('company_id','=',data['company_id']),('date','>=',data['start_date']),('date','<=',data['end_date']),('product_id','=',product_id),('journal_id','!=',journal.id)])
                        if income_move_line_id:
                            income = income_move_line_id


                if expense_ids !=False:
                    # Барааны зарлага
                    expense_move_line_id = move_line_obj.search([('account_id','=',expense_ids),('company_id','=',data['company_id']),('date','>=',data['start_date']),('date','<=',data['end_date']),('product_id','=',product_id),('journal_id','!=',journal.id)])            
                    if expense_move_line_id:
                        expense = expense_move_line_id
                
            elif product_id == False and f_account_ids !=False:
                    #Эхний үлдэгдэл
                    #print("laaaa",f_account_ids.id)
                    if len(str(f_account_ids))==1:
                        # Барааны орлого
                        move_line_id = move_line_obj.search( [('account_id','=',f_account_ids),('company_id','=',data['company_id']),('date','<=',data['start_date']),('journal_id','=',journal.id)])
                        if move_line_id:
                            f_balance = move_line_obj.browse( move_line_id)
                        
                        
                        if income_ids !=False:
                            # Барааны худалдан авалтын орлого
                            income_move_line_id = move_line_obj.search( [('account_id','=',income_ids),('company_id','=',data['company_id']),('date','>=',data['start_date']),('date','<=',data['end_date']),('journal_id','!=',journal.id)])
                            if income_move_line_id:
                                income =income_move_line_id
            
                                
                        if expense_ids !=False:
                            # Барааны зарлага
                            expense_move_line_id = move_line_obj.search( [('account_id','=',expense_ids),('company_id','=',data['company_id']),('date','>=',data['start_date']),('date','<=',data['end_date']),('journal_id','!=',journal.id)])            
                            if expense_move_line_id:
                                expense = expense_move_line_id
                    else:
                        self._cr.execute("""SELECT 
                                            ml.debit, 
                                            ml.credit, 
                                            ml.quantity, 
                                            ml.product_id
                                        FROM account_move_line AS ml
                                        LEFT JOIN account_move AS am 
                                            ON am.id = ml.move_id
                                        LEFT JOIN product_product AS pp 
                                            ON pp.id = ml.product_id
                                        LEFT JOIN product_template AS pt 
                                            ON pt.id = pp.product_tmpl_id
                                        LEFT JOIN stock_move_line AS mv 
                                            ON ml.name = (mv.reference || ' - ' || pt.name)
                                        WHERE mv.location_dest_id = %s
                                        AND am.company_id = %s
                                        AND am.date = '%s'
                                        AND am.journal_id = %s
                                        GROUP BY 
                                            ml.debit, 
                                            ml.credit, 
                                            ml.quantity, 
                                            ml.product_id
                            """%(wh.id,data['company_id'],data['start_date'],journal.id))
                        f_balance = self._cr.dictfetchall()
                        print ("f_balance",f_balance,wh.id,journal.id)
                        # Барааны орлого
                        #move_line_id = move_line_obj.search( [('account_id','=',f_account_ids),('company_id','=',data['company_id']),('date','<=',data['start_date']),('journal_id','=',journal.id)])
                        #if move_line_id:
                        #    f_balance = move_line_id
                            
                        
                        if income_ids !=False:
                            # Барааны худалдан авалтын орлого
                            income_move_line_id = move_line_obj.search( [('account_id','=',income_ids),('company_id','=',data['company_id']),('date','>',data['start_date']),('date','<=',data['end_date']),('journal_id','!=',journal.id)])
                            if income_move_line_id:
                                income = income_move_line_id
            
                                
                        if expense_ids !=False:
                            # Барааны зарлага
                            expense_move_line_id = move_line_obj.search( [('account_id','=',expense_ids),('company_id','=',data['company_id']),('date','>',data['start_date']),('date','<=',data['end_date']),('journal_id','!=',journal.id)])            
                            if expense_move_line_id:
                                expense = expense_move_line_id
                    
        
                
                
           

            sheet.merge_range('A%s:K%s'%(rowx,rowx), u'Агуулах: %s'%(wh.name), data_left_bold)
            rowx += 1
            total_end_qty = 0.0
            total_in_qty = 0.0
            total_in_amount = 0.0
            total_exp_qty = 0.0
            total_exp_amount = 0.0
            f_total_balance = 0.0
            f_total_qty = 0.0
            total_all_price = 0.0
            total_sum_price = 0.0
            
            for line in product_obj.browse(product):
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
                        #print ("aaaaaaaaaaaaaa",f_inc)
                        if line.id == f_inc.product_id.id:
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
                                        if exp.account_id.id != p_inc.product_id.categ_id.property_stock_account_input_categ_id.id:
                                            if exp.credit and exp.debit==0.0:
                                                if exp.quantity <0.0:
                                                    expense_qty +=exp.quantity*(-1)
                                                expense_amount +=exp.credit
                                
                            
                end_qty = f_balance_qty+income_qty+purchase_qty-expense_qty
                uom_name = 'Нэгж'
                #if line.uom_id.name=='Unit(s)':
                #    uom_name = u'Нэгж'
                if f_balance_amount > 0.0 and f_balance_qty:
                    f_balance_unit = f_balance_amount/f_balance_qty
                    
                
                if income_amount>0.0 and income_qty>0.0:
                    income_unit = income_amount/income_qty
                
                if purchase_amount >0.0 and purchase_qty >0.0:
                    purchase_unit = purchase_amount/purchase_qty
                
                if expense_amount > 0.0 and expense_qty>0.0:
                    expense_unit = expense_amount/expense_qty

                if end_qty >0.0 and f_balance_amount > 0.0:
                    end_unit = (f_balance_amount+income_amount+purchase_amount-expense_amount)
                uom_name = ''
                if line.uom_id:
                    uom_name = line.uom_id.name
                sheet.write('A%s'%rowx, int(num), data_center)
                sheet.write('B%s'%rowx, u'%s'%line.name, data_left)
                sheet.write('C%s'%rowx, line.barcode or '', data_center)
                sheet.write('D%s'%rowx, line.default_code or '', data_center)
                sheet.write('E%s'%rowx, u'%s'%(uom_name), data_center)
                sheet.write('F%s'%rowx, f_balance_qty, data_right)
                sheet.write('G%s'%rowx, f_balance_amount, data_right)
                sheet.write('H%s'%rowx, income_qty+purchase_qty, data_right)
                sheet.write('I%s'%rowx, income_amount+purchase_amount, data_right)
                sheet.write('J%s'%rowx, expense_qty, data_right)
                sheet.write('K%s'%rowx, expense_amount, data_right)
                
                if end_unit == 0.0:
                    sheet.write('L%s'%rowx, 0.0, data_right)
                else:
                    if end_qty == 0.0:
                        sheet.write('L%s'%rowx, 0.0, data_right)
                    else:
                        sheet.write('L%s'%rowx, end_qty, data_right)
                sheet.write('M%s'%rowx, end_unit, data_right)
                if end_qty == 0.0:
                    total_sum_price +=total_price_unit
                else:
                    total_sum_price +=total_price_unit/end_qty
                total_all_price +=total_price_unit
                
                f_total_qty +=f_balance_qty
                total_end_qty += end_qty
                f_total_balance += f_balance_amount
                total_in_qty += (income_qty + purchase_qty)
                total_in_amount += (income_amount + purchase_amount)
                total_exp_qty += expense_qty
                total_exp_amount += expense_amount
 
                rowx +=1

            sheet.merge_range('A%s:E%s'%(rowx, rowx), u'НИЙТ', data_center)
            sheet.write('F%s'%(rowx), f_total_qty, data_right)
            sheet.write('G%s'%(rowx), f_total_balance, data_right)
            sheet.write('H%s'%(rowx), total_in_qty, data_right)
            sheet.write('I%s'%(rowx), total_in_amount, data_right)
            sheet.write('J%s'%(rowx), total_exp_qty, data_right)
            sheet.write('K%s'%(rowx), total_exp_amount, data_right)
            sheet.write('L%s'%(rowx), total_end_qty, data_right)
            sheet.write('M%s'%(rowx), total_all_price, data_right)
            rowx +=1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()



