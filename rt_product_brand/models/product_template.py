from odoo import fields, models, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one('product.brand', string='Brand', required=True)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def create(self, vals):
        res = super(ProductProduct, self).create(vals)
        for product in res:
            if product.product_tmpl_id and not product.product_tmpl_id.brand_id:
                default_brand = self.env['product.brand'].search([('code', '=', 'OT'), ('name', '=', 'Other')], limit=1)
                if not default_brand:
                    default_brand = self.env['product.brand'].create({'name': 'Other', 'code': 'OT'})
                product.product_tmpl_id.brand_id = default_brand
            if not product.model:
                product.model = product.name
        return res