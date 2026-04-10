from odoo import models, fields, api

class ContractDecreeConfiguration(models.Model):
    _name = 'contract.decree.conf'
    _description = 'Contract Decree Configuration'

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    model_id = fields.Many2one('ir.model', string='Model')
    model_char = fields.Char()
    file = fields.Binary(string='File')
    file_name = fields.Char(string="File Name")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    line_ids = fields.One2many('contract.configuration.line', 'contract_conf_id', string='Lines')
    type = fields.Selection([('word', 'Word'), ('pdf', 'PDF')], default='pdf', string='Type')

    @api.model
    def create(self, vals):
        if vals.get('model_char', False):
            model_id = self.env['ir.model'].search([('model', '=', vals['model_char'])], limit=1)
            if model_id and not vals.get('model_id', False):
                vals['model_id'] = model_id.id
        return super(ContractDecreeConfiguration, self).create(vals)

    def action_download_docx(self, res_id=None):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/download/modified_docx/{self.id}/{res_id or 0}',
            'target': 'new',
        }


class ContractConfigurationLine(models.Model):
    _name = 'contract.configuration.line'
    _description = 'Contract Decree Configuration'

    text = fields.Char(string="Replace Text", default='&()&')
    field = fields.Many2one('ir.model.fields', string="Field")
    field2 = fields.Char(string="Second Field")
    field3 = fields.Char(string="Third Field")
    parent_model = fields.Many2one(related='contract_conf_id.model_id')
    contract_conf_id = fields.Many2one('contract.decree.conf', string="Contracts")
