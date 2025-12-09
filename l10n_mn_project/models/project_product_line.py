# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from odoo import api, fields, models, SUPERUSER_ID, _



class ProjectProductsLine(models.Model):
    _name = "project.products.line"
    _description = "Project Product Line"
    _order = 'project_id, sequence, id'


    @api.depends('qty_delivered')
    def _compute_qty_delivered(self):   
                           
        for line in self:
            line.qty_delivered = 1
    
    
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
    qty_available = fields.Float(string='Available QTY', required=True, digits='Product', readonly=True, default=0)
    qty_delivered = fields.Float(string='Delivered', compute='_compute_qty_delivered', required=True, digits='Product', readonly=True, default=0)
    price_total = fields.Float(string='Total Price', readonly=True)
    cost_total = fields.Float(string='Total Cost', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company)
    purchase_type = fields.Selection([('local','Local'),
                                    ('foreign','Foreign')],string='Purchase Type',)
    is_task = fields.Boolean(string='Task', default=False)
    is_purchase = fields.Boolean(string='Purchase', default=False)
    purchase_manager_id = fields.Many2one('res.users', string='Purchase Manager')
    last_qty = fields.Float(string='Last qty', compute="_action_compute_qty")
    pur_qty = fields.Float(string='Purchase qty')
    
    def _action_compute_qty(self):
        for line in self:
            qty = 0 
            if line.product_qty>0.0 and line.qty_delivered > 0.0:
                qty = line.product_qty - line.qty_delivered
            line.last_qty = qty
    
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
        self.cost_price = self.product_id.standard_price
        self.name = self.product_id.name
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        # 'net_on_hand': obj.with_context({'warehouse': warehouse, 'to_date': end_date}).qty_available
        print( 'qty avail============', self.with_context({'to_date': datetime.today()}).qty_available)
        self.qty_available = self.with_context({'to_date': datetime.today()}).qty_available
       
        self.price_total = self.price_unit * self.product_qty
        self.cost_total = self.cost_price * self.product_qty   

    

