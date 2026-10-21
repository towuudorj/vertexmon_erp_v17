from odoo import models, fields, api
import json
from urllib.parse import urlencode

class ContractDecreeConfiguration(models.Model):
    _name = 'contract.decree.conf'
    _description = 'Contract Decree Configuration'

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    model_id = fields.Many2one('ir.model', string='Model')
    model_char = fields.Char()
    file = fields.Binary(string='File')
    file_name = fields.Char(string="File Name")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    line_ids = fields.One2many('contract.configuration.line', 'contract_conf_id', string='Lines', copy=True)
    type = fields.Selection([('word', 'Word'), ('pdf', 'PDF')], default='pdf', string='Type')

    @api.model
    def get_conf(self, code, company_id=None):
        if not company_id:
            company_id = self.env.company.id
        elif hasattr(company_id, 'id'):
            company_id = company_id.id

        # 1. Search for configuration specific to the company
        conf = self.search([
            ('code', '=', code),
            ('company_id', '=', company_id),
        ], limit=1)

        # 2. If not found, search for global configuration (no company set)
        if not conf:
            conf = self.search([
                ('code', '=', code),
                ('company_id', '=', False),
            ], limit=1)

        # 3. Fallback to any matching configuration
        if not conf:
            conf = self.sudo().search([
                ('code', '=', code),
            ], limit=1)

        return conf

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('model_char') and not vals.get('model_id'):
                model_id = self.env['ir.model'].search([('model', '=', vals['model_char'])], limit=1)
                if model_id:
                    vals['model_id'] = model_id.id
            elif vals.get('model_id') and not vals.get('model_char'):
                model_rec = self.env['ir.model'].browse(vals['model_id'])
                if model_rec:
                    vals['model_char'] = model_rec.model
        return super(ContractDecreeConfiguration, self).create(vals_list)

    def write(self, vals):
        if vals.get('model_id') and not vals.get('model_char'):
            model_rec = self.env['ir.model'].browse(vals['model_id'])
            if model_rec:
                vals['model_char'] = model_rec.model
        return super(ContractDecreeConfiguration, self).write(vals)

    def copy(self, default=None):
        default = dict(default or {})
        if 'company_id' not in default:
            default['company_id'] = self.env.company.id
        return super(ContractDecreeConfiguration, self).copy(default)

    def action_download_docx(self, res_id=None, custom_dict=None, **kwargs):
        if custom_dict is None:
            custom_dict = {}
        else:
            custom_dict = dict(custom_dict)
        if kwargs:
            custom_dict.update(kwargs)

        url = f'/download/modified_docx/{self.id}/{res_id or 0}'
        if custom_dict:
            query = urlencode({'custom_dict': json.dumps(custom_dict, default=str)})
            url = f'{url}?{query}'

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


class ContractConfigurationLine(models.Model):
    _name = 'contract.configuration.line'
    _description = 'Contract Decree Configuration'

    text = fields.Char(string="Replace Text", default='')
    field = fields.Many2one('ir.model.fields', string="Field")
    field2 = fields.Char(string="Second Field")
    field3 = fields.Char(string="Third Field")
    hel = fields.Selection([
        ('mongol', 'Монгол'),
        ('english', 'English'),
    ], string="Хэл", default='mongol')
    bichwer = fields.Selection([
        ('toogoor', 'Тоогоор'),
        ('ugeer', 'Үгээр'),
        ('galig', 'Галиг'),
    ], string="Бичвэр", default='toogoor')
    parent_model = fields.Many2one(related='contract_conf_id.model_id')
    contract_conf_id = fields.Many2one('contract.decree.conf', string="Contracts")
    company_id = fields.Many2one('res.company', string='Company', related='contract_conf_id.company_id', store=True, readonly=True)
