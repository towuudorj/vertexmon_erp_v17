# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import defaultdict
    
class StockMove(models.Model):
    _inherit = 'stock.move'


    @api.depends('picking_id')
    def _compute_all_price(self):
        for line in self:
            total = 0.0
            if  line.picking_id.sale_id.order_line:
                for lines in self.picking_id.sale_id.order_line:
                    if lines.product_id.id == line.product_id.id:
                        if lines.discount > 0.0:
                            total = (lines.price_subtotal/lines.product_uom_qty)*line.product_uom_qty   
                        else:
                            if lines.price_subtotal>0.0 and lines.product_uom_qty >0.0:
                                total = (lines.price_subtotal/lines.product_uom_qty)*line.product_uom_qty
            else:
                if line.product_uom_qty >0.0 and line.sale_prices >0.0:
                    total = line.product_uom_qty * line.sale_prices
                else:
                    total = 0.0
            line.price_subtotal = total 
    
    @api.depends('picking_id')
    def _compute_list_price(self):
        for line in self:
            sale_price = 0.0
            if line.picking_id.sale_id.order_line:
                for lines in line.picking_id.sale_id.order_line:
                    if lines.product_id.id == line.product_id.id:
                        if lines.discount > 0.0:
                            sale_price = lines.price_unit/1.1
                        else:
                            sale_price = lines.price_unit/1.1
            else:
                sale_price = line.sale_prices
            line.sale_price = sale_price

    
    @api.depends('picking_id')
    def _compute_untaxed_amount(self):
        for line in self:
            total = 0.0
            if line.picking_id.sale_id.order_line:
                for lines in line.picking_id.sale_id.order_line:
                    if lines.product_id.id == line.product_id.id:
                        if lines.discount > 0.0:
                            total = lines.price_subtotal 
                        else:
                            total = lines.price_subtotal

            line.untaxed_amount = total 
    
    @api.depends('picking_id')
    def _compute_tax_amount(self):
        for line in self:
            tax_amount = 0.0
            if line.picking_id.sale_id.order_line:
                for lines in line.picking_id.sale_id.order_line:
                    if lines.product_id.id == line.product_id.id:
                        if lines.discount > 0.0:
                            tax_amount = lines.price_tax
                        else:
                            tax_amount = lines.price_tax

            line.tax_amount = tax_amount

    @api.depends('picking_id')
    def _compute_discount(self):
        for line in self:
            discount = 0.0
            if line.picking_id.sale_id.order_line:
                for lines in line.picking_id.sale_id.order_line:
                    if lines.product_id.id == line.product_id.id:
                        if lines.discount > 0.0:
                            discount = lines.discount
                        else:
                            discount = lines.discount

            line.discount = discount
    
    price_subtotal = fields.Float(string=u'Нийт үнэ',compute='_compute_all_price')
    sale_price = fields.Float(string=u'Зарах үнэ',compute='_compute_list_price', readonly=False)
    sale_prices = fields.Float(string=u'Зарах үнэ')
    untaxed_amount = fields.Float(string=u'Татваргүй үнэ',compute='_compute_untaxed_amount')
    tax_amount = fields.Float(string=u'Татваргүй үнэ',compute='_compute_tax_amount')
    discount = fields.Float(string=u'Хөнгөлөлт', compute='_compute_discount')
    




        
        


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
        
    @api.depends('picking_id')
    def _compute_all_price(self):
        for line in self:
            total = 0.0
            if  line.picking_id.sale_id.order_line:
                for lines in self.picking_id.sale_id.order_line:
                    if lines.product_id.id==line.product_id.id:
                        if lines.discount > 0.0:
                            total = lines.price_subtotal
                        else:
                            total = lines.price_subtotal
            else:
                for lis in line.picking_id.move_ids_without_package:
                    if lis.product_id.id == line.product_id.id:
                        if line.quantity >0.0 and lis.sale_prices >0.0:
                            total = line.quantity * lis.sale_prices
                        else:
                            total = 0.0
                else:
                    total = line.quantity * line.sale_price

            line.price_subtotal = total 
    
    @api.depends('picking_id')
    def _compute_list_price(self):
        for line in self:
            sale_price = 0.0
            if line.picking_id.sale_id.order_line:

                for lines in self.picking_id.sale_id.order_line:
                    if lines.product_id.id == line.product_id.id and lines.id:
                        if lines.discount > 0.0:
                            sale_price = lines.price_unit/1.1
                        else:
                            sale_price = lines.price_unit/1.1
            else:
                if line.picking_id.move_ids_without_package:
                    for lis in line.picking_id.move_ids_without_package:
                        if lis.product_id.id == line.product_id.id and lis.sale_prices > 0.0:
                            sale_price = lis.sale_prices
                else:
                    sale_price = line.sale_prices

            line.sale_price = sale_price
    
    @api.depends('picking_id')
    def _compute_untaxed_amount(self):
        for line in self:
            untaxed_amount = 0.0
            if self.picking_id.sale_id.order_line:
                for lines in self.picking_id.sale_id.order_line:
                    if lines.product_id.id == line.product_id.id:
                        if lines.discount > 0.0:
                            untaxed_amount = lines.price_subtotal
                        else:
                            untaxed_amount = lines.price_subtotal
            line.untaxed_amount = untaxed_amount

    @api.depends('picking_id')
    def _compute_tax_amount(self):
        for line in self:
            tax_amount = 0.0
            if self.picking_id.sale_id.order_line:
                for lines in self.picking_id.sale_id.order_line:
                    if lines.product_id.id == line.product_id.id:
                        if lines.discount > 0.0:
                            tax_amount = lines.price_tax
                        else:
                            tax_amount = lines.price_tax
            line.tax_amount = tax_amount

    
    @api.depends('picking_id')
    def _compute_tax_amount(self):
        for line in self:
            discount = 0.0
            if self.picking_id.sale_id.order_line:
                for lines in self.picking_id.sale_id.order_line:
                    if lines.product_id.id == line.product_id.id:
                        if lines.discount > 0.0:
                            discount = lines.discount
                        else:
                            discount = lines.discount
            line.discount = discount
    
    
    
    price_subtotal=fields.Float(string=u'Нийт үнэ',compute='_compute_all_price')
    sale_price = fields.Float(string=u'Зарах үнэ',compute='_compute_list_price', readonly=False)
    sale_prices = fields.Float(string=u'Зарах үнэ')
    untaxed_amount = fields.Float(string=u'Татваргүй үнэ',compute='_compute_untaxed_amount')
    tax_amount = fields.Float(string=u'Татваргүй үнэ',compute='_compute_tax_amount')
    discount = fields.Float(string=u'Хөнгөлөлт', compute='_compute_discount')