# -*- coding: utf-8 -*#
import io
import json
import xlsxwriter
import time
from odoo import fields, models
from odoo.tools import date_utils
from datetime import datetime

class PurchaseExpenseReport(models.TransientModel):
    _name = 'purchase.expense.report'
    _description = 'Purchase expense report'
    
    company_id=fields.Many2one('res.company', string='Company', required=True,
                               default=lambda self: self.env.user.company_id)
    date_from=fields.Date("Start Date", required=True,default=fields.Date.context_today)
    date_to=fields.Date("End Date", required=True,default=fields.Date.context_today)
    product_id = fields.Many2one('product.product', string='Product')
    category_id = fields.Many2one('product.category', string='Category')
    is_detailed = fields.Boolean(string='Detailed Report', default=False)
    show_customs_vat = fields.Boolean(string='Show customs VAT', default=False)
    purchase_type = fields.Selection([('local', 'Local'),
                                        ('foreign' , 'Foreign')], string='Purchase type',
                                        default='local', required=True)

    def _customs_vat_share(self, cost, moves):
        """Landed cost-ийн vendor bill дээрх "НӨАТ-гааль" (өртөгт шингэдэггүй) дүнгээс өгөгдсөн
        move-уудын хувийг бодно. НӨАТ-ын суурь = барааны өртөг + Гаалийн албан татвар тул
        move бүрийн (former_cost + хуваарилагдсан гаалийн албан татвар)-ын харьцаагаар хуваана."""
        bill = cost.vendor_bill_id.sudo()
        if not bill or not moves:
            return 0.0
        vat = sum(bill.invoice_line_ids.filtered(
            lambda l: l.product_id.name == u'НӨАТ-гааль').mapped('balance'))
        if not vat:
            return 0.0
        duty_lines = cost.cost_lines.filtered(lambda l: l.product_id.name == u'Гаалийн албан татвар')
        base = {}
        for adj in cost.valuation_adjustment_lines:
            if adj.move_id not in base:
                base[adj.move_id] = adj.former_cost
            if adj.cost_line_id in duty_lines:
                base[adj.move_id] += adj.additional_landed_cost
        total = sum(base.values())
        return vat * sum(base.get(move, 0.0) for move in moves) / total if total else 0.0

    def _customs_vat_fallback(self, order, value, handled_costs=None):
        """Өртөг шингэх зардал (landed cost) үүсээгүй/батлагдаагүй гаалийн нэхэмжлэхийн НӨАТ-гаалийг
        нэхэмжлэхийн Худалдан авалтуудын (po_ids) барааны үнийн харьцаагаар хуваана."""
        handled_costs = handled_costs or self.env['stock.landed.cost']
        total = 0.0
        bills = self.env['account.move'].sudo().search([
            ('po_ids', 'in', order.id), ('move_type', '=', 'in_invoice'), ('state', '=', 'posted')])
        for bill in bills:
            if bill.landed_costs_ids.filtered(lambda c: c in handled_costs):
                continue  # landed cost-оор нарийн тооцогдсон
            vat = sum(bill.invoice_line_ids.filtered(
                lambda l: l.product_id.name == u'НӨАТ-гааль').mapped('balance'))
            goods = sum(po.amount_untaxed * po.currency_rate for po in bill.po_ids)
            if vat and goods:
                total += vat * value / goods
        return total

    def action_print_xls_report(self):
        data = {
            'company_name': self.company_id.name,
            'company_id': self.company_id.id,
            'start_date': self.date_from,
            'end_date': self.date_to,
            'product_id': self.product_id.id,
            'category_id': self.category_id.id,
            'is_detailed': self.is_detailed,
            'show_customs_vat': self.show_customs_vat,
            'purchase_type':self.purchase_type
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
        title = workbook.add_format({
                                    'align': 'center',
                                    'border': 1,
                                    'bold': True,
                                    'font_size': 12,
                                    'bg_color': '#B22222',
                                    'color': 'white'
                                })
                                

        sheet.set_column(0, 26, 20)
        rowx = 1
        sheet.merge_range("A%s:AC%s"%(rowx,rowx), u'Худалдан авалтын тайлан', title)
        sheet.merge_range("A%s:C%s"%(rowx+1,rowx+1), u'%s'%(data['company_name']), title)
        sheet.merge_range("F%s:AC%s"%(rowx+1,rowx+1), u'Огноо: %s - %s'%(data['start_date'],data['end_date']), title)
        if data['is_detailed'] == True:
            rowx += 3
            sheet.set_column(28, 28, 20)
            sheet.write("A%s"%rowx, u'Захиалгын дугаар', header_txt)
            sheet.write("B%s"%rowx, u"Мөр", header_txt)
            sheet.write("C%s"%rowx, u'Нийлүүлэгч №', header_txt)
            sheet.write("D%s"%rowx, u'Нийлүүлэгч', header_txt)
            sheet.write("E%s"%rowx, u'Барааны бүлэг', header_txt)
            sheet.write("F%s"%rowx, u'Барааны төрөл', header_txt)
            sheet.write("G%s"%rowx, u'Барааны сегмент', header_txt)
            sheet.write("H%s"%rowx, u'Эцсийн хэрэглэгч', header_txt)
            sheet.write("I%s"%rowx, u'Барааны №', header_txt)
            sheet.write("J%s"%rowx, u'Барааны нэр', header_txt)
            sheet.write("K%s"%rowx, u'Тоо', header_txt)
            sheet.write("L%s"%rowx, u'Нэгжийн үнэ', header_txt)
            sheet.write("M%s"%rowx, u'Нийт үнэ', header_txt)
            sheet.write("N%s"%rowx, u'Валют', header_txt)
            sheet.write("O%s"%rowx, u'Ханш', header_txt)
            sheet.write("P%s"%rowx, u'Нийт дүн', header_txt)
            sheet.write("Q%s"%rowx, u'Нэмэлт өртөг', header_txt)
            sheet.write("R%s"%rowx, u'Нийт өртөг', header_txt)
            sheet.write("S%s"%rowx, u'Хүлээн авсан өдөр', header_txt)
            sheet.write("T%s"%rowx, u'Хэрэглэгч', header_txt)
            sheet.write("U%s"%rowx, u'Тээврийн зардал', header_txt)
            sheet.write("V%s"%rowx, u'Гаалийн албан татвар', header_txt)
            sheet.write("W%s"%rowx, u'Мэдүүлгийн хураамж', header_txt)
            sheet.write("X%s"%rowx, u'Бүрдүүлэлтийн хураамж', header_txt)
            sheet.write("Y%s"%rowx, u'Нийт зардал', header_txt)
            sheet.write("Z%s"%rowx, u'Нийт зардал+өртөг', header_txt)
            sheet.write("AA%s"%rowx, u'Тээврийн компани', header_txt)
            sheet.write("AB%s"%rowx, u'Хүргэсэн тоо', header_txt)
            sheet.write("AC%s"%rowx, u'Хүргэгдсэн нийт дүн', header_txt)
            sheet.write("AD%s"%rowx, u'Гаалийн мэдүүлгийн дугаар', header_txt)
            if data.get('show_customs_vat'):
                sheet.write("AE%s"%rowx, u'НӨАТ-гааль', header_txt)
            rowx +=1

            if data['product_id']:
                self._cr.execute("""SELECT
                                        pol.id,
                                        pol.order_id,
                                        po.name,
                                        pol.product_id,
                                        po.partner_id,
                                        po.sales_partner_id,
                                        po.currency_id,
                                        pol.qty_received,
                                        po.user_id,
                                        po.freight_partner_id,
                                        sp.date_done,
                                        pol.price_unit,
                                        po.currency_rate,
                                        po.partner_ref,
                                        sm.product_uom_qty as product_qty,
                                        sp.id as picking_id,
                                        sm.id as move_id
                                    FROM purchase_order po
                                    LEFT JOIN stock_picking sp
                                        ON sp.origin = po.name
                                    LEFT JOIN stock_move as sm
                                        ON sm.picking_id = sp.id
                                    LEFT JOIN purchase_order_line pol
                                        ON pol.id = sm.purchase_line_id
                                    WHERE date(sp.date_done) >= '%s' AND date(sp.date_done) <= '%s'
                                      AND po.company_id = %s
                                      AND pol.product_id = %s
                                      AND po.purchase_type = '%s'
                                      AND po.state IN ('purchase', 'done')
                                      AND sp.state = 'done'
                                      AND pol.qty_received > 0 order by sp.date_done, po.name
                                      """%(data['start_date'],data['end_date'],data['company_id'], data['product_id'],data['purchase_type']))
                purchase_data_ids = self._cr.dictfetchall()
            elif data['category_id']:
                self._cr.execute("""SELECT
                                        pol.id,
                                        pol.order_id,
                                        po.name,
                                        pol.product_id,
                                        po.partner_id,
                                        po.sales_partner_id,
                                        po.currency_id,
                                        pol.qty_received,
                                        po.user_id,
                                        po.freight_partner_id,
                                        sp.date_done,
                                        pol.price_unit,
                                        po.currency_rate,
                                        po.partner_ref,
                                        sm.product_uom_qty as product_qty,
                                        sp.id as picking_id,
                                        sm.id as move_id
                                    FROM purchase_order po
                                    LEFT JOIN stock_picking sp
                                        ON sp.origin = po.name
                                    LEFT JOIN stock_move as sm
                                        ON sm.picking_id = sp.id
                                    LEFT JOIN purchase_order_line pol
                                        ON pol.id = sm.purchase_line_id
                                    LEFT JOIN product_product as pp
                                        ON pp.id = pol.product_id
                                    WHERE date(sp.date_done) >= '%s' AND date(sp.date_done) <= '%s'
                                      AND po.company_id = %s
                                      AND pp.categ_id = %s
                                      AND po.purchase_type = '%s'
                                      AND po.state IN ('purchase', 'done')
                                      AND sp.state = 'done'
                                      AND pol.qty_received > 0 order by sp.date_done, po.name
                                      """%(data['start_date'],data['end_date'],data['company_id'],data['category_id'],data['purchase_type']))
                purchase_data_ids = self._cr.dictfetchall()
            elif not data['product_id'] and not data['category_id']:
                self._cr.execute("""SELECT
                                        pol.id,
                                        pol.order_id,
                                        po.name,
                                        pol.product_id,
                                        po.partner_id,
                                        po.sales_partner_id,
                                        po.currency_id,
                                        pol.qty_received,
                                        po.user_id,
                                        po.freight_partner_id,
                                        sp.date_done,
                                        pol.price_unit,
                                        po.currency_rate,
                                        po.partner_ref,
                                        sm.product_uom_qty as product_qty,
                                        sp.id as picking_id,
                                        sm.id as move_id,
                                        po.currency_rate
                                    FROM purchase_order po
                                    LEFT JOIN stock_picking sp
                                        ON sp.origin = po.name
                                    LEFT JOIN stock_move as sm
                                        ON sm.picking_id = sp.id
                                    LEFT JOIN purchase_order_line pol
                                        ON pol.id = sm.purchase_line_id
                                    WHERE date(sp.date_done) >= '%s' AND date(sp.date_done) <= '%s'
                                      AND po.company_id = %s
                                      AND po.purchase_type = '%s'
                                      AND po.state IN ('purchase', 'done')
                                      AND sp.state = 'done'
                                      AND pol.qty_received > 0 order by sp.date_done, po.name
                                  """%(data['start_date'],data['end_date'],data['company_id'],data['purchase_type']))
                purchase_data_ids = self._cr.dictfetchall()
            
            for purchase_data in purchase_data_ids:
                product = self.env['product.product'].browse(purchase_data['product_id'])
                partner = self.env['res.partner'].browse(purchase_data['partner_id'])
                sales_partner = self.env['res.partner'].browse(purchase_data['sales_partner_id'])
                currency = self.env['res.currency'].browse(purchase_data['currency_id'])
                st_date = datetime.strptime(str(purchase_data['date_done']).split('.')[0],'%Y-%m-%d %H:%M:%S').date()
                currency_rate = self.env['res.currency.rate'].search([('company_id','=',data['company_id']),('currency_id','=',purchase_data['currency_id']),('name','=',str(st_date))])
                curr_rate = currency_rate.inverse_company_rate if currency_rate else purchase_data['currency_rate']
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
                sheet.write("O%s"%rowx, curr_rate, text_right)
                total_amount = total_price * curr_rate
                sheet.write("P%s"%rowx, total_amount, text_right)


                expense_product_ids = self.env['product.product'].search([('landed_cost_ok', '=', True),('type', '=', 'service')])
                additional_costs = {}
                frieght_cost = 0.0
                custom_tax_cost = 0.0
                declaration_cost = 0.0
                clearance_cost = 0.0
                cost_moves = {}
                quantity = 0
                vat_declaration = []
                freight_partner = ''
                for exp_pro in expense_product_ids:
                    self._cr.execute("""select ad.id, COALESCE(ad.additional_landed_cost, 0) as additional_landed_cost,  
                                        ad.product_id, ad.cost_line_id, 
                                        COALESCE(am.vat_declaration, '') as vat_declaration, sm.quantity
                                    from stock_move as sm
                                    left join stock_valuation_adjustment_lines as ad on sm.id = ad.move_id
                                        and ad.cost_id in (select id from stock_landed_cost where state = 'done')
                                    left join stock_landed_cost_lines as sc_lines on ad.cost_line_id = sc_lines.id
                                    left join stock_landed_cost as sc on ad.cost_id = sc.id
                                    left join account_move am on am.id = sc.vendor_bill_id
                                    where sm.purchase_line_id = %s and sm.id = %s
                                """%(purchase_data['id'], purchase_data['move_id']))
                    expense_data_ids = self._cr.dictfetchall()
                    stock_line_obj = self.env['stock.landed.cost.lines'].sudo()
                    for exp in expense_data_ids:
                        quantity = exp['quantity']
                        if exp['vat_declaration'] not in vat_declaration:
                            vat_declaration.append(exp['vat_declaration'])
                        st_line = stock_line_obj.browse(exp['cost_line_id'])
                        if st_line.cost_id:
                            cost_moves[st_line.cost_id] = cost_moves.get(st_line.cost_id, self.env['stock.move']) | self.env['stock.move'].browse(purchase_data['move_id'])

                        if exp_pro.name == u'Тээврийн зардал' and st_line.product_id.id == exp_pro.id:
                            frieght_cost += exp['additional_landed_cost']
                            if st_line.cost_id.vendor_bill_id.partner_id.name !=False:
                                freight_partner += ", " + st_line.cost_id.vendor_bill_id.partner_id.name
                        elif exp_pro.name == u'Гаалийн албан татвар'  and st_line.product_id.id == exp_pro.id:
                            custom_tax_cost += exp['additional_landed_cost']
                        elif exp_pro.name == u'Гаалийн мэдүүлэг'  and st_line.product_id.id == exp_pro.id:
                            declaration_cost += exp['additional_landed_cost']
                        elif exp_pro.name == u'Гаалийн бүрдүүлэлт'  and st_line.product_id.id == exp_pro.id:
                            clearance_cost += exp['additional_landed_cost']
                        #additional_costs['%s'%exp['id']] = exp['additional_landed_cost']
                

                    
                total_cost = frieght_cost + custom_tax_cost + declaration_cost + clearance_cost
                fr_partner = self.env['res.partner'].browse(purchase_data['freight_partner_id'])
                vat_declaration = ', '.join(vat_declaration) if vat_declaration else ''
                sheet.write("Q%s"%rowx,  total_cost, text_right)
                sheet.write("R%s"%rowx,  total_cost+total_amount, text_right)
                sheet.write("S%s"%rowx,  u"%s"%purchase_data['date_done'], text_right)
                sheet.write("T%s"%rowx,  u"%s"%purchase_data['user_id'], text_right)
                sheet.write("U%s"%rowx,  frieght_cost, text_right)
                sheet.write("V%s"%rowx,  custom_tax_cost, text_right)
                sheet.write("W%s"%rowx,  declaration_cost, text_right)
                sheet.write("X%s"%rowx,  clearance_cost, text_right)
                sheet.write("Y%s"%rowx,  total_cost, text_right)
                sheet.write("Z%s"%rowx,  total_cost+total_amount, text_right)
                sheet.write("AA%s"%rowx, u"%s"%freight_partner, text_right)
                sheet.write("AB%s"%rowx, quantity, text_right)
                sheet.write("AC%s"%rowx, purchase_data['price_unit'] * quantity * curr_rate, text_right)
                sheet.write("AD%s"%rowx, vat_declaration, text_right)
                if data.get('show_customs_vat'):
                    sheet.write("AE%s"%rowx, sum(self._customs_vat_share(cost, moves) for cost, moves in cost_moves.items())
                                                  + self._customs_vat_fallback(self.env['purchase.order'].browse(purchase_data['order_id']), purchase_data['product_qty'] * purchase_data['price_unit'] * purchase_data['currency_rate'],
                                                                               self.env['stock.landed.cost'].browse([c.id for c in cost_moves])), text_right)

                
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
            sheet.write("AC%s"%rowx, '', header_txt)
            if data.get('show_customs_vat'):
                sheet.write("AD%s"%rowx, '', header_txt)
                sheet.write("AE%s"%rowx, '=sum(AE2:AE%s)'%(rowx-1), header_txt)

        else:
            rowx += 3
            sheet.write("A%s"%rowx, u'Захиалгын дугаар', header_txt)
            sheet.write("B%s"%rowx, u"Мөр", header_txt)
            sheet.write("C%s"%rowx, u'Нийлүүлэгч №', header_txt)
            sheet.write("D%s"%rowx, u'Нийлүүлэгч', header_txt)
            sheet.write("E%s"%rowx, u'Эцсийн хэрэглэгч', header_txt)
            sheet.write("F%s"%rowx, u'Нийт үнэ', header_txt)
            sheet.write("G%s"%rowx, u'Валют', header_txt)
            sheet.write("H%s"%rowx, u'Ханш', header_txt)
            sheet.write("I%s"%rowx, u'Нийт дүн', header_txt)
            sheet.write("J%s"%rowx, u'Нэмэлт өртөг', header_txt)
            sheet.write("K%s"%rowx, u'Нийт өртөг', header_txt)
            sheet.write("L%s"%rowx, u'Хүлээн авсан өдөр', header_txt)
            sheet.write("M%s"%rowx, u'Хэрэглэгч', header_txt)
            sheet.write("N%s"%rowx, u'Тээврийн зардал', header_txt)
            sheet.write("O%s"%rowx, u'Гаалийн албан татвар', header_txt)
            sheet.write("P%s"%rowx, u'Мэдүүлгийн хураамж', header_txt)
            sheet.write("Q%s"%rowx, u'Бүрдүүлэлтийн хураамж', header_txt)
            sheet.write("R%s"%rowx, u'Нийт зардал', header_txt)
            sheet.write("S%s"%rowx, u'Нийт зардал+өртөг', header_txt)
            sheet.write("T%s"%rowx, u'Тээврийн компани', header_txt)
            if data.get('show_customs_vat'):
                sheet.write("U%s"%rowx, u'НӨАТ-гааль', header_txt)
            rowx +=1
            purchase_orders = self.env['purchase.order'].search([
                ('date_planned', '>=', data['start_date']),
                ('date_planned', '<=', data['end_date']),
                ('state', 'in', ('purchase', 'done')),
                ('company_id', '=', data['company_id']),
                ('purchase_type','=',data['purchase_type'])
            ])
            for purchase_data in purchase_orders:
                product = self.env['product.product'].browse(purchase_data.product_id.id)
                partner = self.env['res.partner'].browse(purchase_data.partner_id.id)
                sales_partner = self.env['res.partner'].browse(purchase_data.sales_partner_id.id)
                currency = self.env['res.currency'].browse(purchase_data.currency_id.id)
                st_date = datetime.strptime(str(purchase_data['date_planned']).split('.')[0], '%Y-%m-%d %H:%M:%S').date()
                currency_rate = self.env['res.currency.rate'].search([('company_id','=',data['company_id']),('currency_id','=',purchase_data.currency_id.id),('name','=',str(st_date))])
                sheet.write("A%s"%rowx, purchase_data.name, text_right)
                sheet.write("B%s"%rowx, purchase_data.id, text_right)
                sheet.write("C%s"%rowx, partner.code or '', text_right)
                sheet.write("D%s"%rowx, partner.name or '', text_right)
                sheet.write("E%s"%rowx, sales_partner.name or '', text_right)
                sheet.write("F%s"%rowx, purchase_data.amount_total, text_right)
                sheet.write("G%s"%rowx, currency.name or '', text_right)
                sheet.write("H%s"%rowx, currency_rate.inverse_company_rate, text_right)
                total_amount = purchase_data.amount_total * currency_rate.inverse_company_rate
                sheet.write("I%s"%rowx, total_amount, text_right)
                expense_product_ids = self.env['product.product'].search([('landed_cost_ok', '=', True),('type', '=', 'service')])
                additional_costs = {}
                frieght_cost = 0.0
                custom_tax_cost = 0.0
                declaration_cost = 0.0
                clearance_cost = 0.0
                cost_moves = {}
                total_cost = 0.0
                freight_partner = ''
                for exp_pro in expense_product_ids:
                    self._cr.execute("""select ad.id, COALESCE(ad.additional_landed_cost, 0) as additional_landed_cost,
                                    ad.product_id, ad.cost_line_id from
                                    stock_valuation_adjustment_lines as ad
                                    left join stock_move sm on sm.id = ad.move_id
                                    left join stock_landed_cost_lines as sc_lines on ad.cost_line_id = sc_lines.id
                                    left join stock_landed_cost as sc on ad.cost_id = sc.id
                                    left join purchase_order_stock_landed_cost_rel as polsc on sc.id = polsc.stock_landed_cost_id
                                    left join purchase_order_line pol on pol.id = sm.purchase_line_id
                                    where polsc.purchase_order_id = %s and pol.order_id = %s
                                      and sc.company_id = %s and sc.state = 'done'
                                    group by ad.id, ad.additional_landed_cost, sc_lines.product_id, ad.product_id, ad.cost_line_id
                                """%(purchase_data.id, purchase_data.id, data['company_id']))
                    expense_data_ids = self._cr.dictfetchall()
                    stock_line_obj = self.env['stock.landed.cost.lines'].sudo()
                    for exp in expense_data_ids:
                        st_line = stock_line_obj.browse(exp['cost_line_id'])
                        if st_line.cost_id:
                            cost_moves[st_line.cost_id] = cost_moves.get(st_line.cost_id, self.env['stock.move']) | self.env['stock.valuation.adjustment.lines'].sudo().browse(exp['id']).move_id
                        if exp_pro.name == u'Тээврийн зардал' and st_line.product_id.id == exp_pro.id:
                            frieght_cost += exp['additional_landed_cost']
                            if st_line.cost_id.vendor_bill_id.partner_id.name !=False:
                                freight_partner += ", " + st_line.cost_id.vendor_bill_id.partner_id.name
                        elif exp_pro.name == u'Гаалийн албан татвар'  and st_line.product_id.id == exp_pro.id:
                            custom_tax_cost += exp['additional_landed_cost']
                        elif exp_pro.name == u'Гаалийн мэдүүлэг'  and st_line.product_id.id == exp_pro.id:
                            declaration_cost += exp['additional_landed_cost']
                        elif exp_pro.name == u'Гаалийн бүрдүүлэлт'  and st_line.product_id.id == exp_pro.id:
                            clearance_cost += exp['additional_landed_cost']
                        #additional_costs['%s'%exp['id']] = exp['additional_landed_cost']
                total_cost = frieght_cost + custom_tax_cost + declaration_cost + clearance_cost
                sheet.write("J%s"%rowx,  total_cost, text_right)
                sheet.write("K%s"%rowx,  total_cost+total_amount, text_right)
                sheet.write("L%s"%rowx,  u"%s"%purchase_data.date_planned, text_right)
                sheet.write("M%s"%rowx,  u"%s"%purchase_data.user_id.name, text_right)
                sheet.write("N%s"%rowx,  frieght_cost, text_right)
                sheet.write("O%s"%rowx,  custom_tax_cost, text_right)
                sheet.write("P%s"%rowx,  declaration_cost, text_right)
                sheet.write("Q%s"%rowx,  clearance_cost, text_right)
                sheet.write("R%s"%rowx,  total_cost, text_right)
                sheet.write("S%s"%rowx,  total_cost+total_amount, text_right)
                sheet.write("T%s"%rowx,  u'%s'%freight_partner, text_right)
                if data.get('show_customs_vat'):
                    # Тухайн захиалгын move-ууд дээрх батлагдсан landed cost-уудыг шууд олно
                    vat_cost_moves = {}
                    for adj in self.env['stock.valuation.adjustment.lines'].sudo().search([
                            ('move_id.purchase_line_id.order_id', '=', purchase_data.id),
                            ('cost_id.state', '=', 'done')]):
                        vat_cost_moves[adj.cost_id] = vat_cost_moves.get(adj.cost_id, self.env['stock.move']) | adj.move_id
                    sheet.write("U%s"%rowx,  sum(self._customs_vat_share(cost, moves) for cost, moves in vat_cost_moves.items())
                                + self._customs_vat_fallback(purchase_data, purchase_data.amount_untaxed * purchase_data.currency_rate,
                                                             self.env['stock.landed.cost'].browse([c.id for c in vat_cost_moves])), text_right)

                
                rowx +=1
            
            #sheet.merge_range("A%s:E%s"%(rowx,rowx), u'Нийт дүн:', header_txt)
            #sheet.write("F%s"%rowx, '=sum(K2:K%s)'%(rowx-1), header_txt)
            #sheet.write("J%s"%rowx, '=sum(L2:L%s)'%(rowx-1), header_txt)
            #sheet.write("M%s"%rowx, '=sum(M2:M%s)'%(rowx-1), header_txt)
            #sheet.write("N%s"%rowx, '', header_txt)
            #sheet.write("O%s"%rowx, '', header_txt)
            #sheet.write("P%s"%rowx, '=sum(P2:P%s)'%(rowx-1), header_txt)
            #sheet.write("Q%s"%rowx, '=sum(Q2:Q%s)'%(rowx-1), header_txt)
            #sheet.write("R%s"%rowx, '=sum(R2:R%s)'%(rowx-1), header_txt)
            #sheet.write("S%s"%rowx, '', header_txt)
            #sheet.write("T%s"%rowx, '', header_txt)
            #sheet.write("U%s"%rowx, '=sum(U2:U%s)'%(rowx-1), header_txt)
            #sheet.write("V%s"%rowx, '=sum(V2:V%s)'%(rowx-1), header_txt)
            #sheet.write("W%s"%rowx, '=sum(W2:W%s)'%(rowx-1), header_txt)
            #sheet.write("X%s"%rowx, '=sum(X2:X%s)'%(rowx-1), header_txt)
            #sheet.write("Y%s"%rowx, '=sum(Y2:Y%s)'%(rowx-1), header_txt)
            #sheet.write("Z%s"%rowx, '=sum(Z2:Z%s)'%(rowx-1), header_txt)
            #sheet.write("AA%s"%rowx, '', header_txt)
            #sheet.write("AB%s"%rowx, '=sum(AB2:AB%s)'%(rowx-1), header_txt)

        rowx += 1
        sheet.write("C%s"%(rowx + 3), u"Хянасан ажилтан: ..................................................../                                            /",)
        sheet.write("C%s"%(rowx + 4), u"Тайлан гаргасан: ..................................................../                                            /",)



        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


