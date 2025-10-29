# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CrmTeam(models.Model):
    _inherit = 'crm.team'
    _description = 'Crm team'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    project_id = fields.Many2one('project.project', string='Project')

