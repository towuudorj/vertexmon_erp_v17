# -*- coding: utf-8 -*#
import io
import json
import xlsxwriter
import time
from odoo import fields, models
from odoo.tools import date_utils


class PurchaseExpenseReport(models.TransientModel):
    _name = 'purchase.expense.report'
    _description = 'Purchase expense report'
    
    company_id=fields.Many2one('res.company', string='Company', required=True,
                               default=lambda self: self.env.user.company_id)
    date_from=fields.Date("Start Date", required=True,default=fields.Date.context_today)
    date_to=fields.Date("End Date", required=True,default=fields.Date.context_today)
    product_id = fields.Many2one('product.product', string='Product')
    category_id = fields.Many2one('product.category', string='Category')

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.date_from,
            'end_date': self.date_to,
            'product_id': self.product_id.id,
            'category_id': self.category_id.id,
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': {'model': 'purchase.expense.report',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=date_utils.json_default),
                     'report_name': 'Profit excel report'}
        }

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        header = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': 16,
                                    })
        
        header_txt = workbook.add_format({
                                    'align': 'center', 
                                    'bold': True, 
                                    'font_size': 12,
                                    'border': 1,
                                    'text_wrap': True,
                                    })
        
        text_right = workbook.add_format({
                                    'align': 'right', 
                                    'font_size': 12,
                                    'border': 1,
                                    'text_wrap': True,
                                    'num_format': '#,##0.00; (#,##0.00)'
                                    })
                                

        sheet.set_column(0, 26, 20)

        sheet.write("A1", u'Захиалгын дугаар', header_txt)
        sheet.write("B1", u"Мөр", header_txt)
        sheet.write("C1", u'Нийлүүлэгч №', header_txt)
        sheet.write("D1", u'Нийлүүлэгч', header_txt)
        sheet.write("E1", u'Барааны бүлэг', header_txt)
        sheet.write("F1", u'Барааны төрөл', header_txt)
        sheet.write("G1", u'Барааны сегмент', header_txt)
        sheet.write("H1", u'Эцсийн хэрэглэгч', header_txt)
        sheet.write("I1", u'Барааны №', header_txt)
        sheet.write("J1", u'Барааны нэр', header_txt)
        sheet.write("K1", u'Тоо', header_txt)
        sheet.write("L1", u'Нэгжийн үнэ', header_txt)
        sheet.write("M1", u'Нийт үнэ', header_txt)
        sheet.write("N1", u'Валют', header_txt)
        sheet.write("O1", u'Ханш', header_txt)
        sheet.write("P1", u'Нийт дүн', header_txt)
        sheet.write("Q1", u'Нэмэлт өртөг', header_txt)
        sheet.write("R1", u'Нийт өртөг', header_txt)
        sheet.write("S1", u'Хүлээн авсан өдөр', header_txt)
        sheet.write("T1", u'Хэрэглэгч', header_txt)
        sheet.write("U1", u'Тээврийн зардал', header_txt)
        sheet.write("V1", u'Гаалийн албан татвар', header_txt)
        sheet.write("W1", u'Мэдүүлгийн хураамж', header_txt)
        sheet.write("X1", u'Бүрдүүлэлтийн хураамж', header_txt)
        sheet.write("Y1", u'Нийт зардал', header_txt)
        sheet.write("Z1", u'Нийт зардал+өртөг', header_txt)
        sheet.write("AA1", u'Тээврийн компани', header_txt)
        sheet.write("AB1", u'Хүргэсэн тоо', header_txt)
        

        purchase_orders = self.env['purchase.order'].search([
            ('date_order', '>=', data['start_date']),
            ('date_order', '<=', data['end_date']),
            ('state', 'in', ['purchase', 'done']),
            ('company_id', '=', self.company_id.id)
        ])

        if data['product_id']:
            self._cr.execute("""select pol.id, pol.order_id, po.name, pol.product_id, po.partner_id, po.sales_partner_id, po.currency_id,
                            pol.qty_received, po.user_id, pol.date_planned, pol.price_unit, po.currency_rate, po.partner_ref,pol.product_qty
                            from purchase_order as po left join purchase_order_line as pol on pol.order_id = po.id
                            where po.date_order >= '%s' and po.date_order <= '%s' and po.company_id = %s
                            and po.state in ('purchase', 'done') and pol.qty_received > 0 and 
                            pol.product_id = %s
                            group by pol.id, pol.order_id, po.user_id, po.partner_ref, pol.price_unit, po.currency_rate, pol.product_qty,po.name, pol.product_id, po.partner_id, po.sales_partner_id, po.currency_id, pol.qty_received
                            """%(data['start_date'],data['end_date'],data['company_id'], data['product_id']))
            purchase_data_ids = self._cr.dictfetchall()
        elif data['category_id']:
            self._cr.execute("""select pol.id, pol.order_id, po.name, pol.product_id, po.partner_id, po.sales_partner_id, po.currency_id,
                            pol.qty_received, po.user_id, pol.date_planned, pol.price_unit, po.currency_rate, po.partner_ref,pol.product_qty
                            from purchase_order as po left join purchase_order_line as pol on pol.order_id = po.id
                            left join product_product as pp on pol.product_id = pp.id
                            where po.date_order >= '%s' and po.date_order <= '%s' and po.company_id = %s
                            and po.state in ('purchase', 'done') and pol.qty_received > 0
                            and pp.categ_id = %s
                            group by pol.id, pol.order_id,  po.user_id, po.partner_ref, pol.price_unit,pol.product_qty, po.currency_rate, po.name, pol.product_id, po.partner_id, po.sales_partner_id, po.currency_id, pol.qty_received
                            """%(data['start_date'],data['end_date'],data['company_id'],data['category_id']))
            purchase_data_ids = self._cr.dictfetchall()
        elif not data['product_id'] and not data['category_id']:
            self._cr.execute("""select pol.id, pol.order_id, po.name, pol.product_id, po.partner_id, po.sales_partner_id, po.currency_id,
                            pol.qty_received, po.user_id, pol.date_planned, pol.price_unit, po.currency_rate, po.partner_ref,pol.product_qty
                            from purchase_order as po left join purchase_order_line as pol on pol.order_id = po.id
                            where po.date_order >= '%s' and po.date_order <= '%s' and po.company_id = %s
                            and po.state in ('purchase', 'done') and pol.qty_received > 0
                            group by pol.id, pol.order_id, po.user_id, po.partner_ref, pol.price_unit,pol.product_qty, po.currency_rate, po.name, pol.product_id, po.partner_id, po.sales_partner_id, po.currency_id, pol.qty_received
                            """%(data['start_date'],data['end_date'],data['company_id']))
            purchase_data_ids = self._cr.dictfetchall()
        rowx = 2
        for purchase_data in purchase_data_ids:
            product = self.env['product.product'].browse(purchase_data['product_id'])
            partner = self.env['res.partner'].browse(purchase_data['partner_id'])
            sales_partner = self.env['res.partner'].browse(purchase_data['sales_partner_id'])
            currency = self.env['res.currency'].browse(purchase_data['currency_id'])
            sheet.write("A%s"%rowx, purchase_data['name'], text_right)
            sheet.write("B%s"%rowx, purchase_data['id'], text_right)
            sheet.write("C%s"%rowx, partner.code or '', text_right)
            sheet.write("D%s"%rowx, partner.name or '', text_right)
            sheet.write("E%s"%rowx, product.categ_id.name or '', text_right)
            sheet.write("F%s"%rowx, product.brand_id.name or '', text_right)
            sheet.write("G%s"%rowx, product.categ_id.name or '', text_right)
            sheet.write("H%s"%rowx, sales_partner.name or '', text_right)
            sheet.write("I%s"%rowx, product.default_code or '', text_right)
            sheet.write("J%s"%rowx, product.name or '', text_right)
            sheet.write("K%s"%rowx, purchase_data['product_qty'], text_right)
            sheet.write("L%s"%rowx, purchase_data['price_unit'], text_right)
            total_price = purchase_data['product_qty'] * purchase_data['price_unit']
            sheet.write("M%s"%rowx, total_price, text_right)
            sheet.write("N%s"%rowx, currency.name or '', text_right)
            sheet.write("O%s"%rowx, purchase_data['currency_rate'], text_right)
            total_amount = total_price * purchase_data['currency_rate']
            sheet.write("P%s"%rowx, total_amount, text_right)


            expense_product_ids = self.env['product.product'].search([('landed_cost_ok', '=', True),('type', '=', 'service')])
            additional_costs = {}
            frieght_cost = 0.0
            custom_tax_cost = 0.0
            declaration_cost = 0.0
            clearance_cost = 0.0
            total_cost = 0.0
            for exp_pro in expense_product_ids:
                self._cr.execute("""select ad.id, ad.additional_landed_cost,  ad.product_id, ad.cost_line_id from 
                                stock_valuation_adjustment_lines as ad
                                left join stock_landed_cost_lines as sc_lines on ad.additional_landed_cost = sc_lines.id
                                left join stock_landed_cost as sc on ad.cost_id = sc.id
                                left join purchase_order_stock_landed_cost_rel as polsc on sc.id = polsc.stock_landed_cost_id
                                where polsc.purchase_order_id = %s and ad.product_id = %s and sc.company_id = %s
                                group by ad.id, ad.additional_landed_cost, sc_lines.product_id, ad.product_id, ad.cost_line_id
                            """%(purchase_data['order_id'], product.id, data['company_id']))
                expense_data_ids = self._cr.dictfetchall()
                stock_line_obj = self.env['stock.landed.cost.lines']
                for exp in expense_data_ids:
                    st_line = stock_line_obj.browse(exp['cost_line_id'])
                    if exp_pro.name == u'Тээврийн зардал' and st_line.product_id.id == exp_pro.id:
                        frieght_cost += exp['additional_landed_cost']
                    elif exp_pro.name == u'Гаалийн албан татвар'  and st_line.product_id.id == exp_pro.id:
                        custom_tax_cost += exp['additional_landed_cost']
                    elif exp_pro.name == u'Гаалийн мэдүүлэг'  and st_line.product_id.id == exp_pro.id:
                        declaration_cost += exp['additional_landed_cost']
                    elif exp_pro.name == u'Гаалийн бүрдүүлэлт'  and st_line.product_id.id == exp_pro.id:
                        clearance_cost += exp['additional_landed_cost']
                    #additional_costs['%s'%exp['id']] = exp['additional_landed_cost']
            total_cost = frieght_cost + custom_tax_cost + declaration_cost + clearance_cost
            sheet.write("Q%s"%rowx,  total_cost, text_right)
            sheet.write("R%s"%rowx,  total_cost+total_amount, text_right)
            sheet.write("S%s"%rowx,  u"%s"%purchase_data['date_planned'], text_right)
            sheet.write("T%s"%rowx,  u"%s"%purchase_data['user_id'], text_right)
            sheet.write("U%s"%rowx,  frieght_cost, text_right)
            sheet.write("V%s"%rowx,  custom_tax_cost, text_right)
            sheet.write("W%s"%rowx,  declaration_cost, text_right)
            sheet.write("X%s"%rowx,  clearance_cost, text_right)
            sheet.write("Y%s"%rowx,  total_cost, text_right)
            sheet.write("Z%s"%rowx,  total_cost+total_amount, text_right)
            sheet.write("AA%s"%rowx, '', text_right)
            sheet.write("AB%s"%rowx, purchase_data['qty_received'], text_right)

            
            rowx +=1
        
        sheet.merge_range("A%s:J%s"%(rowx,rowx), u'Нийт дүн:', header_txt)
        sheet.write("K%s"%rowx, '=sum(K2:K%s)'%(rowx-1), header_txt)
        sheet.write("L%s"%rowx, '=sum(L2:L%s)'%(rowx-1), header_txt)
        sheet.write("M%s"%rowx, '=sum(M2:M%s)'%(rowx-1), header_txt)
        sheet.write("N%s"%rowx, '', header_txt)
        sheet.write("O%s"%rowx, '', header_txt)
        sheet.write("P%s"%rowx, '=sum(P2:P%s)'%(rowx-1), header_txt)
        sheet.write("Q%s"%rowx, '=sum(Q2:Q%s)'%(rowx-1), header_txt)
        sheet.write("R%s"%rowx, '=sum(R2:R%s)'%(rowx-1), header_txt)
        sheet.write("S%s"%rowx, '', header_txt)
        sheet.write("T%s"%rowx, '', header_txt)
        sheet.write("U%s"%rowx, '=sum(U2:U%s)'%(rowx-1), header_txt)
        sheet.write("V%s"%rowx, '=sum(V2:V%s)'%(rowx-1), header_txt)
        sheet.write("W%s"%rowx, '=sum(W2:W%s)'%(rowx-1), header_txt)
        sheet.write("X%s"%rowx, '=sum(X2:X%s)'%(rowx-1), header_txt)
        sheet.write("Y%s"%rowx, '=sum(Y2:Y%s)'%(rowx-1), header_txt)
        sheet.write("Z%s"%rowx, '=sum(Z2:Z%s)'%(rowx-1), header_txt)
        sheet.write("AA%s"%rowx, '', header_txt)
        sheet.write("AB%s"%rowx, '=sum(AB2:AB%s)'%(rowx-1), header_txt)


        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


