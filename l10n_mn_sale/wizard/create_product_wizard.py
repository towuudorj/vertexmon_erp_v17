# -*- coding: utf-8 -*-

from odoo import api, fields, models

class CreateProductWizard(models.TransientModel):
    _name = 'create.product.wizard'
    _description = 'Create product wizard'

    
    company_id = fields.Many2one(
        string='Company', 
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.user.company_id)
    name = fields.Char(string='Product name')
    uom_id = fields.Many2one('uom.uom', string='Uom')
    model = fields.Char(string='Model', required=True)
    brand_id = fields.Many2one('product.brand', string='Brand')
    categ_id = fields.Many2one('product.category', string='Item group')
    distrubitor_id = fields.Many2one('distributor.register', string='Distributor')
    distributor_ids = fields.Many2one('res.partner', string='Distributor')
    supplier_tax_ids = fields.Many2many('account.tax', string='Supplier Taxes', domain="[('type_tax_use', '=', 'purchase')]")


    @api.model
    def default_get(self, fields_list):
        res = super(CreateProductWizard, self).default_get(fields_list)
        line_ids = self.env['purchase.requisition.line'].browse(self.env.context['active_ids'])
        res['uom_id'] = line_ids.product_uom_id.id
        res['name'] = line_ids.product_description_variants
        return res

    def create_product(self):
        line_ids = self.env['purchase.requisition.line'].browse(self._context.get('active_ids', []))
        for line in line_ids:
            create_product_id = self.env['product.product'].create({
                'name': self.name,
                'uom_id': self.uom_id.id,
                'uom_po_id': self.uom_id.id,
                'brand_id': self.brand_id.id,
                'categ_id': self.categ_id.id,
                'model':self.model,
                'distributor_ids': self.distributor_ids.id,
                'company_id': self.company_id.id,
                'supplier_taxes_id': [(6, 0, self.supplier_tax_ids.ids)],
                'detailed_type': 'product',
            })
            crm_line_id = self.env['crm.lead.line'].search([('id', '=', line.lead_line_id.id)])
            if crm_line_id.lead_id.order_ids:
                for order in crm_line_id.lead_id.order_ids.order_line:
                    if order.crm_lead_line_id.id == crm_line_id.id:
                        order.write({'product_id': create_product_id.id, 'product_uom': self.uom_id.id})
            crm_line_id.write({
                                'product_id': create_product_id.id,
                                'uom_id': self.uom_id.id
                                })
            line.product_id = create_product_id.id



    