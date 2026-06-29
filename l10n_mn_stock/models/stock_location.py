from odoo import models, fields


class Location(models.Model):
    _inherit = 'stock.location'

    supply_location = fields.Boolean('Is supply', default=False)