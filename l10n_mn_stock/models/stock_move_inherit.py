# -*- coding: utf-8 -*-

from odoo import fields, models, api
from collections import defaultdict
from odoo.tools.float_utils import float_round, float_is_zero, float_compare
    
class StockMove(models.Model):
    _inherit = 'stock.move'


    def product_price_update_before_done(self, forced_qty=None):
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        for move in self:
            if not move._is_in():
                continue
            if move.with_company(move.company_id).product_id.cost_method == 'standard':
                continue
            product_tot_qty_available = move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[move.product_id.id]
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            quantity = 0
            for valued_move_line in valued_move_lines:
                quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.quantity, move.product_id.uom_id)

            qty = forced_qty or quantity
            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
            elif float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) or \
                    float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
            else:
                # Get the standard price
                amount_unit = std_price_update.get((move.company_id.id, move.product_id.id)) or move.product_id.with_company(move.company_id).standard_price
                new_std_price = ((amount_unit * product_tot_qty_available) + (move._get_price_unit() * qty)) / (product_tot_qty_available + qty)
            tmpl_dict[move.product_id.id] += quantity
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write({'standard_price': new_std_price})
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price

    def _get_in_svl_vals(self, forced_quantity):
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_in_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.quantity, move.product_id.uom_id)
            unit_cost = move.product_id.standard_price
            if move.product_id.cost_method != 'standard':
                unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).
            svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % (move.picking_id.name or move.name)
            svl_vals_list.append(svl_vals)
        return svl_vals_list

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

    @api.depends('picking_id')
    def _compute_cost_price(self):
        for line in self:
            cost_price = 0
            if line.location_usage in ['internal','transit'] and line.location_dest_usage not in ['internal','transit']:
                if line.picking_id.analytic_id and line.picking_id.analytic_id.project_ids and line.picking_id.analytic_id.project_ids[0].products_line:
                    product_line = line.picking_id.analytic_id.project_ids[0].products_line.filtered(lambda p_line: p_line.product_id.id == line.product_id.id)
                    if product_line:
                        cost_price = product_line[0].cost_price
                if cost_price == 0.0:
                    cost_price = line.product_id.standard_price
                line.cost_price = cost_price
                line.total_cost_price = line.quantity * cost_price
            else:
                line.cost_price = 0
                line.total_cost_price = 0

    price_subtotal=fields.Float(string=u'Нийт үнэ',compute='_compute_all_price')
    sale_price = fields.Float(string=u'Зарах үнэ',compute='_compute_list_price', readonly=False)
    sale_prices = fields.Float(string=u'Зарах үнэ')
    untaxed_amount = fields.Float(string=u'Татваргүй үнэ',compute='_compute_untaxed_amount')
    tax_amount = fields.Float(string=u'Татваргүй үнэ',compute='_compute_tax_amount')
    discount = fields.Float(string=u'Хөнгөлөлт', compute='_compute_discount')
    delivered_qty = fields.Integer(string='Delivered qty')
    package_no = fields.Char(string='Package no')
    net_weight = fields.Float(string='Net weight (kg)')
    gross_weight = fields.Float(string='Gross weight (kg)')
    dimensions = fields.Char(string='Dimensions')
    cbm = fields.Float(string='CBM')
    po_origin = fields.Char(related="picking_id.origin", string=u'Баримтын дугаар', store=True)
    cost_price = fields.Float(string="Өртөг үнэ", compute='_compute_cost_price')
    total_cost_price = fields.Float('Нийт өртөг', compute='_compute_cost_price')
    analytic_id = fields.Many2one(related='picking_id.analytic_id', store=True)

