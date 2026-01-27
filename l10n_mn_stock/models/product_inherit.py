# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools.misc import unique
    
    
    
class ProductProduct(models.Model):
    _inherit= 'product.product'

    distributor_id = fields.Many2one('distributor.register', string='Distributer', related="product_tmpl_id.distributor_id")
    distributor_ids = fields.Many2one('res.partner', string='Distributer', domain=[("is_distributor","=",True)])
    model = fields.Char(string='Model', related="product_tmpl_id.model", related_sudo=False, readonly=False)
    default_code = fields.Char('Internal Reference', related="product_tmpl_id.default_code")
    is_quotation = fields.Boolean(string='Is quotation', related="product_tmpl_id.is_quotation")
    ot_code = fields.Char(string='OT code', related="product_tmpl_id.ot_code")


    @api.depends('name', 'default_code', 'product_tmpl_id')
    @api.depends_context('display_default_code', 'seller_id', 'company_id', 'partner_id')
    def _compute_display_name(self):
        def get_display_name(name, code):
            if self._context.get('display_default_code', True) and code:
                return f'{name}[{code}] '
            return name

        partner_id = self._context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []
        company_id = self.env.context.get('company_id')

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights("read")
        self.check_access_rule("read")

        product_template_ids = self.sudo().product_tmpl_id.ids

        if partner_ids:
            # prefetch the fields used by the `display_name`
            supplier_info = self.env['product.supplierinfo'].sudo().search_fetch(
                [('product_tmpl_id', 'in', product_template_ids), ('partner_id', 'in', partner_ids)],
                ['product_tmpl_id', 'product_id', 'company_id', 'product_name', 'product_code'],
            )
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id, []).append(r)

        for product in self.sudo():
            variant = product.product_template_attribute_value_ids._get_combination_name()

            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = self.env['product.supplierinfo'].sudo().browse(self.env.context.get('seller_id')) or []
            if not sellers and partner_ids:
                product_supplier_info = supplier_info_by_template.get(product.product_tmpl_id, [])
                sellers = [x for x in product_supplier_info if x.product_id and x.product_id == product]
                if not sellers:
                    sellers = [x for x in product_supplier_info if not x.product_id]
                # Filter out sellers based on the company. This is done afterwards for a better
                # code readability. At this point, only a few sellers should remain, so it should
                # not be a performance issue.
                if company_id:
                    sellers = [x for x in sellers if x.company_id.id in [company_id, False]]
            if sellers:
                temp = []
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    temp.append(get_display_name(seller_variant or name, s.product_code or product.default_code))

                # => Feature drop here, one record can only have one display_name now, instead separate with `,`
                # Remove this comment
                product.display_name = ", ".join(unique(temp))
            else:
                product.display_name = get_display_name(name, product.default_code)

class ProductTemplate(models.Model):
    _inherit= 'product.template'


    @tools.ormcache()
    def _get_default_category_id(self):
        # Deletion forbidden (at least through unlink)
        return self.env.ref('product.product_category_all')

    model = fields.Char(string='Model',required=True)
    distributor_ids = fields.Many2one('res.partner', string='Distributer', domain=[("is_distributor","=",True)])
    distributor_id = fields.Many2one('distributor.register', string='Distributer')
    default_code = fields.Char('Internal Reference', index=True, compute='_compute_default_code', store=True)
    product_categ_id = fields.Many2one('product.category.new', string='Product Category')
    is_quotation = fields.Boolean(string='Is quotation', default=False)
    ot_code = fields.Char(string='OT code')
    categ_id = fields.Many2one(
        'product.category', string='Item group',
        change_default=True, default=_get_default_category_id, group_expand='_read_group_categ_id',
        required=True)

    _sql_constraints = [
        ('unique_model_company_id', 'unique(model)', 'Model must be unique!'),
    ]

    @api.depends('name', 'default_code')
    def _compute_display_name(self):
        for template in self:
            template.display_name = '{} {}'.format(template.name, template.default_code and '[%s] ' % template.default_code or '')

    def _compute_default_code(self):
        for record in self:
            if record.brand_id:
                pre_code = str(record.id)
                if pre_code !=False:
                    if len(pre_code) > 0:
                        if len(pre_code) == 1:
                            record.default_code = record.brand_id.code + '' + str(int(pre_code)).zfill(7)
                        elif len(pre_code) == 2:
                            record.default_code = record.brand_id.code + '' + str(int(pre_code)).zfill(7)
                        elif len(pre_code) == 3:
                            record.default_code = record.brand_id.code + '' + str(int(pre_code)).zfill(7)
                        elif len(pre_code) == 4:
                            record.default_code = record.brand_id.code + '' + str(int(pre_code)).zfill(7)
                        elif len(pre_code) == 5:
                            record.default_code = record.brand_id.code + '' + str(int(pre_code) ).zfill(7)
                        elif len(pre_code) == 6:
                            record.default_code = record.brand_id.code + '' + str(int(pre_code) ).zfill(7)
                        elif len(pre_code) == 7:
                            record.default_code = record.brand_id.code + '' + str(int(pre_code) ).zfill(7)
                    else:
                        record.default_code = record.brand_id.code + '0000001'
                else:
                    record.default_code = record.brand_id.code + '0000001'
            else:
                UserError(_('Please select brand first!'))
