from odoo import models, fields, api, _

class TrainingFeeOptions(models.Model):
    _name = 'training.fee.options'
    _description = 'Training Fee Option'

    name = fields.Char(string='Training Fee Option')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)