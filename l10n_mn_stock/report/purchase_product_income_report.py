# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime, timedelta
import xlwt, json
from odoo.tools import date_utils
import io
import json
import xlsxwriter

class PurchaseProductIncomeReport(models.TransientModel):
    """
        Барааны материалын орлого тайлан
    """
    _name = "purchase.product.income.report"
    _description = "Purchase product income"

    company_id = fields.Many2one('res.company', string=u'Компани',readonly=True,
                                default=lambda self: self.env.user.company_id)
    category_id = fields.Many2one('product.category', string=u'Барааны ангилал')
    product_id = fields.Many2one('product.product', string=u'Бараа')
    start_date = fields.Date(string='Start date')
    end_date = fields.Date('End date')
    type = fields.Selection([('purchase','Purchase income'),
                             ('internal','Internal income'),
                             ('return','Return income'),
                             ('all', 'All')],string='Type', default='purchase')


    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'categ_id':self.category_id.id,
            'product_id': self.product_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'type': self.type
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'purchase.product.income.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'purchase_product_income_report'
                     }
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
                                    'bold': True,
                                    'text_wrap': True
                                })
        
        txt_center_no_border = workbook.add_format({
                                    'align': 'center',
                                    'font_size': 12,
                                    'bold': True,
                                    'text_wrap': True
                                })

        data_right = workbook.add_format({
                                    'align': 'right',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        data_left_no_border = workbook.add_format({
                                    'align': 'left',
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
        
        data_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })
        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' % (data['company_name']), data_left_no_border)
        sheet.merge_range('A2:I2', u'Барааны орлогын тайлан', head_title)

        sheet.merge_range('F3:I3', u'Огноо: %s - %s'%(data['start_date'], data['end_date']), txt_center_no_border)
        

        rowx = 4
        sheet.set_column(0, 0, 8)
        sheet.set_column(1, 1, 40)
        sheet.set_column(2, 8, 20)

        sheet.write('A%s'%(rowx), u'Д/д', txt_center)
        sheet.write('B%s'%(rowx), u'Барааны нэр', txt_center)
        sheet.write('C%s'%(rowx), u'Барааны код', txt_center)
        sheet.write('D%s'%(rowx), u'Дотоод код', txt_center)
        sheet.write('E%s'%(rowx), u'Барааны хэмжих нэгж', txt_center)
        sheet.write('F%s'%(rowx), u'Баримтын дугаар', txt_center)
        sheet.write('G%s'%(rowx), u'Худалдан авалтын дугаар', txt_center)
        sheet.write('H%s'%(rowx), u'Орлогын огноо', txt_center)
        sheet.write('I%s'%(rowx), u'Орлогын тоо', txt_center)

        product_obj = self.env['product.product']
        category_obj = self.env['product.category']
        category_id = False
        product_id = False
        if data['categ_id']:
            category_id = data['categ_id']
        if data['product_id']:
            product_id = data['product_id']

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
                product_ids = product_obj.search([],order='name asc')
                for pr in product_ids:
                    product.append(pr.id)
        products = product_obj.search([('id','in',product)],order='name asc')
        picking_obj = self.env['stock.picking']
        for pro in products:
            
            self.env.cr.execute("""select mv.product_id, mv.product_qty, mv.picking_id  from 
                        stock_move as mv 
                        left join stock_location as sl on mv.location_id=sl.id
                        left join stock_location as dest_id on mv.location_dest_id = dest_id.id
                        where mv.state = 'done' and mv.product_id = %s and 
                        date(mv.date) >= '%s' and date(mv.date) <= '%s' and mv.company_id = %s
                        and sl.usage in ('supplier') and dest_id.usage = 'internal' 
                        group by mv.product_id, mv.picking_id, mv.product_qty """%(pro.id,data['start_date'], data['end_date'],data['company_id']))
            income_pro = self.env.cr.dictfetchall()
            
            for prod in income_pro:
                rowx += 1
                sheet.write('A%s' % (rowx), rowx - 4, data_right)
                sheet.write('B%s' % (rowx), pro.name, data_left)
                sheet.write('C%s' % (rowx), pro.barcode or '', data_left)
                sheet.write('D%s' % (rowx), pro.default_code or '', data_left)
                sheet.write('E%s' % (rowx), pro.uom_id.name or '', data_left)
                picking = picking_obj.browse(prod['picking_id'])
                sheet.write('F%s' % (rowx), '%s'%picking.name, data_left)
                sheet.write('G%s' % (rowx), '%s'%picking.origin, data_left)
                clean_str = (str(picking.scheduled_date)).split('.')[0]
                dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
                dt_plus_8 = dt + timedelta(hours=8)
                sheet.write('H%s' % (rowx), '%s'%dt_plus_8, data_left)
                sheet.write('I%s' % (rowx), prod['product_qty'], data_left)
    

        rowx += 2
        sheet.write("C%s"%(rowx + 3), u"Хянасан ажилтан: ..................................................../                                            /",)



        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


        