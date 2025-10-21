# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta, datetime
import xlwt, json
from odoo.tools import date_utils
import io
import json
import xlsxwriter

class ProductQuantityPage(models.TransientModel):
    """
        Барааны материалын тооллогын хуудас
    """
    _name = "product.quantity.page"
    _description = "Stock product quantity page"

    company_id = fields.Many2one('res.company', string=u'Компани',readonly=True,
                                default=lambda self: self.env.user.company_id)
    category_id = fields.Many2one('product.category', string=u'Барааны ангилал')
    product_id = fields.Many2one('product.product', string=u'Бараа')
    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', default=fields.Date.context_today)

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'categ_id':self.category_id.id,
            'product_id': self.product_id.id,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {
                     'model': 'product.quantity.page',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'product_quantity_page_report',}
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
        
        data_center = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'font_size': 12,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00'
                                    })

        product_obj = self.env['product.product']
        category_obj = self.env['product.category']
        category_id = False
        product_id = False
        if data['categ_id']:
            category_id = data['categ_id']
        if data['product_id']:
            product_id = data['product_id']

        
        sheet.merge_range('A1:D1', u'Байгууллагын нэр: %s' % (data['company_name']), data_left)
        
        sheet.merge_range('A2:G2', u'Барааны материалын тоологын хуудас', head_title)
        

        rowx = 4
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 10, 20)

        sheet.write('A%s'%(rowx), u'Д/д', txt_center)
        sheet.write('B%s'%(rowx), u'Барааны нэр', txt_center)
        sheet.write('C%s'%(rowx), u'Барааны код', txt_center)
        sheet.write('D%s'%(rowx), u'Дотоод код', txt_center)
        sheet.write('E%s'%(rowx), u'Барааны хэмжих нэгж', txt_center)
        sheet.write('F%s'%(rowx), u'Тоолсон тоо', txt_center)
        sheet.write('G%s'%(rowx), u'Тоолсон ажилтан', txt_center)
        
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
        for pro in products:
            rowx += 1
            sheet.write('A%s'%(rowx), rowx-4, data_right)
            sheet.write('B%s'%(rowx), pro.name, data_left)
            sheet.write('C%s'%(rowx), pro.barcode or '', data_left)
            sheet.write('D%s'%(rowx), pro.default_code or '', data_left)
            sheet.write('E%s'%(rowx), pro.uom_id.name or '', data_left)
            sheet.write('F%s'%(rowx), '', data_left)
            sheet.write('G%s'%(rowx), '', data_left)
        
        rowx += 2
        sheet.write("C%s"%(rowx + 3), u"Хянасан ажилтан: ..................................................../                                            /",)
        sheet.write("C%s"%(rowx + 4), u"Тоолсон гаргасан: ..................................................../                                            /",)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()