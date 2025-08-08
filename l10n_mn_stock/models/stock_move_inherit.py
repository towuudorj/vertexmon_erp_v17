# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import defaultdict
from odoo.tools.float_utils import float_round, float_is_zero, float_compare
    
class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if self._should_ignore_pol_price():
            return super(StockMove, self)._get_price_unit()
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        line = self.purchase_line_id
        order = line.order_id
        received_qty = line.qty_received
        if self.state == 'done':
            received_qty -= self.product_uom._compute_quantity(self.quantity, line.product_uom, rounding_method='HALF-UP')
        if float_compare(line.qty_invoiced, received_qty, precision_rounding=line.product_uom.rounding) > 0:
            move_layer = line.move_ids.sudo().stock_valuation_layer_ids
            invoiced_layer = line.sudo().invoice_lines.stock_valuation_layer_ids
            # value on valuation layer is in company's currency, while value on invoice line is in order's currency
            receipt_value = 0
            
            if move_layer:
                
                receipt_value += sum(move_layer.mapped(lambda l: l.currency_id._convert(
                    l.value, order.currency_id, order.company_id, l.stock_move_id.picking_id.date_done, round=False)))
                
            if invoiced_layer:
                receipt_value += sum(invoiced_layer.mapped(lambda l: l.currency_id._convert(
                    l.value, order.currency_id, order.company_id, l.stock_move_id.picking_id.date_done, round=False)))
            invoiced_value = 0
            invoiced_qty = 0
            for invoice_line in line.sudo().invoice_lines:
                if invoice_line.tax_ids:
                    invoiced_value += invoice_line.tax_ids.with_context(round=False).compute_all(
                        invoice_line.price_unit, currency=invoice_line.currency_id, quantity=invoice_line.quantity)['total_void']
                else:
                    invoiced_value += invoice_line.price_unit * invoice_line.quantity
                invoiced_qty += invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, line.product_id.uom_id)
            # TODO currency check
            remaining_value = invoiced_value - receipt_value
            # TODO qty_received in product uom
            remaining_qty = invoiced_qty - line.product_uom._compute_quantity(received_qty, line.product_id.uom_id)
            price_unit = float_round(remaining_value / remaining_qty, precision_digits=price_unit_prec)
            
        else:
            price_unit = line._get_gross_price_unit()
        if order.currency_id != order.company_id.currency_id:
            # The date must be today, and not the date of the move since the move move is still
            # in assigned state. However, the move date is the scheduled date until move is
            # done, then date of actual move processing. See:
            # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
            price_unit = order.currency_id._convert(
                price_unit, order.company_id.currency_id, order.company_id, order.date_order, round=False)
        return price_unit


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