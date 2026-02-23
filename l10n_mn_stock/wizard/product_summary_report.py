# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta, datetime, time
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
    location_ids = fields.Many2one('stock.location', string=u'Байрлал')
    start_date = fields.Date(string=u'Эхлэх огноо', required=True,
                                    default=fields.Date.context_today)
    end_date = fields.Date(string=u'Дуусах огноо', required=True,
                                    default=fields.Date.context_today)
    categ_id = fields.Many2one('product.category', string=u'Барааны ангилал')
    product_id = fields.Many2one('product.product', string=u'Бараа')
    warehouse_ids = fields.Many2many('stock.warehouse','stock_warehouse_product_summary_rel','report_id','warehouse_ids', string=u'Агуулах')
    type = fields.Selection([('quantity',u'Тоогоор'),
                             ('cost',u'Өртгөөр')], string=u'Төрөл', required=True)
    


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'date_from': self.start_date,
            'date_to': self.end_date,
            'location_ids':self.location_ids.ids,
            'warehouse_ids': self.warehouse_ids.ids,
            'categ_id':self.categ_id.id,
            'product_id': self.product_id.id,
            'type':self.type,

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
                                    'text_wrap': True,
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


        
        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' %(data['company_name']), head_title)
        sheet.merge_range('A2:I2', u'Барааны материалын товчоо тайлан', head_title)

        rowx = 4
        sheet.set_column(1, 1, 40)
        sheet.set_column(2, 20, 15)
        
        location_ids = []            
        warehouse_ids = data.get('warehouse_ids') or []
        if isinstance(warehouse_ids, (list, tuple)) and warehouse_ids:
            locations = self.env['stock.location'].search([
                ('warehouse_id', 'in', tuple(warehouse_ids))
            ])
            location_ids = locations.ids
        
        product_obj = self.env['product.product']
        if data['product_id'] and not data['categ_id']:
            product_ids = product_obj.search(data['product_id'])
        elif not data['product_id'] and data['categ_id']:
            product_ids = product_obj.search([('categ_id','=',data['categ_id'])])
        elif not data['product_id'] and not data['categ_id']:
            product_ids = product_obj.search([])
        
        if data['type'] == 'cost':
            sheet.merge_range('J3:M3', u'Тайлант хугацаа: %s - %s'%(data['date_from'],data['date_to']), head_title )
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
            
            
            count = 0
            rowx +=2
            
            total_f_bal_qty = 0
            total_f_bal_price = 0
            total_f_in_qty = 0
            total_f_in_price = 0
            total_in_qty = 0
            total_in_price = 0
            total_ex_qty = 0
            total_ex_price = 0
            total_last_qty = 0
            total_last_price = 0
            total_f_ex_qty = 0
            total_f_ex_price = 0
            
            date_from = data['date_from']

            if isinstance(date_from, str):
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            
            date_to_dt_max = datetime.combine(date_from, time.max)
            date_to_dt_min = datetime.combine(date_from, time.min)
            
            for pro in product_ids:
                if location_ids:
                    f_query_income = """
                        SELECT
                            mv.product_id,
                            SUM(svl.quantity) AS qty,
                            AVG(svl.unit_cost) AS price
                        FROM stock_valuation_layer svl
                        JOIN stock_move mv ON mv.id = svl.stock_move_id
                        JOIN stock_location sl ON mv.location_id = sl.id
                        JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date <= %s
                          AND dest.id IN %s
                          AND mv.product_id = %s
                          AND mv.company_id = %s
                          AND sl.usage = 'inventory'
                          AND dest.usage = 'internal'
                          AND svl.product_id = mv.product_id
                          AND svl.create_date = mv.date
                        GROUP BY mv.product_id
                    """
                
                    self._cr.execute(
                        f_query_income,
                        (date_to_dt_max, tuple(location_ids), pro.id, data['company_id'])
                    )
                    f_income = self._cr.dictfetchall()
                    
                    
                    f_query_expense = """
                        SELECT
                            mv.product_id,
                            SUM(svl.quantity) AS qty,
                            AVG(svl.unit_cost) AS price
                        FROM stock_valuation_layer svl
                        JOIN stock_move mv ON mv.id = svl.id
                        JOIN stock_location sl ON mv.location_id = sl.id
                        JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date <= %s
                          AND sl.id IN %s
                          AND mv.product_id = %s
                          AND mv.company_id = %s
                          AND sl.usage = 'internal'
                          AND dest.usage = 'inventory'
                          AND svl.product_id = mv.product_id
                          AND svl.create_date = mv.date
                        GROUP BY mv.product_id
                    """
                
                    self._cr.execute(
                        f_query_expense,
                        (date_to_dt_max, tuple(location_ids), pro.id, data['company_id'])
                    )
                    f_expense = self._cr.dictfetchall()
                    
                    
                    query_income = """
                        SELECT
                            mv.product_id,
                            SUM(svl.quantity) AS qty,
                            AVG(svl.unit_cost) AS price
                        FROM stock_valuation_layer svl
                        JOIN stock_move mv ON svl.stock_move_id = mv.id
                        JOIN stock_location sl ON mv.location_id = sl.id
                        JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date > %s
                          AND mv.date <= %s
                          AND dest.id IN %s
                          AND mv.product_id = %s
                          AND mv.company_id = %s
                          AND sl.usage IN ('supplier','customer','inventory','production','internal')
                          AND dest.usage = 'internal'
                          AND svl.product_id = mv.product_id
                        GROUP BY mv.product_id
                    """
                
                    self._cr.execute(
                        query_income,
                        (date_to_dt_min, data['date_to'], tuple(location_ids), pro.id, data['company_id'])
                    )
                    income = self._cr.dictfetchall()
                    
                    
                    query_expense = """
                        SELECT
                            mv.product_id,
                            SUM(svl.quantity) AS qty,
                            AVG(svl.unit_cost) AS price
                        FROM stock_valuation_layer svl
                        JOIN stock_move mv ON svl.stock_move_id = mv.id
                        JOIN stock_location sl ON mv.location_id = sl.id
                        JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date > %s
                          AND mv.date <= %s
                          AND sl.id IN %s
                          AND mv.product_id = %s
                          AND mv.company_id = %s
                          AND sl.usage = 'internal'
                          AND dest.usage IN ('customer','supplier','inventory','production','internal')
                          AND svl.product_id = mv.product_id
                        GROUP BY mv.product_id
                    """
                
                    self._cr.execute(
                        query_expense,
                        (date_to_dt_min, data['date_to'], tuple(location_ids), pro.id, data['company_id'])
                    )
                    expense = self._cr.dictfetchall()
                
                else:
                    f_income = []
                    f_expense = []
                    income = []
                    expense = []
                
                    
                f_bal_price = 0
                f_in_qty = 0
                f_in_price = 0
                in_qty = 0
                in_price = 0
                ex_qty = 0
                ex_price = 0
                last_qty = 0
                last_price = 0
                f_ex_qty = 0
                f_ex_price = 0
            
                for lines in f_income:
                    if lines['product_id'] == pro.id:
                        f_in_qty +=lines['qty']
                        f_in_price +=lines['price']
                
                for lined in f_expense:
                    if lined['product_id'] == pro.id:
                        f_ex_qty +=lined['qty']
                        f_ex_price +=lined['price']
                        
                                    
                for linem in income:
                    if linem['product_id'] == pro.id:
                        in_qty +=linem['qty']
                        in_price +=linem['price']
                
                for linex in expense:
                    if linex['product_id'] == pro.id:
                        ex_qty +=linex['qty']
                        ex_price +=linex['price']
                
                f_bal_qty = f_in_qty - f_ex_qty
                f_bal_price = f_in_price - f_ex_price
                last_qty = f_bal_qty + in_qty - ex_qty
                last_price = f_bal_price + in_price - ex_price
                
                sheet.write(f'A%s'%rowx, count, data_left)
                sheet.write(f'B%s'%rowx, u'%s'%pro.name, data_left)
                sheet.write(f'C%s'%rowx, u'%s'%pro.barcode, data_left)
                sheet.write(f'D%s'%rowx, u'%s'%pro.default_code, data_left)
                sheet.write(f'E%s'%rowx, u'%s'%pro.uom_id.name, data_left)
                sheet.write(f'F%s'%rowx, f_bal_qty, data_right)
                sheet.write(f'G%s'%rowx, f_bal_price, data_right)
                sheet.write(f'H%s'%rowx, in_qty, data_right)
                sheet.write(f'I%s'%rowx, in_price, data_right)
                sheet.write(f'J%s'%rowx, ex_qty, data_right)
                sheet.write(f'K%s'%rowx, ex_price, data_right)
                sheet.write(f'L%s'%rowx, last_qty, data_right)
                sheet.write(f'M%s'%rowx, last_price, data_right)
    
                count +=1
                rowx +=1
                
                total_f_bal_qty +=f_bal_qty
                total_f_bal_price +=f_bal_price
                total_in_qty +=in_qty
                total_in_price +=in_price
                total_ex_qty +=ex_qty
                total_ex_price +=ex_price
                total_last_qty +=last_qty
                total_last_price +=last_price
                
            sheet.merge_range(f'A%s:E%s'%(rowx,rowx), u'Нийт', data_center_bold)
            sheet.write(f'F%s'%rowx, total_f_bal_qty, data_right)
            sheet.write(f'G%s'%rowx, total_f_bal_price, data_right)
            sheet.write(f'H%s'%rowx, total_in_qty, data_right)
            sheet.write(f'I%s'%rowx, total_in_price, data_right)
            sheet.write(f'J%s'%rowx, total_ex_qty, data_right)
            sheet.write(f'K%s'%rowx, total_ex_price, data_right)
            sheet.write(f'L%s'%rowx, total_last_qty, data_right)
            sheet.write(f'M%s'%rowx, total_last_price, data_right)
            
            
            
            
    
        else:

            rowx = 5
            
            sheet.merge_range(
                'F3:I3',
                u'Тайлант хугацаа: %s - %s' % (data.get('date_from'), data.get('date_to')),
                head_title
            )
            
            sheet.merge_range(f'A{rowx}:A{rowx+1}', u'Д/д', data_center_bold)
            sheet.merge_range(f'B{rowx}:B{rowx+1}', u'Барааны нэр', data_center_bold)
            sheet.merge_range(f'C{rowx}:C{rowx+1}', u'Барааны код', data_center_bold)
            sheet.merge_range(f'D{rowx}:D{rowx+1}', u'Дотоод код', data_center_bold)
            sheet.merge_range(f'E{rowx}:E{rowx+1}', u'Хэмжих нэгж', data_center_bold)
            sheet.merge_range(f'F{rowx}:F{rowx+1}', u'Эхний үлдэгдэл', data_center_bold)
            sheet.merge_range(f'G{rowx}:G{rowx+1}', u'Орлого', data_center_bold)
            sheet.merge_range(f'H{rowx}:H{rowx+1}', u'Зарлага', data_center_bold)
            sheet.merge_range(f'I{rowx}:I{rowx+1}', u'Эцсийн үлдэгдэл', data_center_bold)
            
            
            
            
            count = 0
            rowx +=1
            
            total_f_bal_qty = 0
            total_f_in_qty = 0
            total_in_qty = 0
            total_ex_qty = 0
            total_last_qty = 0
            total_f_ex_qty = 0
            
            date_from = data['date_from']

            if isinstance(date_from, str):
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            
            date_to_dt_max = datetime.combine(date_from, time.max)
            date_to_dt_min = datetime.combine(date_from, time.min)
            
            
            for pro in product_ids:
                
                f_in_qty = 0
                in_qty = 0
                ex_qty = 0
                last_qty = 0
                f_ex_qty = 0
                if location_ids:
                    f_query_income = """
                        SELECT
                            mv.product_id,
                            SUM(mv.product_uom_qty) AS qty,
                            AVG(mv.price_unit) AS price
                        FROM stock_move mv
                        JOIN stock_location sl ON mv.location_id = sl.id
                        JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date <= %s
                          AND dest.id IN %s
                          AND mv.product_id = %s
                          AND mv.company_id = %s
                          AND sl.usage = 'inventory'
                          AND dest.usage = 'internal'
                        GROUP BY mv.product_id
                    """
                
                    self._cr.execute(
                        f_query_income,
                        (date_to_dt_max, tuple(location_ids), pro.id, data['company_id'])
                    )
                    f_income = self._cr.dictfetchall()
                    
                    f_query_expense = """
                        SELECT
                            mv.product_id,
                            SUM(mv.product_uom_qty) AS qty,
                            AVG(mv.price_unit) AS price
                        FROM stock_move mv
                        JOIN stock_location sl ON mv.location_id = sl.id
                        JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date <= %s
                          AND sl.id IN %s
                          AND mv.product_id = %s
                          AND mv.company_id = %s
                          AND sl.usage = 'internal'
                          AND dest.usage = 'inventory'
                        GROUP BY mv.product_id
                    """
                
                    self._cr.execute(
                        f_query_expense,
                        (date_to_dt_max, tuple(location_ids), pro.id, data['company_id'])
                    )
                    f_expense = self._cr.dictfetchall()
                    
                    
                    
                    query_income = """
                        SELECT
                            mv.product_id,
                            SUM(mv.product_uom_qty) AS qty,
                            AVG(mv.price_unit) AS price
                        FROM stock_move mv
                        JOIN stock_location sl ON mv.location_id = sl.id
                        JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date > %s
                          AND mv.date <= %s
                          AND dest.id IN %s
                          AND mv.product_id = %s
                          AND mv.company_id = %s
                          AND sl.usage IN ('supplier','customer','inventory','production','internal')
                          AND dest.usage = 'internal'
                        GROUP BY mv.product_id
                    """
                
                    self._cr.execute(
                        query_income,
                        (date_to_dt_min, data['date_to'], tuple(location_ids), pro.id, data['company_id'])
                    )
                    income = self._cr.dictfetchall()
                    
                    
                    query_expense = """
                        SELECT
                            mv.product_id,
                            SUM(mv.product_uom_qty) AS qty,
                            AVG(mv.price_unit) AS price
                        FROM stock_move mv
                        JOIN stock_location sl ON mv.location_id = sl.id
                        JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date > %s
                          AND mv.date <= %s
                          AND sl.id IN %s
                          AND mv.product_id = %s
                          AND mv.company_id = %s
                          AND sl.usage = 'internal'
                          AND dest.usage IN ('customer','supplier','inventory','production','internal')
                        GROUP BY mv.product_id
                    """
                
                    self._cr.execute(
                        query_expense,
                        (date_to_dt_min, data['date_to'], tuple(location_ids), pro.id, data['company_id'])
                    )
                    expense = self._cr.dictfetchall()
                    
                else:
                    f_income = []
                    f_expense = []
                    income = []
                    expense = []
    

                    
                    
                
                for lines in f_income:
                    if lines['product_id'] == pro.id:
                        f_in_qty +=lines['qty']
                
                for lined in f_expense:
                    if lined['product_id'] == pro.id:
                        f_ex_qty +=lined['qty']
                        
                                    
                for linem in income:
                    if linem['product_id'] == pro.id:
                        in_qty +=linem['qty']
                
                for linex in expense:
                    if linex['product_id'] == pro.id:
                        ex_qty +=linex['qty']
                
                f_bal_qty = f_in_qty - f_ex_qty
                last_qty = f_bal_qty + in_qty - ex_qty
                sheet.write(f'A%s'%rowx, count, data_left)
                sheet.write(f'B%s'%rowx, u'%s'%pro.name, data_left)
                sheet.write(f'C%s'%rowx, u'%s'%pro.barcode, data_left)
                sheet.write(f'D%s'%rowx, u'%s'%pro.default_code, data_left)
                sheet.write(f'E%s'%rowx, u'%s'%pro.uom_id.name, data_left)
                sheet.write(f'F%s'%rowx, f_bal_qty, data_right)
                sheet.write(f'G%s'%rowx, in_qty, data_right)
                sheet.write(f'H%s'%rowx, ex_qty, data_right)
                sheet.write(f'I%s'%rowx, last_qty, data_right)

                count +=1
                rowx +=1
                total_f_bal_qty +=f_bal_qty
                total_in_qty +=in_qty
                total_ex_qty +=ex_qty
                total_last_qty +=last_qty
                
            sheet.merge_range(f'A%s:E%s'%(rowx,rowx), u'Нийт', data_center_bold)
            sheet.write(f'F%s'%rowx, total_f_bal_qty, data_right)
            sheet.write(f'G%s'%rowx, total_in_qty, data_right)
            sheet.write(f'H%s'%rowx, total_ex_qty, data_right)
            sheet.write(f'I%s'%rowx, total_last_qty, data_right)
            


        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()



