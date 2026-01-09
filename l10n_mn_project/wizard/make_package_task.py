# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import format_date, frozendict


class ProjectPackageTaskLine(models.TransientModel):
    _name = "project.package.task.create.line"
    _rec_name = 'product_id'
    _description = 'Return Picking Line'

    product_id = fields.Many2one('product.product', string="Product", required=True, domain="[('id', '=', product_id)]")
    quantity = fields.Float("Quantity", digits='Product Unit of Measure', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id')
    wizard_id = fields.Many2one('project.package.task.create', string="Wizard")
    pline_id = fields.Many2one('project.products.line', "Product line")
    project_id = fields.Many2one('project.project', "Project")


class ProjectPackageTask(models.TransientModel):
    _name = 'project.package.task.create'

    name = fields.Char(string="Description", required=True)
    date = fields.Date(string="Date", required=True)
    product_lines = fields.One2many('project.package.task.create.line', 'wizard_id', 'Products', readonly=False, store=True)
    task_lines = fields.Many2many('project.package.task.create.line', 'package_task_create_line_rel', 'wizard_id', 'line_id',
                                  string="Products", readonly=False, domain="[('id', 'in', product_lines)]")
    
    


    #### Багц Даалгавар үүсгэх
    def action_create_packege_tasks(self):

        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'project.project':
           
            project = self.env['project.project'].browse(self.env.context.get('active_id'))

        if project:
            vals={
                'project_id': project.id,
                'name':self.name,
                'date_deadline': self.date
            }
            task = self.env['project.task'].create(vals)
        if task:
            for line in self.task_lines:
                line_vals = {
                    'product_id': line.product_id.id,
                    'name': line.pline_id.name,
                    'product_qty':line.quantity,
                    'price_unit': line.pline_id.price_unit,
                    'task_id': task.id,
                }
                self.env['task.products.line'].create(line_vals)
              