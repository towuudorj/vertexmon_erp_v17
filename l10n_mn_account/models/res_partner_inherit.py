# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResPartner(models.Model):
     _inherit = 'res.partner'


     @api.model
     def _get_partner_type(self):
         return self.env['partner.type.register'].search([], limit=1)


     code = fields.Char(string='Code', readonly=True, copy=False,
                        default=lambda self:self.env['ir.sequence'].next_by_code('res.partner'))
     partner_type = fields.Many2one('partner.type.register', string='Partner type')
     vat = fields.Char(string='Tax ID', index=True, help="The Tax Identification Number. Values here will be validated based on the country format. You can use '/' to indicate that the partner is not subject to tax.")
     group_company_id = fields.Many2one('res.partner', string='Parent company')
     is_distributor = fields.Boolean(string='Is distributor')
     partner_group = fields.Selection([('001','001 Sales'),
                                       ('002','002 Employee'),
                                       ('003','003 Bank'),
                                       ('004','004 State'),
                                       ('005','005 Freight'),
                                       ('006','006 Supplier foreign'),
                                       ('007','007 Supplier local'),
                                       ('008','008 Marketing'),
                                       ('008','009 Relation'),
                                       ('010','010 Self'),
                                       ('011','011 Contract partner')], string='Partner group', default='001', required=True)
     
     _sql_constraints = [
        ('unique_vat', 'unique(vat)', 'This vat is already assigned to another contact. Please make sure you assign a unique vat to this contact.'),
    ]

     

     @api.onchange('partner_group')
     def _onchange_partner_group(self):
        for line in self:
            partner_type_id = self.env['partner.type.register'].search([('partner_group', '=', line.partner_group)], limit=1)
            line.partner_type = partner_type_id.id



     @api.onchange('partner_type')
     def _onchange_partner_type(self):
        for line in self:
            if line.partner_type:
               line.property_account_receivable_id = line.partner_type.payable_account_id.id
               line.property_account_payable_id = line.partner_type.receivable_account_id.id 

     
     