# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from odoo.tools import SQL



class ProjectProductsLine(models.Model):
    _name = "project.products.line"
    _description = "Project Product Line"
    _order = 'project_id, sequence, id'


    @api.depends('project_id')
    def _compute_qty_available(self):
        quant_obj = self.env['stock.quant']
        purchase_obj = self.env['purchase.order']
        for line in self:
            qty = 0
            quant = quant_obj.search([('location_id','=',line.project_id.warehouse_id.lot_stock_id.id),('product_id','=',line.product_id.id),('inventory_quantity_auto_apply','>',0.0)])
            if quant:
                for qt in quant:
                    qty +=qt.inventory_quantity_auto_apply
            else:
                qty = 0
            line.qty_available = qty
    
    @api.depends('project_id')
    def _compute_qty_delivered(self):
        quant_obj = self.env['stock.quant']
        picking_obj = self.env['stock.picking']
        for line in self:
            qty = 0
            for pick in line.project_id.picking_ids:
                for pur in pick.move_ids_without_package:
                    if pur.product_id.id == line.product_id.id:
                        qty +=pur.quantity   
            line.qty_delivered = qty
    
    project_id = fields.Many2one('project.project', string='Project', index=True, required=True, ondelete='cascade')
    
    sequence = fields.Integer(string='Sequence', default=1)
    product_id = fields.Many2one('product.product', string='Product', 
                    domain=[('purchase_ok', '=', True)], change_default=True)

    name = fields.Text(
        string="Description",
        compute='_compute_name',
        store=True, readonly=False, required=True, precompute=True)
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    price_unit = fields.Float(string='Price', required=True, digits='Product Price')
    cost_price = fields.Float(string='Cost Price', required=True, digits='Product Price')
    qty_available = fields.Float(string='Available QTY', compute='_compute_qty_available', required=True, digits='Product', readonly=True, default=0)
    qty_delivered = fields.Float(string='Delivered',  required=True, digits='Product', readonly=True, 
                                        default=0, compute="_compute_qty_delivered")
    price_total = fields.Float(string='Total Price', readonly=True)
    cost_total = fields.Float(string='Total Cost', readonly=True)
    delivery_cost = fields.Float(string='Delivery cost', compute="compute_delivery_cost")
    qty_available_cost = fields.Float(string='Qty available cost', compute="compute_qty_available_cost")
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company)
    purchase_type = fields.Selection([('local','Local'),
                                    ('foreign','Foreign')],string='Purchase Type',)
    is_task = fields.Boolean(string='Task', default=False)
    is_purchase = fields.Boolean(string='Purchase', default=False)
    purchase_manager_id = fields.Many2one('res.users', string='Purchase Manager')
    last_qty = fields.Float(string='Last qty', compute="_action_compute_qty")
    pur_qty = fields.Float(string='Purchase qty')
    picking_ids = fields.Many2many('stock.picking', string='Picking')
    change_cost = fields.Float(string='Change cost', compute="action_change_cost")
    
    
    
    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group('account.group_account_manager'):
            for vals in vals_list:
                project_id = vals.get('project_id')
                product_id = vals.get('product_id')
                if project_id and product_id:
                    project = self.env['project.project'].browse(project_id)
                    if project.state == 'process':
                        raise UserError(
                            "Эрх бүхий ажилтан биш тул засварлах боломжгүйг анхаарна уу!"
                        )
    
        return super().create(vals_list)
    
    def write(self, vals):
        for order in self:
            if order.project_id.state == 'process':
                if 'product_id' in vals or 'product_qty' in vals or 'purchase_type' in vals or 'purchase_manager_id' in vals or 'cost_price' in vals or 'price_unit' in vals:
                    if not self.env.user.has_group('account.group_account_manager'):
                        raise UserError((u"Эрх бүхий ажилтан биш тул засварлах боломжгүйг анхаарна уу !"))
        return super(ProjectProductsLine, self).write(vals)
    
    
    def action_change_cost(self):
        for line in self:
            cost = 0
            for lines in line.project_id.purchase_ids:
                for list in lines.order_line:
                    cost = ((list.price_unit * lines.currency_rate) + line.change_cost)/2
            line.change_cost = cost
            
    
    
    def compute_delivery_cost(self):
        for line in self:
            delivery_cost = 0
            if line.product_id and line.product_id.detailed_type == 'service' and line.project_id.analytic_account_id:
                query = self.env['account.move.line']._search(
                    [('move_id.move_type', 'in', self.env['account.move'].get_purchase_types())])
                query.add_where(
                    SQL(
                        "%s && %s",
                        [str(line.project_id.analytic_account_id.id)],
                        self.env['account.move.line']._query_analytic_accounts(),
                    )
                )
                query_string, query_param = query.select('DISTINCT account_move_line.move_id')
                self._cr.execute(query_string, query_param)
                move_ids = [l.get('move_id') for l in self._cr.dictfetchall()]
                invoice_ids = self.env['account.move'].browse(move_ids)
                invoice_line_ids = False
                if invoice_ids:
                    invoice_line_ids = invoice_ids.mapped('invoice_line_ids').filtered(lambda i_line: i_line.product_id.id == line.product_id.id and i_line.move_id.state == 'posted')
                if invoice_line_ids:
                    delivery_cost = abs(sum(invoice_line_ids.mapped('price_total')))
                else:
                    delivery_cost = 0
            else:
                if line.cost_price > 0.0 and line.qty_delivered > 0.0:
                    delivery_cost = line.cost_price * line.qty_delivered
                
            line.delivery_cost = delivery_cost
        
    def compute_qty_available_cost(self):
        for line in self:
            available_cost = 0
            if line.cost_price > 0.0 and line.qty_available > 0.0:
                available_cost = line.cost_price * line.qty_available
                
            line.qty_available_cost = available_cost
    
    def _action_compute_qty(self):
        for line in self:
            qty = 0 
            if line.product_qty>0.0 and line.qty_delivered > 0.0:
                qty = line.product_qty - line.qty_delivered
            line.last_qty = qty
            
    @api.onchange('cost_price')
    def onchange_cost_price(self):
        for line in self:
            if line.product_qty > 0:
                line.cost_total = line.cost_price * line.product_qty
    
    @api.onchange('price_unit')
    def onchange_price_unit(self):
        if self.product_qty > 0:
            self.price_total = self.price_unit * self.product_qty
            
    @api.onchange('product_qty')
    def onchange_product_qty(self):
        
        if not self.product_id:
            return
        
        self.price_total = self.price_unit * self.product_qty
        self.cost_total = self.cost_price * self.product_qty
   
        
    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            return
        # pricelist = self.company_id.base_pricelist_id
        # sale_pricelist = self.company_id.sale_pricelist_id
        
        # # Reset date, price and quantity since _onchange_quantity will provide default values
        # list_price = pricelist._get_product_price(self.product_id , 1, self.project_id.partner_id)
        
        self.price_unit = self.product_id.list_price
        self.change_cost = self.product_id.standard_price
        self.cost_price = self.product_id.standard_price
        self.name = self.product_id.name
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        # 'net_on_hand': obj.with_context({'warehouse': warehouse, 'to_date': end_date}).qty_available
        print( 'qty avail============', self.with_context({'to_date': datetime.today()}).qty_available)
        self.qty_available = self.with_context({'to_date': datetime.today()}).qty_available
       
        self.price_total = self.price_unit * self.product_qty
        self.cost_total = self.cost_price * self.product_qty   

    

