# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleOrderInvoicePaymentTerm(models.TransientModel):
    _name = 'sale.order.invoice.payment.term'
    _description = 'Sale order invoice payment term'
    
    company_id = fields.Many2one('res.company', string='Company')
    so_id = fields.Many2one('sale.order', string='Sale order')
    line_ids = fields.One2many('sale.order.invoice.payment.term.line', 'term_id', string='Invoice list')
    
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(SaleOrderInvoicePaymentTerm, self).default_get(fields_list)
        line_ids = self.env['sale.order'].browse(self.env.context['active_ids'])
        line_data = []
        account_move_obj = self.env['account.move']
        acc_move_id = account_move_obj.search([('invoice_origin','=',line_ids.name),('state','!=','cancel'),('partner_id','=',line_ids.partner_id.id),('company_id','=',line_ids.company_id.id)])
        
        for lines in line_ids.payment_term_id.line_ids:
            if lines.value == 'percent':
                amount = line_ids.amount_total / 100.0 * lines.value_amount
                is_create = False
                invoice_id = False
                for inv in acc_move_id:
                    if inv.amount_total == amount:
                        is_create = True
                        invoice_id = inv.id
                    
                line_data.append((0,0,{
                                        'company_id':line_ids.company_id.id,
                                        'invoice_amount':amount,
                                        'percent':lines.value_amount,
                                        'is_created':is_create,
                                        'desc':lines.desc,
                                        'invoice_id':invoice_id,
                                        }))

        res['company_id'] = line_ids.company_id.id
        res['so_id'] = line_ids.id
        res['line_ids'] = line_data
        return res
    
    
    def action_create_invoice(self):
        
        for line in self:
            tax_id = self.env['account.tax'].search([('type_tax_use','=','sale'),('company_id','=',self.company_id.id),('price_include','=',True)],limit=1)
            pre_amount = 0
            count = 0
            for pr in line.line_ids:
               pre_amount +=pr.invoice_amount
               count +=1
               
            for lines in line.line_ids[:-1]:
               if lines.is_new_create == True:
                    invoice_amount = lines.invoice_amount
                    inv_vals = line.so_id._prepare_invoice()
                    inv_vals.update({
                        "invoice_origin": line.so_id.name,
                        "invoice_line_ids": [
                            (0, 0, {
                                "name": f"{lines.desc} {lines.percent}%",
                                "quantity": 1,
                                "price_unit": invoice_amount,
                                "is_downpayment":True,
                                "tax_ids": [(6, 0, [tax_id.id])],
                            })
                        ]
                    })
                    invoice = self.env["account.move"].create(inv_vals)
                    
            last_percent = line.line_ids[-1].percent
            last_true = line.line_ids[-1].is_new_create
            if last_true == True:
                ratio = last_percent / 100.0
        
                inv_vals = line.so_id._prepare_invoice()
                final_lines = []
                all_amount = 0
                for lined in line.so_id.order_line:
                    all_amount +=lined.price_total
                    scaled_subtotal = lined.price_subtotal
                    unit_price = scaled_subtotal / lined.product_uom_qty if lined.product_uom_qty else 0
                    final_lines.append((0, 0, {
                        "product_id": lined.product_id.id,
                        "name": lined.name,
                        "quantity": lined.product_uom_qty,
                        "price_unit": unit_price,
                        "sale_line_ids":[(6, 0, [line.id])],
                        "tax_ids": [(6, 0, lined.tax_id.ids)],
                    }))
                
                pre_percent = 100 - last_percent
                pre_price = all_amount/100.0*pre_percent
                tax_id = self.env['account.tax'].search([('type_tax_use','=','sale'),('company_id','=',line.company_id.id),('price_include','=',True)],limit=1)
                final_lines.append((0, 0, {
                    "name": 'Урьдчилгаа төлбөр %s'%pre_percent,
                    "quantity": -1,
                    "price_unit": pre_price,
                    "tax_ids": [(6, 0, [tax_id.id])],
                }))
                inv_vals["invoice_origin"] = self.so_id.name
                inv_vals["invoice_line_ids"] = final_lines
        
                final_invoice = self.env["account.move"].create(inv_vals)
                   
                   
        
    
    

class SaleOrderInvoicePaymentTermLine(models.TransientModel):
    _name = 'sale.order.invoice.payment.term.line'
    _description = 'Sale order invoice payment term line'
    
    company_id = fields.Many2one('res.company', string='Company')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_amount = fields.Float(string='Invoice amount')
    percent = fields.Float(string='Percent')
    is_created = fields.Boolean(string='Is created')
    is_new_create = fields.Boolean(string='Is new create')
    desc = fields.Char(string='Description')
    term_id = fields.Many2one('sale.order.invoice.payment.term', string='Payment term')
    
    
    
