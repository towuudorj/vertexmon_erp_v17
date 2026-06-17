# -*- coding: utf-8 -*-

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import format_date, frozendict

from odoo.exceptions import ValidationError


class ProjectInvoice(models.TransientModel):
    _name = "project.invoice"
    _description = 'Project Invoice'

    invoice_amount = fields.Float('Amount')
    project_id = fields.Many2one('project.project', "Project")
    invoiced_amount = fields.Float('Invoiced amount')
    partner_id = fields.Many2one('res.partner', "Partner")
    payment_type = fields.Selection([('down_payment', 'Down payment'),
                                     ('progress_payment', 'Progress payment'),
                                     ('final_payment', 'Final payment'),
                                     ('barter', 'Barter transaction'),
                                     ('guarantee_collateral', 'Guarantee and collateral'),
                                     ('penalty', 'Penalty')],
                                    default=False,
                                    string='Payment type')
    invoice_type = fields.Selection(
        [
            ('out_invoice', 'Out invoice'),
            ('in_invoice', 'In invoice')
        ],
        required=1,
        default='out_invoice')
    line_ids = fields.One2many('project.invoice.line', 'parent_id')

    @api.model
    def default_get(self, fields):
        res = super(ProjectInvoice, self).default_get(fields)
        context = self.env.context
        if context.get('active_model') == 'project.project' and context.get('active_id'):
            project = self.env['project.project'].browse(context['active_id'])
            if 'project_id' in fields and not res.get('project_id'):
                res['project_id'] = project.id
            if 'invoiced_amount' in fields and not res.get('invoiced_amount'):
                analytic_id = str(project.analytic_account_id.id)
                self.env.cr.execute("""
                                    SELECT aml.id
                                    FROM account_move_line aml
                                    LEFT JOIN account_move am on am.id = aml.move_id
                                    WHERE am.move_type = 'out_invoice' and aml.analytic_distribution ? %s
                                    """, [analytic_id])
                aml_ids = [row[0] for row in self.env.cr.fetchall()]
                aml_ids = self.env['account.move.line'].browse(aml_ids)
                invoice_ids = aml_ids.filtered(lambda line: line.move_id.payment_types != 'penalty')
                if invoice_ids:
                    res['invoiced_amount'] = sum(invoice_ids.mapped('price_unit'))
                else:
                    res['invoiced_amount'] = 0
        return res

    def create_invoice(self):
        account_move_obj = self.env['account.move']
        project = self.project_id
        tax_ids = self.env['account.tax'].search(
            [('company_id', '=', project.company_id.id), ('type_tax_use', '=', 'sale'), ('price_include', '=', True)],
            limit=1)
        analytic_account_1 = project.analytic_account_id



        if  self.invoice_type == 'out_invoice':
            if self.invoice_amount + self.invoiced_amount > project.contract_amount:
                raise ValidationError(u'Нийт нэхэмжлэлийн дүн төслийн гэрээний дүнгээс хэтэрж байна')

            invoice_line = {
                'name': u'%s' % project.invoice_product_id.name,
                'quantity': 1.0,
                'product_id': project.invoice_product_id.id,
                'product_uom_id': project.invoice_product_id.uom_id.id,
                'price_unit': self.invoice_amount,
                'tax_ids': [(6, 0, tax_ids.ids)],
                'analytic_distribution': {
                    analytic_account_1.id: 100.0,
                },
                'account_id': project.invoice_journal_id.default_account_id.id,
            }

            invoice_vals = {
                'invoice_date': project.close_date,
                'journal_id': project.invoice_journal_id.id,
                'partner_id': project.partner_id.id,
                'state': 'draft',
                'move_type': 'out_invoice' if self.invoice_type == 'out_invoice' else 'in_invoice',
                'payment_types': self.payment_type,
                'invoice_line_ids': [(0, 0, invoice_line)],
                'company_id': project.company_id.id,
                'invoice_origin': '%s' % project.name
            }
            account_move_obj.create(invoice_vals)
            return None
        else:
            invoice_lines = []
            for line in self.line_ids:
                invoice_lines.append((0, 0,{
                    'name': u'%s' % line.product_id.name,
                    'quantity': 1.0,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_id.uom_id.id,
                    'price_unit': line.amount,
                    'tax_ids': [(6, 0, tax_ids.ids)],
                    'analytic_distribution': {
                        analytic_account_1.id: 100.0,
                    },
                    'account_id': line.product_id.property_account_expense_id.id or False,
                }))

            invoice_vals = {
                'invoice_date': project.close_date,
                'journal_id': project.invoice_journal_id.id,
                'partner_id': self.partner_id.id,
                'state': 'draft',
                'move_type': 'in_invoice',
                'payment_types': self.payment_type,
                'invoice_line_ids': invoice_lines,
                'company_id': project.company_id.id,
                'invoice_origin': '%s' % project.name
            }

            account_move_obj.create(invoice_vals)
            return None


class ProjectInvoiceLine(models.TransientModel):
    _name = "project.invoice.line"
    _description = 'Project Invoice Line'

    product_id = fields.Many2one('product.product', string='Product', domain=[('categ_id.code', '=', 'project')])
    amount = fields.Float('Amount')
    parent_id = fields.Many2one('project.invoice', string='Parent Invoice')