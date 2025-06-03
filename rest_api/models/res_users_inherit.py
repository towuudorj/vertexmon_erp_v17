# -*- coding: utf-8 -*-

import time
import sys
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)
_is_used_simple_token_store = sys.modules.get('odoo.addons.rest_api.controllers.simple_token_store')


class ResUsers(models.Model):
    _inherit = "res.users"
    _description = "Res users"
    
    #location_ids = fields.One2many('location.register','user_id',string='Location')
    
class LocationRegister(models.Model):
    _name = 'location.register'
    _description = "Res users"
    
    latitude = fields.Float(string='Latitude',digits=(10,7))
    longitude = fields.Float(string='Longitude',digits=(10,7))
    user_id = fields.Many2one('res.users',string='User')
    company_id = fields.Many2one('res.company',string='Company', default=lambda self: self.env['res.company']._company_default_get('location.register'))
    
    
    
    