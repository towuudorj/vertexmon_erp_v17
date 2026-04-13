# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta, datetime, time
import xlwt, json
from odoo.tools import date_utils
import io
import json
import xlsxwriter

class product_detail_report(models.TransientModel):
    """
        Барааны материалын дэлгэрэнгүй тайлан
    """
    _name = "product.detail.report"
    _inherit = 'xls.report.base'
    _description = "Stock expense Report - Mongolia"

    
    company_id = fields.Many2one('res.company', string=u'Компани', readonly=True,
                                default=lambda self: self.env.user.company_id)
    is_transection = fields.Boolean(string=u'Гүйлгээтэй эсэх')
    start_date = fields.Date(string=u'Эхлэх огноо', required=True,
                                    default=fields.Date.context_today)
    end_date = fields.Date(string=u'Дуусах огноо', required=True,
                                    default=fields.Date.context_today)
    categ_id = fields.Many2one('product.category', string=u'Барааны ангилал')
    product_id = fields.Many2one('product.product', string=u'Бараа')
    warehouse_ids = fields.Many2many('stock.warehouse','stock_warehouse_product_rel','report_id','warehouse_ids', string=u'Агуулах', required=True)
    type = fields.Selection([('quantity',u'Тоогоор'),
                             ('cost',u'Өртгөөр')], string=u'Төрөл', required=True)
    
    def get_report_data(self):
        data = super(product_detail_report, self).get_report_data()
        data.update({
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'warehouse_ids': self.warehouse_ids.ids,
            'categ_id':self.categ_id.id,
            'product_id': self.product_id.id,
            'is_transection':self.is_transection,
            'type':self.type
        })
        return data

    def action_print_xls_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'product.detail.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'account_move'}
        }
        
    def get_location_qty(self, type, product_id, start_date, end_date, company):
        
        return 

    def get_xlsx_report(self, data, response, get_file=False):
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
        data_right_bold = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00',
                                    'bold': True
                                    })
        data_left = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00'
                                    })
        data_left_bold = workbook.add_format({
                                    'align': 'left',
                                    'border': 1,
                                    'font_size': 12,
                                    'num_format': '#,##0.00',
                                    'bold': True
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
                                    'num_format': '#,##0.00',
                                    'bold': True
                                    })

        product_obj = self.env['product.product']
        category_obj = self.env['product.category']
        category_id = False
        product_id = False
        if data['categ_id']:
            category_id = data['categ_id']
        if data['product_id']:
            product_id = data['product_id']

        
        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' % (data['company_name']), head)
        
        sheet.merge_range('A2:T2', u'Барааны материалын дэлгэрэнгүй тайлан', head_title)
        
        sheet.merge_range('R3:T3', u'Тайлант хугацаа: %s - %s'%(data['start_date'],data['end_date']), head)

        rowx = 4
        sheet.set_paper(9)
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0.5)
        sheet.set_column(1, 1, 50)
        sheet.set_column(2, 20, 15)
        
        if data['type'] == 'cost':

            sheet.merge_range('A%s:A%s'%(rowx, rowx+1), u'Д/д', data_right_bold)
            sheet.merge_range('B%s:B%s'%(rowx, rowx+1), u'Барааны нэр', data_right_bold)
            sheet.merge_range('C%s:C%s'%(rowx, rowx+1), u'Барааны код', data_right_bold)
            sheet.merge_range('D%s:D%s'%(rowx, rowx+1), u'Дотоод код', data_right_bold)
            sheet.merge_range('E%s:F%s'%(rowx, rowx), u'Барааны эхний үлдэгдэл', data_center_bold)
            sheet.write('E%s'%(rowx+1), u'Барааны хэмжих нэгж', data_left_bold)
            sheet.write('F%s'%(rowx+1), u'Тоо', data_left_bold)
            
    
            sheet.merge_range('G%s:L%s'%(rowx, rowx), u'Барааны орлого', data_center_bold)
            sheet.write('G%s'%(rowx+1), u'Худалдан авалт', data_left_bold)
            sheet.write('H%s'%(rowx+1), u'Захиалагчаас', data_left_bold)
            sheet.write('I%s'%(rowx+1), u'Дотоод', data_left_bold)
            sheet.write('J%s'%(rowx+1), u'Тооллогоос', data_left_bold)
            sheet.write('K%s'%(rowx+1), u'Нийт', data_left_bold)
    
    
            sheet.merge_range('L%s:P%s'%(rowx, rowx), u'Барааны зарлага', data_center_bold)
            sheet.write('L%s'%(rowx+1), u'Захиалагчийн', data_left_bold)
            sheet.write('M%s'%(rowx+1), u'Худалдан авалт', data_left_bold)
            sheet.write('N%s'%(rowx+1), u'Дотоод', data_left_bold)
            sheet.write('O%s'%(rowx+1), u'Тооллогоос', data_left_bold)
            sheet.write('P%s'%(rowx+1), u'Нийт', data_left_bold)
            sheet.merge_range('Q%s:S%s'%(rowx, rowx), u'Барааны эцсийн үлдэгдэл', data_center_bold)
            sheet.write('Q%s'%(rowx+1), u'Тоо', data_left_bold)
            sheet.write('R%s'%(rowx+1), u'Нэгж өртөг', data_left_bold)
            sheet.write('S%s'%(rowx+1), u'Нийт өртөг', data_left_bold)
        

            rowx += 2
            datas = False
            purchase_income = []
            customer_income = []
            sale_expense = []
            customer_expense = []
            internal_income = []
            internal_expense = []
            expense = []
            f_income = []
            f_expense = []
            sale_expo = []
            wh_obj = self.env['stock.warehouse']
            loc_obj = self.env['stock.location']
            loc_ids = []
            if len(data['warehouse_ids']) == 1:
                wh_id = wh_obj.browse(data['warehouse_ids'][0])
            else:
                for wh in data['warehouse_ids']:
                    wh_id = wh_obj.browse(wh)
                    for li in wh_id:
                        loc_ids.append(li.lot_stock_id.id)
            
            loc_id = wh_id.lot_stock_id
            if len(str(loc_id))==1:
                loc_ids.append(loc_id)
            else:
                if loc_id:
                    loc_ids.append(loc_id.id)
                    if loc_id.child_ids:
                        for lin in loc_id.child_ids:
                            loc_ids.append(lin.id)
                            if lin.child_ids:
                                for lins in lin.child_ids:
                                    loc_ids.append(lins.id)
            date_from = data['start_date']

            if isinstance(date_from, str):
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()

            date_from_dt_max = datetime.combine(date_from, time.min)
            date_from_dt_min = datetime.combine(date_from, time.min)
            
            date_to = data['end_date']

            if isinstance(date_to, str):
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

            date_to_dt_max = datetime.combine(date_to, time.max)
            date_to_dt_min = datetime.combine(date_to, time.min)
            if product_id !=False and loc_ids !=False:          
                #Эхний үлдэгдэл
                # Барааны орлого
                f_query_income = """
                                 SELECT mv.product_id, 
                                       SUM(mv.quantity) AS qty
                                 FROM stock_move_line mv
                                      JOIN stock_location sl ON mv.location_id = sl.id
                                      JOIN stock_location dest ON mv.location_dest_id = dest.id
                                 WHERE mv.state = 'done'
                                   AND mv.date < %s
                                   AND dest.id IN %s
                                   AND mv.product_id = %s
                                   AND mv.company_id = %s
                                   AND sl.usage IN ('supplier', 'customer', 'inventory', 'production', 'internal')
                                   AND dest.usage = 'internal'
                                 GROUP BY mv.product_id \
                                 """
                self._cr.execute(f_query_income,(date_from_dt_min, tuple(loc_ids), product_id, data['company_id']))
                f_income = self._cr.dictfetchall()
                    

                # Барааны зарлага
                f_query_expense = """
                                  SELECT mv.product_id, 
                                        SUM(mv.quantity) AS qty
                                  FROM stock_move_line mv
                                       JOIN stock_location sl ON mv.location_id = sl.id
                                       JOIN stock_location dest ON mv.location_dest_id = dest.id
                                  WHERE mv.state = 'done'
                                    AND mv.date < %s
                                    AND sl.id IN %s
                                    AND mv.product_id = %s
                                    AND mv.company_id = %s
                                    AND sl.usage = 'internal'
                                    AND dest.usage IN ('customer', 'supplier', 'inventory', 'production', 'internal')
                                  GROUP BY mv.product_id 
                                  """
                self._cr.execute(f_query_expense,(date_from_dt_min, tuple(loc_ids), product_id, data['company_id']))
                f_expense = self._cr.dictfetchall()
                
                
                
                #Худалдан авалтын барааны орлого                
                pur_income_query = f"""
                    SELECT
                        mv.product_id,
                        SUM(mv.product_uom_qty) AS qty,
                        sum(svl.price) AS price
                    FROM 
                    (   
                        SELECT sum(svl.value) AS price, mv.id as stock_move_id
                        FROM stock_valuation_layer svl 
                        LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                        WHERE mv.product_id = {product_id}
                        GROUP BY mv.id
                    ) AS svl 
                    LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                    LEFT JOIN stock_location sl ON mv.location_id = sl.id
                    LEFT JOIN stock_location dest ON mv.location_dest_id = dest.id
                    WHERE mv.state = 'done'
                      AND mv.date >= %s
                      AND mv.date <= %s
                      AND dest.id IN %s
                      AND mv.product_id = %s
                      AND mv.company_id = %s
                      AND sl.usage IN ('supplier')
                      AND dest.usage = 'internal'
                    GROUP BY mv.product_id
                """
                self._cr.execute(pur_income_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), product_id, data['company_id']))
                purchase_income = self._cr.dictfetchall()
                
                
                #Захиалагчаас орсон орлого
                cus_income_query = f"""
                    SELECT
                        mv.product_id,
                        SUM(mv.product_uom_qty) AS qty,
                        sum(svl.price) AS price
                    FROM 
                    (   
                        SELECT sum(svl.value) AS price, mv.id as stock_move_id
                        FROM stock_valuation_layer svl 
                        LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                        WHERE mv.product_id = {product_id}
                        GROUP BY mv.id
                    ) AS svl 
                    LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                    LEFT JOIN stock_location sl ON mv.location_id = sl.id
                    LEFT JOIN stock_location dest ON mv.location_dest_id = dest.id
                    WHERE mv.state = 'done'
                      AND mv.date >= %s
                      AND mv.date <= %s
                      AND dest.id IN %s
                      AND mv.product_id = %s
                      AND mv.company_id = %s
                      AND sl.usage IN ('customer')
                      AND dest.usage = 'internal'
                    GROUP BY mv.product_id
                """
                self._cr.execute( cus_income_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), product_id, data['company_id']))
                customer_income = self._cr.dictfetchall()
                

                
                
                 #Дотоод хөдөлгөөнөөс орсон орлого
                int_income_query = """
                               SELECT mv.product_id, 
                                    SUM(mv.quantity) AS qty
                               FROM stock_move_line mv
                                    JOIN stock_location sl ON mv.location_id = sl.id
                                    JOIN stock_location dest ON mv.location_dest_id = dest.id
                               WHERE mv.state = 'done'
                                 AND mv.date >= %s
                                 AND mv.date <= %s
                                 AND dest.id IN %s
                                 AND mv.product_id = %s
                                 AND mv.company_id = %s
                                 AND sl.usage IN ('internal')
                                 AND dest.usage = 'internal'
                               GROUP BY mv.product_id 
                               """
                self._cr.execute(int_income_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), product_id, data['company_id']))
                internal_income = self._cr.dictfetchall()
                 
            
                #Тооллогоос орсон орлого
                qty_income_query = f"""
                    SELECT
                        mv.product_id,
                        SUM(mv.product_uom_qty) AS qty,
                        sum(svl.price) AS price
                    FROM 
                    (   
                        SELECT sum(svl.value) AS price, mv.id as stock_move_id
                        FROM stock_valuation_layer svl 
                        LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                        WHERE mv.product_id = {product_id}
                        GROUP BY mv.id
                    ) AS svl 
                    LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                    LEFT JOIN stock_location sl ON mv.location_id = sl.id
                    LEFT JOIN stock_location dest ON mv.location_dest_id = dest.id
                    WHERE mv.state = 'done'
                      AND mv.date >= %s
                      AND mv.date <= %s
                      AND dest.id IN %s
                      AND mv.product_id = %s
                      AND mv.company_id = %s
                      AND sl.usage IN ('inventory')
                      AND dest.usage = 'internal'
                    GROUP BY mv.product_id
                """
                self._cr.execute(qty_income_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), product_id, data['company_id']))
                qty_income = self._cr.dictfetchall()
                

                

                
                #Борлуулсан барааны зарлага
                sale_query = f"""
                    SELECT
                        mv.product_id,
                        SUM(mv.product_uom_qty) AS qty,
                        sum(svl.price) AS price
                    FROM 
                    (   
                        SELECT sum(svl.value) AS price, mv.id as stock_move_id
                        FROM stock_valuation_layer svl 
                        LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                        WHERE mv.product_id = {product_id}
                        GROUP BY mv.id
                    ) AS svl 
                    LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                    LEFT JOIN stock_location sl ON mv.location_id = sl.id
                    LEFT JOIN stock_location dest ON mv.location_dest_id = dest.id
                    WHERE mv.state = 'done'
                      AND mv.date >= %s
                      AND mv.date <= %s
                      AND sl.id IN %s
                      AND mv.product_id = %s
                      AND mv.company_id = %s
                      AND sl.usage = 'internal'
                      AND dest.usage IN ('customer')
                    GROUP BY mv.product_id
                """

                self._cr.execute(sale_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), product_id, data['company_id']))
                sale_expense = self._cr.dictfetchall()

                
                #Хуадалдан авалтын барааны буцаалт
                pur_ret_query = f"""
                    SELECT
                        mv.product_id,
                        SUM(mv.product_uom_qty) AS qty,
                        sum(svl.price) AS price
                    FROM 
                        (SELECT sum(svl.value) AS price, mv.id as stock_move_id
                        FROM stock_valuation_layer svl 
                        LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                        WHERE mv.product_id = {product_id}
                        GROUP BY mv.id
                    ) AS svl 
                    LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                    LEFT JOIN stock_location sl ON mv.location_id = sl.id
                    LEFT JOIN stock_location dest ON mv.location_dest_id = dest.id
                    WHERE mv.state = 'done'
                      AND mv.date >= %s
                      AND mv.date <= %s
                      AND sl.id IN %s
                      AND mv.product_id = %s
                      AND mv.company_id = %s
                      AND sl.usage = 'internal'
                      AND dest.usage IN ('supplier')
                    GROUP BY mv.product_id
                """
                self._cr.execute( pur_ret_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), product_id, data['company_id']))
                pur_ret = self._cr.dictfetchall()
                

                
                #Дотоод барааны зарлага
                int_query = """
                            SELECT mv.product_id, 
                                    SUM(mv.quantity) AS qty
                            FROM stock_move_line mv
                                 JOIN stock_location sl ON mv.location_id = sl.id
                                 JOIN stock_location dest ON mv.location_dest_id = dest.id
                            WHERE mv.state = 'done'
                              AND mv.date >= %s
                              AND mv.date <= %s
                              AND sl.id IN %s
                              AND mv.product_id = %s
                              AND mv.company_id = %s
                              AND sl.usage = 'internal'
                              AND dest.usage IN ('internal')
                            GROUP BY mv.product_id 
                                """
                self._cr.execute(int_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), product_id, data['company_id']))
                internal_expense = self._cr.dictfetchall()

                
                #Тооллогын зарлага
                qty_exp_query = f"""
                    SELECT
                        mv.product_id,
                        SUM(mv.product_uom_qty) AS qty,
                        sum(svl.price) AS price
                    FROM 
                        (SELECT sum(svl.value) AS price, mv.id as stock_move_id
                        FROM stock_valuation_layer svl 
                        LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                        WHERE mv.product_id = {product_id}
                        GROUP BY mv.id
                    ) AS svl 
                    LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                    LEFT JOIN stock_location sl ON mv.location_id = sl.id
                    LEFT JOIN stock_location dest ON mv.location_dest_id = dest.id
                    WHERE mv.state = 'done'
                      AND mv.date >= %s
                      AND mv.date <= %s
                      AND sl.id IN %s
                      AND mv.product_id = %s
                      AND mv.company_id = %s
                      AND sl.usage = 'internal'
                      AND dest.usage IN ('inventory')
                    GROUP BY mv.product_id
                """
                self._cr.execute(
                    qty_exp_query,
                    (date_from_dt_min, date_to_dt_max, tuple(loc_ids), product_id, data['company_id']))
                qty_expense = self._cr.dictfetchall()

                
                
              
                
            elif product_id == False and loc_ids !=False:
                    #Эхний үлдэгдэл
                    # Барааны орлого
                    f_query_income = """
                                     SELECT mv.product_id, 
                                           SUM(mv.quantity) AS qty
                                     FROM stock_move_line mv
                                          JOIN stock_location sl ON mv.location_id = sl.id
                                          JOIN stock_location dest ON mv.location_dest_id = dest.id
                                     WHERE mv.state = 'done'
                                       AND mv.date < %s
                                       AND dest.id IN %s
                                       AND mv.company_id = %s
                                       AND sl.usage IN ('supplier', 'customer', 'inventory', 'production', 'internal')
                                       AND dest.usage = 'internal'
                                     GROUP BY mv.product_id \
                                     """
                    self._cr.execute(f_query_income,(date_from_dt_min, tuple(loc_ids), data['company_id']))
                    f_income = self._cr.dictfetchall()

                    
                    # Барааны зарлага
                    f_query_expense = """
                                      SELECT mv.product_id, 
                                            SUM(mv.quantity) AS qty
                                      FROM stock_move_line mv
                                           JOIN stock_location sl ON mv.location_id = sl.id
                                           JOIN stock_location dest ON mv.location_dest_id = dest.id
                                      WHERE mv.state = 'done'
                                        AND mv.date < %s
                                        AND sl.id IN %s
                                        AND mv.company_id = %s
                                        AND sl.usage = 'internal'
                                        AND dest.usage IN ('customer', 'supplier', 'inventory', 'production', 'internal')
                                      GROUP BY mv.product_id 
                                      """
                    self._cr.execute(f_query_expense,(date_from_dt_min, tuple(loc_ids), data['company_id']))
                    f_expense = self._cr.dictfetchall()

                    
                    #Худалдан авалтын барааны орлого
                    pur_income_query = f"""
                        SELECT
                            mv.product_id,
                            SUM(mv.product_uom_qty) AS qty,
                            sum(svl.price) AS price
                        FROM 
                        (   
                            SELECT sum(svl.value) AS price, mv.id as stock_move_id
                            FROM stock_valuation_layer svl 
                            LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                            GROUP BY mv.id
                        ) AS svl 
                        LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                        LEFT JOIN stock_location sl ON mv.location_id = sl.id
                        LEFT JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date >= %s
                          AND mv.date <= %s
                          AND dest.id IN %s
                          AND mv.company_id = %s
                          AND sl.usage IN ('supplier')
                          AND dest.usage = 'internal'
                        GROUP BY mv.product_id
                    """
                    self._cr.execute(pur_income_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), data['company_id']))
                    purchase_income = self._cr.dictfetchall()
                    
                    
                    
                    #Захиалагчаас орсон орлого
                    cus_income_query = f"""
                        SELECT
                            mv.product_id,
                            SUM(mv.product_uom_qty) AS qty,
                            sum(svl.price) AS price
                        FROM 
                        (   
                            SELECT sum(svl.value) AS price, mv.id as stock_move_id
                            FROM stock_valuation_layer svl 
                            LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                            GROUP BY mv.id
                        ) AS svl 
                        LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                        LEFT JOIN stock_location sl ON mv.location_id = sl.id
                        LEFT JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date >= %s
                          AND mv.date <= %s
                          AND dest.id IN %s
                          AND mv.company_id = %s
                          AND sl.usage IN ('customer')
                          AND dest.usage = 'internal'
                        GROUP BY mv.product_id
                    """
                    self._cr.execute( cus_income_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), data['company_id']))
                    customer_income = self._cr.dictfetchall()

                    
                    
                    #Дотоод орсон орлого
                    int_income_query = """
                                   SELECT mv.product_id, 
                                        SUM(mv.quantity) AS qty
                                   FROM stock_move_line mv
                                        JOIN stock_location sl ON mv.location_id = sl.id
                                        JOIN stock_location dest ON mv.location_dest_id = dest.id
                                   WHERE mv.state = 'done'
                                     AND mv.date >= %s
                                     AND mv.date <= %s
                                     AND dest.id IN %s
                                     AND mv.company_id = %s
                                     AND sl.usage IN ('internal')
                                     AND dest.usage = 'internal'
                                   GROUP BY mv.product_id 
                                   """
                    self._cr.execute(int_income_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), data['company_id']))
                    internal_income = self._cr.dictfetchall()
                     
                    
                     #Тооллогоос орсон орлого
                    qty_income_query = f"""
                        SELECT
                            mv.product_id,
                            SUM(mv.product_uom_qty) AS qty,
                            sum(svl.price) AS price
                        FROM 
                        (   
                            SELECT sum(svl.value) AS price, mv.id as stock_move_id
                            FROM stock_valuation_layer svl 
                            LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                            GROUP BY mv.id
                        ) AS svl 
                        LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                        LEFT JOIN stock_location sl ON mv.location_id = sl.id
                        LEFT JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date >= %s
                          AND mv.date <= %s
                          AND dest.id IN %s
                          AND mv.company_id = %s
                          AND sl.usage IN ('inventory')
                          AND dest.usage = 'internal'
                        GROUP BY mv.product_id
                    """
                    self._cr.execute(qty_income_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), data['company_id']))
                    qty_income = self._cr.dictfetchall()

                    
                    
                    
                    
                    
                    #Борлуулсан барааны зарлага
                    sale_query = f"""
                        SELECT
                            mv.product_id,
                            SUM(mv.product_uom_qty) AS qty,
                            sum(svl.price) AS price
                        FROM 
                        (   
                            SELECT sum(svl.value) AS price, mv.id as stock_move_id
                            FROM stock_valuation_layer svl 
                            LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                            GROUP BY mv.id
                        ) AS svl 
                        LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                        LEFT JOIN stock_location sl ON mv.location_id = sl.id
                        LEFT JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date >= %s
                          AND mv.date <= %s
                          AND sl.id IN %s
                          AND mv.company_id = %s
                          AND sl.usage = 'internal'
                          AND dest.usage IN ('customer')
                        GROUP BY mv.product_id
                    """
                    self._cr.execute(sale_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), data['company_id']))
                    sale_expense = self._cr.dictfetchall()

                    
                    #Худалдан авалтын барааны буцаалт
                    pur_ret_query = f"""
                        SELECT
                            mv.product_id,
                            SUM(mv.product_uom_qty) AS qty,
                            sum(svl.price) AS price
                        FROM 
                            (SELECT sum(svl.value) AS price, mv.id as stock_move_id
                            FROM stock_valuation_layer svl 
                            LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                            GROUP BY mv.id
                        ) AS svl 
                        LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                        LEFT JOIN stock_location sl ON mv.location_id = sl.id
                        LEFT JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date >= %s
                          AND mv.date <= %s
                          AND sl.id IN %s
                          AND mv.company_id = %s
                          AND sl.usage = 'internal'
                          AND dest.usage IN ('supplier')
                        GROUP BY mv.product_id
                    """
                    self._cr.execute( pur_ret_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), data['company_id']))
                    pur_ret = self._cr.dictfetchall()
                    
  
                    
                    #Дотоод барааны зарлага
                    int_query = """
                                SELECT mv.product_id, 
                                        SUM(mv.quantity) AS qty
                                FROM stock_move_line mv
                                     JOIN stock_location sl ON mv.location_id = sl.id
                                     JOIN stock_location dest ON mv.location_dest_id = dest.id
                                WHERE mv.state = 'done'
                                  AND mv.date >= %s
                                  AND mv.date <= %s
                                  AND sl.id IN %s
                                  AND mv.company_id = %s
                                  AND sl.usage = 'internal'
                                  AND dest.usage IN ('internal')
                                GROUP BY mv.product_id 
                                    """
                    self._cr.execute(int_query,(date_from_dt_min, date_to_dt_max, tuple(loc_ids), data['company_id']))
                    internal_expense = self._cr.dictfetchall()
                    
                    
                    #Тооллого барааны зарлага
                    qty_exp_query = f"""
                        SELECT
                            mv.product_id,
                            SUM(mv.product_uom_qty) AS qty,
                            sum(svl.price) AS price
                        FROM 
                            (SELECT sum(svl.value) AS price, mv.id as stock_move_id
                            FROM stock_valuation_layer svl 
                            LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                            GROUP BY mv.id
                        ) AS svl 
                        LEFT JOIN stock_move mv ON mv.id = svl.stock_move_id
                        LEFT JOIN stock_location sl ON mv.location_id = sl.id
                        LEFT JOIN stock_location dest ON mv.location_dest_id = dest.id
                        WHERE mv.state = 'done'
                          AND mv.date >= %s
                          AND mv.date <= %s
                          AND sl.id IN %s
                          AND mv.company_id = %s
                          AND sl.usage = 'internal'
                          AND dest.usage IN ('inventory')
                        GROUP BY mv.product_id
                    """
                    self._cr.execute(
                        qty_exp_query,
                        (date_from_dt_min, date_to_dt_max, tuple(loc_ids), data['company_id']))
                    qty_expense = self._cr.dictfetchall()

                    
                
                    
          
                
                
            product = []
            products = False
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
                                            product_ids = product_obj.search([('categ_id','=',catss.id),('detailed_type','=','product')],order='name asc')
                                            for pr in product_ids:
                                                product.append(pr.id)
                    else:
                        product_ids = product_obj.search([('categ_id','=',category_id),('detailed_type','=','product')],order='name asc')
                        for pr in product_ids:
                            product.append(pr.id)
                else:
                    if data['is_transection'] == True:
                        if len(loc_ids)==1:
                            self._cr.execute("""select mv.product_id from stock_move as mv 
                                left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                left join stock_location as src_id on mv.location_id = src_id.id 
                                where src_id.id = %s  or dest_id.id = %s group by mv.product_id"""%(loc_ids[0],loc_ids[0]))
                            products = self._cr.dictfetchall()
                        else:
                            self._cr.execute("""select mv.product_id from stock_move as mv 
                                left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                left join stock_location as src_id on mv.location_id = src_id.id 
                                where src_id.id in %s  or dest_id.id in %s group by mv.product_id"""%(tuple(loc_ids),tuple(loc_ids)))
                            products = self._cr.dictfetchall()
                    else:
                        product_ids = product_obj.search([('detailed_type','=','product')],order='name asc')
                        for pr in product_ids:
                            product.append(pr.id)
                        
            num = 0
            f_standard_price = 0.0
            f_list_price = 0.0
            total_income_pur_qty = 0.0
            total_income_oth_qty = 0.0
            total_expense_sale_qty= 0.0
            total_qty_income_qty = 0.0
            total_end_oth_qty = 0.0
            total_expense_qty = 0.0
            total_qty_exp_qty = 0.0
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
            if data['is_transection'] == True:
                if products:
                    for line in products:
                        product.append(line['product_id'])
            rowx = 6
            for line in product_obj.browse(product):
                num +=1
                f_income_qty = 0.0
                f_income_price = 0.0
                f_expense_qty = 0.0
                f_expense_price = 0.0
                pur_income_qty = 0.0
                pur_income_price = 0.0
                custom_income_qty = 0.0
                custom_income_price = 0.0
                int_income_qty = 0.0
                int_income_price = 0.0
                qty_income_qty = 0.0
                qty_income_price = 0.0
                income_qty = 0.0
                expense_qty = 0.0
                expense_int_qty = 0.0
                expense_int_price = 0.0
                income_price = 0.0
                sale_expense_qty = 0.0
                sale_expense_price = 0.0
                qty_expense_qty = 0.0
                qty_expense_price = 0.0
                cust_expense_qty = 0.0
                oth_expense_qty = 0.0
                expense_price = 0.0
                end_qty =0.0
                expo_qty = 0.0
                expo_price = 0.0
                seri = ''
                stock_valuation_layer_obj = self.env['stock.valuation.layer']
                if f_income!=[]:
                    for f_inc in f_income:
                        if line.id==f_inc['product_id']:
                            if f_inc['qty'] !=None:
                                f_income_qty += f_inc['qty']
                            valuation_ids = stock_valuation_layer_obj.search([('product_id','=',line.id),('create_date','<',date_from_dt_min),('quantity','>',0.0)])
                            if valuation_ids:
                                for vl in valuation_ids:
                                    f_income_price += vl.value
                            else:
                                f_income_price = line.standard_price
                                
                if f_expense !=[]:
                    for f_exp in f_expense:
                        if line.id==f_exp['product_id']:
                            if f_exp['qty'] !=None:
                                f_expense_qty +=f_exp['qty']
                            valuation_ids = stock_valuation_layer_obj.search([('product_id','=',line.id),('create_date','<',date_from_dt_min),('quantity','<',0.0)])
                            if valuation_ids:
                                for vl in valuation_ids:
                                    if vl.value < 0.0:
                                        f_expense_price += vl.value*(-1)
                                    else:
                                        f_expense_price += vl.value
                            else:
                                f_expense_price = line.standard_price

    
                if purchase_income!=[]:
                    for pur_income in purchase_income:
                        if line.id==pur_income['product_id']:
                            if pur_income['qty'] !=None:
                                pur_income_qty += pur_income['qty']
                            if pur_income['price'] !=None:
                                pur_income_price +=pur_income['price']

                                
                if customer_income!=[]:
                    for cust_income in customer_income:
                        if line.id==cust_income['product_id']:
                            if cust_income['qty'] !=None:
                                custom_income_qty += cust_income['qty']
                            if cust_income['price'] !=None:
                                custom_income_price += cust_income['price']
                                
                if internal_income!=[]:
                    for int_income in internal_income:
                        if line.id==int_income['product_id']:
                            if int_income['qty'] !=None:
                                int_income_qty += int_income['qty']
                            valuation_ids = stock_valuation_layer_obj.search([('product_id','=',line.id),('create_date','<',date_from_dt_min),('quantity','<',0.0)])
                            if valuation_ids:
                                for vl in valuation_ids:
                                    if vl.value < 0.0:
                                        int_income_price += vl.value*(-1)
                                    else:
                                        int_income_price += vl.value
                            else:
                                int_income_price = line.standard_price

               
                if qty_income!=[]:
                    for qt_income in qty_income:
                        if line.id == qt_income['product_id']:
                            if qt_income['qty'] !=None:
                                qty_income_qty += qt_income['qty']
                            if qt_income['price'] !=None:
                                qty_income_price += qt_income['price']
                                
                                
    
    
                                
                if sale_expense !=[]:
                    for sale_expen in sale_expense:
                        if line.id==sale_expen['product_id']:
                            if sale_expen['qty'] !=None:
                                sale_expense_qty +=sale_expen['qty']
                            if sale_expen['price'] !=None:
                                sale_expense_price +=sale_expen['price']
                if pur_ret !=[]:
                    for sale_exp in pur_ret:
                        if line.id==sale_exp['product_id']:
                            if sale_exp['qty'] !=None:
                                expo_qty +=sale_exp['qty']
                            if sale_exp['price'] !=None:
                                expo_price +=sale_exp['price']
                                
                if internal_expense !=[]:
                    for inter_exp in internal_expense:
                        if line.id==inter_exp['product_id']:
                            if inter_exp['qty'] !=None:
                                expense_int_qty +=inter_exp['qty']
                            valuation_ids = stock_valuation_layer_obj.search([('product_id','=',line.id),('create_date','<',date_from_dt_min),('quantity','<',0.0)])
                            if valuation_ids:
                                for vl in valuation_ids:
                                    if vl.value < 0.0:
                                        expense_int_price += vl.value*(-1)
                                    else:
                                        expense_int_price += vl.value
                            else:
                                expense_int_price = line.standard_price

                if qty_expense !=[]:
                    for qty_exp in qty_expense:
                        if line.id==qty_exp['product_id']:
                            if qty_exp['qty'] !=None:
                                qty_expense_qty +=qty_exp['qty']
                            if qty_exp['price'] !=None:
                                qty_expense_price +=qty_exp['price']
                                
                            
                first_qty = f_income_qty - f_expense_qty
                end_qty = first_qty + (pur_income_qty + custom_income_qty + int_income_qty  + qty_income_qty) - (sale_expense_qty + expo_qty+expense_int_qty + qty_expense_qty)
                
                total_price_unit = line.standard_price
                uom_name = ''
                if line.uom_id:
                    uom_name = line.uom_id.name
                sheet.write('A%s'%rowx, num, data_center)
                sheet.write('B%s'%rowx, u'%s'%line.name, data_left)
                sheet.write('C%s'%rowx, line.barcode or '', data_center)
                sheet.write('D%s'%rowx, line.default_code or '', data_center)
                sheet.write('E%s'%rowx, u'%s'%(uom_name), data_center)
                sheet.write('F%s'%rowx, first_qty, data_right)
                sheet.write('G%s'%rowx, pur_income_qty, data_right)
                sheet.write('H%s'%rowx, custom_income_qty, data_right)
                sheet.write('I%s'%rowx, int_income_qty, data_right)
                sheet.write('J%s'%rowx, qty_income_qty, data_right)
                sheet.write('K%s'%rowx, (pur_income_qty+custom_income_qty+int_income_qty+qty_income_qty), data_right)
                sheet.write('L%s'%rowx, sale_expense_qty, data_right)
                sheet.write('M%s'%rowx, expo_qty, data_right)
                sheet.write('N%s'%rowx, expense_int_qty, data_right)
                sheet.write('O%s'%rowx, qty_expense_qty, data_right)
                sheet.write('P%s'%rowx, sale_expense_qty+expo_qty+expense_int_qty+qty_expense_qty, data_right)
                sheet.write('Q%s'%rowx, first_qty + ( pur_income_qty + custom_income_qty + int_income_qty + qty_income_qty) - (sale_expense_qty+expo_qty+expense_int_qty+qty_expense_qty), data_right)
                
                if total_price_unit == 0.0:
                    sheet.write('R%s'%rowx, 0.0, data_right)
                    sheet.write('S%s'%rowx, 0.0, data_right)
                else:
                    if end_qty == 0.0:
                        sheet.write('R%s'%rowx, 0.0, data_right)
                        sheet.write('S%s'%rowx, 0.0, data_right)
                    else:
                        sheet.write('R%s'%rowx, total_price_unit, data_right)
                        sheet.write('S%s'%rowx, total_price_unit * end_qty, data_right)
                
                
                if end_qty == 0.0:
                    total_sum_price +=total_price_unit
                else:
                    total_sum_price +=total_price_unit*end_qty
                total_all_price +=total_price_unit
                
                f_total_qty +=first_qty
                total_income_pur_qty +=pur_income_qty
                total_income_cus_qty +=custom_income_qty
                total_income_qty +=(pur_income_qty+custom_income_qty+int_income_qty+qty_income_qty)
                total_expense_cust_qty +=cust_expense_qty
                total_expense_sale_qty +=sale_expense_qty
                total_end_qty +=end_qty
                total_qty +=(sale_expense_qty+expo_qty+expense_int_qty+qty_expense_qty)
                total_end_oth_qty +=oth_expense_qty
                total_qty_income_qty +=qty_income_qty
                total_qty_exp_qty +=qty_expense_qty
                total_income_int_qty +=int_income_qty
                total_expo_qty +=expo_qty
                total_exp_int_qty +=expense_int_qty
                rowx +=1
        else:
            sheet.merge_range('A%s:A%s'%(rowx, rowx+1), u'Д/д', data_right_bold)
            sheet.merge_range('B%s:B%s'%(rowx, rowx+1), u'Барааны нэр', data_right_bold)
            sheet.merge_range('C%s:C%s'%(rowx, rowx+1), u'Барааны код', data_right_bold)
            sheet.merge_range('D%s:D%s'%(rowx, rowx+1), u'Дотоод код', data_right_bold)
            sheet.merge_range('E%s:F%s'%(rowx, rowx), u'Барааны эхний үлдэгдэл', data_center_bold)
            sheet.write('E%s'%(rowx+1), u'Барааны хэмжих нэгж', data_left_bold)
            sheet.write('F%s'%(rowx+1), u'Тоо', data_left_bold)
            sheet.write('G%s'%(rowx), u'Барааны орлого', data_center_bold)
            sheet.write('H%s'%(rowx), u'Барааны зарлага', data_center_bold)
            sheet.write('I%s'%(rowx), u'Барааны эцсийн үлдэгдэл', data_center_bold)
        

            rowx += 2
            datas = False
            purchase_income = []
            customer_income = []
            sale_expense = []
            customer_expense = []
            internal_income = []
            internal_expense = []
            expense = []
            f_income = []
            f_expense = []
            sale_expo = []
            wh_obj = self.env['stock.warehouse']
            loc_obj = self.env['stock.location']
            loc_ids = []
            if len(data['warehouse_ids'])==1:
                wh_id = wh_obj.browse(data['warehouse_ids'][0])
            else:
                for wh in data['warehouse_ids']:
                    wh_id = wh_obj.browse(wh)
                    for li in wh_id:
                        loc_ids.append(li.lot_stock_id.id)
            
            loc_id = wh_id.lot_stock_id.id
            if len(str(loc_id))==1:
                loc_ids.append(loc_id)
            else:
                if loc_id:
                    for line in loc_id:
                        loc_ids.append(line.id)
                        if line.child_ids:
                            for lin in line.child_ids:
                                loc_ids.append(lin.id)
                                if lin.child_ids:
                                    for lins in lin.child_ids:
                                        loc_ids.append(lins.id)
            if product_id !=False and loc_ids !=False:          
                #Эхний үлдэгдэл
                # Барааны орлого
                self.env.cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from 
                            stock_move as mv 
                            left join stock_location as sl on mv.location_id=sl.id
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                            where mv.state='done' and mv.product_id = %s and 
                            date(mv.date) <'%s' and dest_id.id = %s and sl.usage in( 'supplier','customer','inventory','internal','production') and dest_id.usage = 'internal' 
                            group by mv.product_id """%(product_id,data['start_date'],loc_ids[0]))
                f_income = self.env.cr.dictfetchall()
                
                # Барааны зарлага
                self.env.cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from 
                            stock_move as mv 
                            left join stock_location as sl on mv.location_id=sl.id
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                            where mv.state='done' and mv.product_id = %s and 
                            date(mv.date) <'%s' and sl.id = %s and sl.usage in('internal') and dest_id.usage in ('production','customer','supplier','inventory','internal') 
                            group by mv.product_id """%(product_id,data['start_date'],loc_ids[0]))
                f_expense = self.env.cr.dictfetchall()
                
                #Худалдан авалтын барааны орлого
                self.env.cr.execute("""  select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from stock_move as mv 
                                left join stock_location as sl on sl.id=mv.location_id
                                left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                where mv.state='done'  and 
                                date(mv.date) >='%s' and date(mv.date) <='%s' and sl.usage ='supplier' 
                                and dest_id.usage='internal' and mv.product_id=%s and dest_id.id = %s group by mv.product_id """%(data['start_date'],data['end_date'],product_id,loc_ids[0]))
                purchase_income = self.env.cr.dictfetchall()
                
                
                #Захиалагчаас орсон орлого
                self.env.cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from stock_move as mv 
                                left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                left join stock_location as src_id on mv.location_id = src_id.id
                                where mv.state='done' and 
                                date(mv.date) >='%s' and date(mv.date) <='%s' and dest_id.usage='internal' 
                                and src_id.usage='customer' and mv.product_id=%s and  mv.location_dest_id = %s 
                                group by mv.product_id """%(data['start_date'],data['end_date'],product_id,loc_ids[0]))
                customer_income = self.env.cr.dictfetchall()
                
                 #Дотоод хөдөлгөөнөөс орсон орлого
                self.env.cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from stock_move as mv 
                                left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                left join stock_location as src_id on mv.location_id = src_id.id
                                where mv.state='done' and 
                                date(mv.date) >='%s' and date(mv.date) <='%s' and dest_id.usage='internal' 
                                and src_id.usage='internal' and mv.product_id=%s and  dest_id.id = %s 
                                group by mv.product_id """%(data['start_date'],data['end_date'],product_id,loc_ids[0]))
                internal_income = self.env.cr.dictfetchall()
                
                #Тооллогоос орсон орлого
                self.env.cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from stock_move as mv 
                                left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                left join stock_location as src_id on mv.location_id = src_id.id
                                where mv.state='done' and 
                                date(mv.date) >='%s' and date(mv.date) <='%s' and dest_id.usage='internal' 
                                and src_id.usage='inventory' and mv.product_id=%s and  dest_id.id = %s 
                                group by mv.product_id """%(data['start_date'],data['end_date'],product_id,loc_ids[0]))
                qty_income = self.env.cr.dictfetchall()
                
                
    
                
                
                #Борлуулсан барааны зарлага
                self.env.cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from stock_move as mv 
                        left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                        left join stock_location as src_id on mv.location_id = src_id.id
                        where mv.state='done' and 
                        date(mv.date) >='%s' and date(mv.date) <='%s' and dest_id.usage='customer' 
                        and src_id.usage='internal' and mv.product_id=%s and src_id.id = %s group by mv.product_id """%(data['start_date'],data['end_date'],product_id,loc_ids[0]))
                sale_expense = self.env.cr.dictfetchall()
                
                #Хуадалдан авалтын барааны буцаалт
                self.env.cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from stock_move as mv 
                        left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                        left join stock_location as src_id on mv.location_id = src_id.id
                        where mv.state='done' and 
                        date(mv.date) >='%s' and date(mv.date) <='%s' and dest_id.usage = 'supplier' 
                        and src_id.usage='internal' and mv.product_id=%s and src_id.id = %s group by mv.product_id """%(data['start_date'],data['end_date'],product_id,loc_ids[0]))
                pur_ret = self.env.cr.dictfetchall()
                
                #Дотоод барааны зарлага
                self.env.cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from stock_move as mv 
                        left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                        left join stock_location as src_id on mv.location_id = src_id.id
                        where mv.state='done' and 
                        date(mv.date) >='%s' and date(mv.date) <='%s' and dest_id.usage='internal' 
                        and src_id.usage='internal' and mv.product_id=%s and src_id.id = %s group by mv.product_id """%(data['start_date'],data['end_date'],product_id,loc_ids[0]))
                internal_expense = self.env.cr.dictfetchall()
                
                
                #Тооллогын зарлага
                self.env.cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from stock_move as mv 
                        left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                        left join stock_location as src_id on mv.location_id = src_id.id
                        where mv.state='done' and 
                        date(mv.date) >='%s' and date(mv.date) <='%s' and dest_id.usage='inventory' 
                        and src_id.usage='internal' and mv.product_id=%s and src_id.id = %s group by mv.product_id """%(data['start_date'],data['end_date'],product_id,loc_ids[0]))
                qty_expense = self.env.cr.dictfetchall()
                
                
              
                
            elif product_id == False and loc_ids !=False:
                if len(loc_ids)==1:
                    #Эхний үлдэгдэл
                    # Барааны орлого
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from 
                                stock_move as mv 
                                left join stock_location as sl on mv.location_id=sl.id
                                left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                where mv.state='done'  and 
                                date(mv.date) < '%s' and  dest_id.id = %s and 
                                sl.usage in('supplier','customer','inventory','production','internal') and dest_id.usage = 'internal' 
                                group by mv.product_id """%(data['start_date'],loc_ids[0]))
                    f_income = self._cr.dictfetchall()
                    
                    # Барааны зарлага
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from 
                                stock_move as mv 
                                left join stock_location as sl on mv.location_id=sl.id
                                left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                where mv.state='done' and 
                                date(mv.date) <'%s' and  sl.id = %s and sl.usage in('internal') 
                                and dest_id.usage in ('customer','supplier','inventory','production','internal') group by mv.product_id """%(data['start_date'],loc_ids[0]))
                    f_expense = self._cr.dictfetchall()
                    
                    #Худалдан авалтын барааны орлого
                    self._cr.execute("""  select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from stock_move as mv 
                                    left join stock_location as sl on sl.id=mv.location_id
                                    left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                    where mv.state='done'  and 
                                    date(mv.date) >='%s' and date(mv.date) <='%s' and  dest_id.id = %s and sl.usage ='supplier' 
                                    and dest_id.usage='internal' group by mv.product_id """%(data['start_date'],data['end_date'],loc_ids[0]))
                    purchase_income = self._cr.dictfetchall()
                    
                    
                    #Захиалагчаас орсон орлого
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                                    left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                    left join stock_location as src_id on mv.location_id = src_id.id
                                    where mv.state='done' and 
                                    date(mv.date) >='%s' and date(mv.date) <='%s'  and  dest_id.id = %s and dest_id.usage='internal' 
                                    and src_id.usage='customer' group by mv.product_id """%(data['start_date'],data['end_date'],loc_ids[0]))
                    customer_income = self._cr.dictfetchall()
                    
                    
                     #Дотоод орсон орлого
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                                    left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                    left join stock_location as src_id on mv.location_id = src_id.id
                                    where mv.state='done' and 
                                    date(mv.date) >='%s' and date(mv.date) <='%s'  and  dest_id.id = %s and dest_id.usage='internal' 
                                    and src_id.usage='internal' group by mv.product_id """%(data['start_date'],data['end_date'],loc_ids[0]))
                    internal_income = self._cr.dictfetchall()
                    
                     #Тооллогоос орсон орлого
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                                    left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                    left join stock_location as src_id on mv.location_id = src_id.id
                                    where mv.state='done' and 
                                    date(mv.date) >='%s' and date(mv.date) <='%s'  and  dest_id.id = %s and dest_id.usage='internal' 
                                    and src_id.usage='inventory' group by mv.product_id """%(data['start_date'],data['end_date'],loc_ids[0]))
                    qty_income = self._cr.dictfetchall()
                    
                    
                    
                    
                    
                    
                    
                    #Борлуулсан барааны зарлага
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                            left join stock_location as src_id on mv.location_id = src_id.id
                            where mv.state='done' and 
                            date(mv.date) >='%s' and date(mv.date) <='%s' and src_id.id = %s and dest_id.usage='customer' 
                            and src_id.usage='internal'  group by mv.product_id """%(data['start_date'],data['end_date'],loc_ids[0]))
                    sale_expense = self._cr.dictfetchall()
                    
                    #Худалдан авалтын барааны буцаалт
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                            left join stock_location as src_id on mv.location_id = src_id.id
                            where mv.state='done' and 
                            date(mv.date) >='%s' and date(mv.date) <='%s' and src_id.id = %s and dest_id.usage='supplier' 
                            and src_id.usage='internal'  group by mv.product_id """%(data['start_date'],data['end_date'],loc_ids[0]))
                    pur_ret = self._cr.dictfetchall()
                    
                    #Дотоод барааны зарлага
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                            left join stock_location as src_id on mv.location_id = src_id.id
                            where mv.state='done' and 
                            date(mv.date) >='%s' and date(mv.date) <='%s' and src_id.id = %s and dest_id.usage='internal' 
                            and src_id.usage='internal'  group by mv.product_id """%(data['start_date'],data['end_date'],loc_ids[0]))
                    internal_expense = self._cr.dictfetchall()
                    
                    
                    #Тооллого барааны зарлага
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                            left join stock_location as src_id on mv.location_id = src_id.id
                            where mv.state='done' and 
                            date(mv.date) >='%s' and date(mv.date) <='%s' and src_id.id = %s and dest_id.usage='inventory' 
                            and src_id.usage='internal'  group by mv.product_id """%(data['start_date'],data['end_date'],loc_ids[0]))
                    qty_expense = self._cr.dictfetchall()
                    
                    
                    
                else:
                    #Эхний үлдэгдэл
                    # Барааны орлого
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from 
                                stock_move as mv 
                                left join stock_location as sl on mv.location_id=sl.id
                                left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                where mv.state='done'  and 
                                date(mv.date) <'%s' and  dest_id.id in %s and sl.usage in('supplier','customer','inventory','production','internal') 
                                and dest_id.usage = 'internal' group by mv.product_id """%(data['start_date'],tuple(loc_ids)))
                    f_income = self._cr.dictfetchall()
                    
                    # Барааны зарлага
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from 
                                stock_move as mv 
                                left join stock_location as sl on mv.location_id=sl.id
                                left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                where mv.state='done' and 
                                date(mv.date) <'%s' and  sl.id in %s and sl.usage in('internal') and dest_id.usage in ('customer','supplier','inventory','production','internal') 
                                group by mv.product_id """%(data['start_date'],tuple(loc_ids)))
                    f_expense = self._cr.dictfetchall()
                    
                    #Худалдан авалтын барааны орлого
                    self._cr.execute("""  select mv.product_id,sum(mv.product_qty), avg(mv.price_unit) as price from stock_move as mv 
                                    left join stock_location as sl on sl.id=mv.location_id
                                    left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                    where mv.state='done'  and 
                                    date(mv.date) >='%s' and date(mv.date) <='%s' and  dest_id.id in %s and sl.usage ='supplier' 
                                    and dest_id.usage='internal' group by mv.product_id """%(data['start_date'],data['end_date'],tuple(loc_ids)))
                    purchase_income = self._cr.dictfetchall()
                    
                   
                    
                    #Захиалагчаас орсон орлого
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                                    left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                    left join stock_location as src_id on mv.location_id = src_id.id
                                    where mv.state='done' and 
                                    date(mv.date) >='%s' and date(mv.date) <='%s'  and  src_id.id in %s and dest_id.usage='internal' 
                                    and src_id.usage='customer' group by mv.product_id """%(data['start_date'],data['end_date'],tuple(loc_ids)))
                    customer_income = self._cr.dictfetchall()
                    
                    #Дотоод орсон орлого
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                                    left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                    left join stock_location as src_id on mv.location_id = src_id.id
                                    where mv.state='done' and 
                                    date(mv.date) >='%s' and date(mv.date) <='%s'  and  dest_id.id in %s and dest_id.usage='internal' 
                                    and src_id.usage='internal' group by mv.product_id """%(data['start_date'],data['end_date'],tuple(loc_ids)))
                    internal_income = self._cr.dictfetchall()
                    
                    
                    #Тооллогоос орсон орлого
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                                    left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                    left join stock_location as src_id on mv.location_id = src_id.id
                                    where mv.state='done' and 
                                    date(mv.date) >='%s' and date(mv.date) <='%s'  and  dest_id.id in %s and dest_id.usage='internal' 
                                    and src_id.usage='inventory' group by mv.product_id """%(data['start_date'],data['end_date'],tuple(loc_ids)))
                    qty_income = self._cr.dictfetchall()
                    
                    
                    #Борлуулсан барааны зарлага
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                            left join stock_location as src_id on mv.location_id = src_id.id
                            where mv.state='done' and 
                            date(mv.date) >='%s' and date(mv.date) <='%s' and src_id.id in %s and dest_id.usage='customer' 
                            and src_id.usage='internal'  group by mv.product_id """%(data['start_date'],data['end_date'],tuple(loc_ids)))
                    sale_expense = self._cr.dictfetchall()
                    
                    #Борлуулсан барааны зарлага
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                            left join stock_location as src_id on mv.location_id = src_id.id
                            where mv.state='done' and 
                            date(mv.date) >='%s' and date(mv.date) <='%s' and src_id.id in %s and dest_id.usage='supplier' 
                            and src_id.usage='internal'  group by mv.product_id """%(data['start_date'],data['end_date'],tuple(loc_ids)))
                    pur_ret = self._cr.dictfetchall()
                    
                    
                    #Дотоод барааны зарлага
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                            left join stock_location as src_id on mv.location_id = src_id.id
                            where mv.state='done' and 
                            date(mv.date) >='%s' and date(mv.date) <='%s' and src_id.id in %s and dest_id.usage='internal' 
                            and src_id.usage='internal'  group by mv.product_id """%(data['start_date'],data['end_date'],tuple(loc_ids)))
                    internal_expense = self._cr.dictfetchall()
                    
                    #Тооллого барааны зарлага
                    self._cr.execute("""select mv.product_id,sum(mv.product_qty ), avg(mv.price_unit) as price from stock_move as mv 
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                            left join stock_location as src_id on mv.location_id = src_id.id
                            where mv.state='done' and 
                            date(mv.date) >='%s' and date(mv.date) <='%s' and src_id.id in %s and dest_id.usage='inventory' 
                            and src_id.usage='internal'  group by mv.product_id """%(data['start_date'],data['end_date'],tuple(loc_ids)))
                    qty_expense = self._cr.dictfetchall()
                    
          
                
                
            product = []
            products = False
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
                    if self.is_transection == True:
                        if len(loc_ids)==1:
                            self._cr.execute("""select mv.product_id from stock_move as mv 
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                left join stock_location as src_id on mv.location_id = src_id.id 
                                where src_id.id = %s  or dest_id.id = %s group by mv.product_id"""%(loc_ids[0],loc_ids[0]))
                            products = self._cr.dictfetchall()
                        else:
                            self._cr.execute("""select mv.product_id from stock_move as mv 
                            left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                                left join stock_location as src_id on mv.location_id = src_id.id 
                                where src_id.id in %s  or dest_id.id in %s group by mv.product_id"""%(tuple(loc_ids),tuple(loc_ids)))
                            products = self._cr.dictfetchall()
                    else:
                        product_ids = product_obj.search([],order='name asc')
                        for pr in product_ids:
                            product.append(pr.id)
                        
            num = 0
            f_standard_price = 0.0
            f_list_price = 0.0
            total_income_pur_qty = 0.0
            total_income_oth_qty = 0.0
            total_expense_sale_qty= 0.0
            total_qty_income_qty = 0.0
            total_end_oth_qty = 0.0
            total_expense_qty = 0.0
            total_qty_exp_qty = 0.0
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
            if self.is_transection == True:
                if products:
                    for line in products:
                        product.append(line['product_id'])
            rowx = 6
            for line in product_obj.browse(product):
                num +=1
                f_income_qty = 0.0
                f_income_price = 0.0
                f_expense_qty = 0.0
                f_expense_price = 0.0
                pur_income_qty = 0.0
                pur_income_price = 0.0
                custom_income_qty = 0.0
                custom_income_price = 0.0
                int_income_qty = 0.0
                int_income_price = 0.0
                qty_income_qty = 0.0
                qty_income_price = 0.0
                income_qty = 0.0
                expense_qty = 0.0
                expense_int_qty = 0.0
                expense_int_price = 0.0
                income_price = 0.0
                sale_expense_qty = 0.0
                sale_expense_price = 0.0
                qty_expense_qty = 0.0
                qty_expense_price = 0.0
                cust_expense_qty = 0.0
                oth_expense_qty = 0.0
                expense_price = 0.0
                end_qty =0.0
                expo_qty = 0.0
                expo_price = 0.0
                seri = ''
                if f_income!=[]:
                    for f_inc in f_income:
                        if line.id==f_inc['product_id']:
                            if f_inc['sum'] !=None:
                                f_income_qty += f_inc['sum']
                            if f_inc['price'] !=None:
                                f_income_price +=f_inc['price']
                                
                if f_expense !=[]:
                    for f_exp in f_expense:
                        if line.id==f_exp['product_id']:
                            if f_exp['sum'] !=None:
                                f_expense_qty +=f_exp['sum']
                            if f_exp['price'] !=None:
                                f_expense_price +=f_exp['price']
    
                if purchase_income!=[]:
                    for pur_income in purchase_income:
                        if line.id==pur_income['product_id']:
                            if pur_income['sum'] !=None:
                                pur_income_qty += pur_income['sum']
                            if pur_income['price'] !=None:
                                pur_income_price += pur_income['price']
                                
                if customer_income!=[]:
                    for cust_income in customer_income:
                        if line.id==cust_income['product_id']:
                            if cust_income['sum'] !=None:
                                custom_income_qty += cust_income['sum']
                            if cust_income['price'] !=None:
                                custom_income_price += cust_income['price']
                                
                if internal_income!=[]:
                    for int_income in internal_income:
                        if line.id==int_income['product_id']:
                            if int_income['sum'] !=None:
                                int_income_qty += int_income['sum']
                            if int_income['price'] !=None:
                                int_income_price += int_income['price']
                                
                if qty_income!=[]:
                    for qt_income in qty_income:
                        if line.id==qt_income['product_id']:
                            if qt_income['sum'] !=None:
                                qty_income_qty += qt_income['sum']
                            if qt_income['price'] !=None:
                                qty_income_price += qt_income['price']
  
                                
    
    
                                
                if sale_expense !=[]:
                    for sale_expen in sale_expense:
                        if line.id==sale_expen['product_id']:
                            if sale_expen['sum'] !=None:
                                sale_expense_qty +=sale_expen['sum']
                            if sale_expen['price'] !=None:
                                sale_expense_price +=sale_expen['price']
                                
                if pur_ret !=[]:
                    for sale_exp in pur_ret:
                        if line.id==sale_exp['product_id']:
                            if sale_exp['sum'] !=None:
                                expo_qty +=sale_exp['sum']
                            if sale_exp['price'] !=None:
                                expo_price +=sale_exp['price']
                                
                if internal_expense !=[]:
                    for inter_exp in internal_expense:
                        if line.id==inter_exp['product_id']:
                            if inter_exp['sum'] !=None:
                                expense_int_qty +=inter_exp['sum']
                            if inter_exp['price'] !=None:
                                expense_int_price +=inter_exp['price']
                                
                if qty_expense !=[]:
                    for qty_exp in qty_expense:
                        if line.id==qty_exp['product_id']:
                            if qty_exp['sum'] !=None:
                                qty_expense_qty +=qty_exp['sum']
                            if qty_exp['price'] !=None:
                                qty_expense_price +=qty_exp['price']
                                
                            
                first_qty = f_income_qty - f_expense_qty
                end_qty = first_qty+(pur_income_qty+custom_income_qty+int_income_qty+qty_income_qty)-(sale_expense_qty+expo_qty+expense_int_qty+qty_expense_qty)
                total_price_unit = (f_income_qty*f_income_price)-(f_expense_qty*f_expense_price)+((pur_income_qty*pur_income_price)+(custom_income_qty*custom_income_price)+(int_income_qty*int_income_price)+(qty_income_qty*qty_income_price))-((sale_expense_qty*sale_expense_price)+(expo_qty*expo_price)+(expense_int_qty*expense_int_price)+(qty_expense_qty*qty_expense_price))
                uom_name = ''
                if line.uom_id:
                    uom_name = line.uom_id.name
                sheet.write('A%s'%rowx, num, data_center)
                sheet.write('B%s'%rowx, u'%s'%line.name, data_left)
                sheet.write('C%s'%rowx, line.barcode or '', data_center)
                sheet.write('D%s'%rowx, line.default_code or '', data_center)
                sheet.write('E%s'%rowx, u'%s'%(uom_name), data_center)
                sheet.write('F%s'%rowx, first_qty, data_right)
                sheet.write('G%s'%rowx, (pur_income_qty+custom_income_qty+int_income_qty+qty_income_qty), data_right)
                sheet.write('H%s'%rowx, sale_expense_qty+expo_qty+expense_int_qty+qty_expense_qty, data_right)
                sheet.write('I%s'%rowx, first_qty+(pur_income_qty+custom_income_qty+int_income_qty+qty_income_qty)-(sale_expense_qty+expo_qty+expense_int_qty+qty_expense_qty), data_right)
                
                if total_price_unit==0.0:
                    sheet.write('S%s'%rowx, 0.0, data_right)
                else:
                    if end_qty == 0.0:
                        sheet.write('S%s'%rowx, 0.0, data_right)
                    else:
                        sheet.write('S%s'%rowx, total_price_unit/end_qty, data_right)
                sheet.write('T%s'%rowx, total_price_unit, data_right)
                if end_qty == 0.0:
                    total_sum_price +=total_price_unit
                else:
                    total_sum_price +=total_price_unit/end_qty
                total_all_price +=total_price_unit
                
                f_total_qty +=first_qty
                total_income_pur_qty +=pur_income_qty
                total_income_cus_qty +=custom_income_qty
                total_income_qty +=(pur_income_qty+custom_income_qty+int_income_qty+qty_income_qty)
                total_expense_cust_qty +=cust_expense_qty
                total_expense_sale_qty +=sale_expense_qty
                total_end_qty +=end_qty
                total_qty +=(sale_expense_qty+expo_qty+expense_int_qty+qty_expense_qty)
                total_end_oth_qty +=oth_expense_qty
                total_qty_income_qty +=qty_income_qty
                total_qty_exp_qty +=qty_expense_qty
                total_income_int_qty +=int_income_qty
                total_expo_qty +=expo_qty
                total_exp_int_qty +=expense_int_qty
                rowx +=1
            

        workbook.close()
        output.seek(0)
        if get_file:
            return output.read()
        response.stream.write(output.read())
        output.close()
        return



