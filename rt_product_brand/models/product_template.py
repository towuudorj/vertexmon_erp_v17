from odoo import fields, models, api, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one('product.brand', string='Brand')
    
    @api.model
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        for product in res:
            #if product.brand_id.is_barcode_required == True and product.barcode == False:
                
            #    raise UserError(_("Заавал баркод талбарыг бөглөнө үү.2"))
            if product and not product.brand_id:
                default_brand = self.env['product.brand'].search([('code', '=', 'OT'), ('name', '=', 'Other')], limit=1)
                if not default_brand:
                    default_brand = self.env['product.brand'].create({'name': 'Other', 'code': 'OT'})
                product.brand_id = default_brand
            if not product.model:
                product.model = product.name
            
        return res
    

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