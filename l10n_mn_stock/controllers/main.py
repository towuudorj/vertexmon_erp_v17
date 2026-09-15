# -*- coding: utf-8 -*-
import json
from datetime import datetime
from html import escape

from odoo import http
from odoo.http import request


STATE_LABELS = {
    'draft': u'Ноорог',
    'waiting': u'Хүлээгдэж буй',
    'confirmed': u'Баталгаажсан',
    'partially_available': u'Хэсэгчлэн бэлэн',
    'assigned': u'Бэлэн',
    'done': u'Дууссан',
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="mn">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Барааны урсгалын диаграм</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  html, body { margin:0; padding:0; height:100%; font-family: -apple-system, "Segoe UI", Arial, sans-serif; }
  #header { padding:14px 20px; border-bottom:1px solid #ddd; background:#fafafa; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; }
  #header strong { color:#1F5C73; }
  #legend { font-size:12px; color:#666; display:flex; align-items:center; gap:14px; }
  #legend span { display:inline-flex; align-items:center; gap:6px; }
  #legend i { width:14px; height:3px; display:inline-block; border-radius:2px; }
  #main { position:relative; height:calc(100vh - 56px); }
  #network { width:100%; height:100%; }
  #empty { padding:40px; text-align:center; color:#888; font-size:16px; }
  #detailPanel {
    position:absolute; top:0; right:0; width:520px; max-width:92%; height:100%;
    background:#fff; border-left:1px solid #ddd; box-shadow:-4px 0 12px rgba(0,0,0,.08);
    transform:translateX(100%); transition:transform .18s ease; overflow:auto; z-index:5;
  }
  #detailPanel.open { transform:translateX(0); }
  #detailPanel .dp-head {
    display:flex; align-items:center; justify-content:space-between;
    padding:14px 16px; border-bottom:1px solid #eee; position:sticky; top:0; background:#fff;
  }
  #detailPanel .dp-head strong { color:#1F5C73; font-size:14px; }
  #detailPanel .dp-close { cursor:pointer; border:none; background:none; font-size:18px; color:#888; line-height:1; }
  #detailPanel .dp-close:hover { color:#333; }
  #detailPanel table { width:100%; border-collapse:collapse; font-size:12.5px; }
  #detailPanel th, #detailPanel td { text-align:left; padding:8px 10px; border-bottom:1px solid #f0f0f0; vertical-align:top; }
  #detailPanel th { background:#fafafa; color:#666; font-size:11px; text-transform:uppercase; letter-spacing:.03em; }
  #detailPanel td.num { text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; }
  #detailPanel a { color:#1F5C73; text-decoration:none; }
  #detailPanel a:hover { text-decoration:underline; }
  #detailHint { padding:14px 16px; color:#999; font-size:12.5px; }
  .badge { display:inline-block; font-size:10.5px; padding:2px 6px; border-radius:999px; white-space:nowrap; }
  .badge-done { background:#E3EEE8; color:#1F5C73; }
  .badge-pending { background:#FBF0D9; color:#93691B; }
</style>
</head>
<body>
  <div id="header">
    <div><strong>Барааны урсгалын диаграм</strong> &mdash; __PRODUCT_NAME__ (__DATE_FROM__ &rarr; __DATE_TO__)</div>
    <div id="legend">
      <span><i style="background:#9BB4BC"></i> Дууссан хөдөлгөөн</span>
      <span><i style="background:#D9A62E"></i> Дуусаагүй хөдөлгөөн</span>
    </div>
  </div>
  <div id="main">
    __BODY__
    <div id="detailPanel">
      <div class="dp-head">
        <strong id="dpTitle">Хөдөлгөөний жагсаалт</strong>
        <button class="dp-close" onclick="closeDetail()">&#10005;</button>
      </div>
      <div id="detailHint">Диаграм дээрх зангилаа (агуулах/харилцагч) эсвэл сум дээр дарж холбогдох хөдөлгөөнүүдийг жагсаалтаар харна уу.</div>
      <div id="detailBody"></div>
    </div>
  </div>
  <script>
    var nodes = new vis.DataSet(__NODES_JSON__);
    var edges = new vis.DataSet(__EDGES_JSON__);
    var edgeMoves = __EDGE_MOVES_JSON__;
    var nodeMoves = __NODE_MOVES_JSON__;
    var container = document.getElementById('network');

    function openDetail() { document.getElementById('detailPanel').classList.add('open'); }
    function closeDetail() { document.getElementById('detailPanel').classList.remove('open'); }

    function stateBadge(m) {
      return m.done
        ? '<span class="badge badge-done">' + m.state_label + '</span>'
        : '<span class="badge badge-pending">' + m.state_label + '</span>';
    }

    function renderMoves(moves, showDirection) {
      var rows = moves.map(function(m) {
        var ref = m.picking_id
          ? '<a href="/web#id=' + m.picking_id + '&model=stock.picking&view_type=form" target="_blank">' + m.reference + '</a>'
          : m.reference;
        return '<tr>' +
          '<td>' + m.date + '</td>' +
          '<td>' + ref + '</td>' +
          (showDirection ? '<td>' + m.direction + '</td>' : '') +
          '<td>' + (m.partner || '') + '</td>' +
          '<td>' + (m.responsible || '') + '</td>' +
          '<td class="num">' + m.quantity + '</td>' +
          '<td>' + stateBadge(m) + '</td>' +
          '</tr>';
      }).join('');
      var dirHeader = showDirection ? '<th>Чиглэл</th>' : '';
      document.getElementById('detailBody').innerHTML =
        '<table><thead><tr><th>Огноо</th><th>Баримт</th>' + dirHeader + '<th>Харилцагч</th><th>Хариуцагч</th><th>Тоо</th><th>Төлөв</th></tr></thead>' +
        '<tbody>' + rows + '</tbody></table>';
    }

    function showEdgeDetail(edgeId) {
      var moves = edgeMoves[edgeId] || [];
      document.getElementById('detailHint').style.display = 'none';
      document.getElementById('dpTitle').textContent = 'Хөдөлгөөнүүд (' + moves.length + ')';
      renderMoves(moves, false);
      openDetail();
    }

    function showNodeDetail(nodeId) {
      var moves = nodeMoves[nodeId] || [];
      var node = nodes.get(nodeId);
      document.getElementById('detailHint').style.display = 'none';
      document.getElementById('dpTitle').textContent = (node ? node.label.split('\\n')[0] : 'Зангилаа') + ' (' + moves.length + ')';
      renderMoves(moves, true);
      openDetail();
    }

    if (container) {
      var data = { nodes: nodes, edges: edges };
      var options = {
        layout: { improvedLayout: true },
        physics: {
          stabilization: { iterations: 300 },
          barnesHut: { springLength: 260, springConstant: 0.02, centralGravity: 0.15, avoidOverlap: 1 }
        },
        edges: {
          font: { align: 'top', size: 13, strokeWidth: 4, strokeColor: '#ffffff' },
          arrows: { to: { enabled: true, scaleFactor: 0.7 } },
          width: 2,
          hoverWidth: 1.5,
          selectionWidth: 1.5
        },
        nodes: { shape: 'box', margin: 12, font: { size: 15 } },
        interaction: { hover: true, dragNodes: false }
      };
      var network = new vis.Network(container, data, options);
      network.once('stabilizationIterationsDone', function() {
        network.setOptions({ physics: false });
      });
      network.on('click', function(params) {
        if (params.nodes && params.nodes.length) {
          showNodeDetail(params.nodes[0]);
        } else if (params.edges && params.edges.length) {
          showEdgeDetail(params.edges[0]);
        } else {
          closeDetail();
        }
      });
    }
  </script>
</body>
</html>
"""


class StockWarehouseFlowController(http.Controller):

    @http.route('/l10n_mn_stock/warehouse_flow', type='http', auth='user')
    def warehouse_flow(self, product_id=None, date_from=None, date_to=None,
                        warehouse_ids=None, company_id=None, **kw):
        env = request.env
        product_id = int(product_id) if product_id else False
        company_id = int(company_id) if company_id else env.company.id
        wh_filter_ids = [int(i) for i in warehouse_ids.split(',') if i] if warehouse_ids else []

        # Тайлангийн шинж чанартай тул одоогийн хэрэглэгчийн stock.picking/
        # res.partner г.м моделийн уншиж эрхээс үл хамааран ажиллуулна.
        senv = env.sudo()
        product = senv['product.product'].browse(product_id) if product_id else senv['product.product']

        # 'cancel'-аас бусад бүх төлвийг оруулна: 'done' бус мөр бүрийг
        # "дуусаагүй" гэж үзэж диаграм дээр шар өнгөөр ялгаж харуулна.
        where = ["sm.state != 'cancel'", "sm.company_id = %s"]
        params = [company_id]
        if product_id:
            where.append("sm.product_id = %s")
            params.append(product_id)
        if date_from:
            where.append("sm.date >= %s")
            params.append(date_from + ' 00:00:00')
        if date_to:
            where.append("sm.date <= %s")
            params.append(date_to + ' 23:59:59')

        query = """
            SELECT
                sm.id AS move_id,
                sm.date AS date,
                sm.state AS state,
                sm.reference AS reference,
                sm.picking_id AS picking_id,
                sm.location_id AS location_id,
                sl.usage AS src_usage,
                sl.warehouse_id AS src_warehouse_id,
                sm.location_dest_id AS location_dest_id,
                dest.usage AS dest_usage,
                dest.warehouse_id AS dest_warehouse_id,
                sm.partner_id AS partner_id,
                sm.product_uom_qty AS demand_qty,
                COALESCE(mvl.qty, 0.0) AS quantity
            FROM stock_move sm
            JOIN stock_location sl ON sm.location_id = sl.id
            JOIN stock_location dest ON sm.location_dest_id = dest.id
            LEFT JOIN (
                SELECT move_id, SUM(quantity) AS qty
                FROM stock_move_line
                GROUP BY move_id
            ) mvl ON mvl.move_id = sm.id
            WHERE {where}
            ORDER BY sm.date DESC
        """.format(where=' AND '.join(where))
        request.env.cr.execute(query, tuple(params))
        rows = request.env.cr.dictfetchall()

        warehouse_obj = senv['stock.warehouse']
        partner_obj = senv['res.partner']
        location_obj = senv['stock.location']

        def node_key(usage, warehouse_id, location_id, partner_id):
            if usage in ('internal', 'transit') and warehouse_id:
                return ('wh', warehouse_id)
            if partner_id:
                return ('partner', partner_id)
            return ('loc', location_id)

        node_labels = {}
        edge_qty = {}
        edge_move_rows = {}
        node_move_entries = {}  # node_key -> list of (row, direction)
        partner_ids = set()
        picking_ids = set()
        for r in rows:
            is_done = r['state'] == 'done'
            qty = (r['quantity'] or 0.0) if is_done else (r['demand_qty'] or 0.0)
            if not qty:
                continue
            src_key = node_key(r['src_usage'], r['src_warehouse_id'], r['location_id'], r['partner_id'])
            dest_key = node_key(r['dest_usage'], r['dest_warehouse_id'], r['location_dest_id'], r['partner_id'])
            if src_key == dest_key:
                continue
            if wh_filter_ids:
                wh_ids_in_edge = [k[1] for k in (src_key, dest_key) if k[0] == 'wh']
                if not any(w in wh_filter_ids for w in wh_ids_in_edge):
                    continue

            for key, usage, wid, lid, pid in (
                (src_key, r['src_usage'], r['src_warehouse_id'], r['location_id'], r['partner_id']),
                (dest_key, r['dest_usage'], r['dest_warehouse_id'], r['location_dest_id'], r['partner_id']),
            ):
                if key not in node_labels:
                    if key[0] == 'wh':
                        node_labels[key] = warehouse_obj.browse(wid).name or ('Агуулах %s' % wid)
                    elif key[0] == 'partner':
                        node_labels[key] = partner_obj.browse(pid).name or 'Харилцагч'
                    else:
                        node_labels[key] = location_obj.browse(lid).display_name or 'Байршил'

            edge_key = (src_key, dest_key, is_done)
            edge_qty[edge_key] = edge_qty.get(edge_key, 0.0) + qty
            edge_move_rows.setdefault(edge_key, []).append((r, qty))

            node_move_entries.setdefault(src_key, []).append((r, qty, u'Зарлага'))
            node_move_entries.setdefault(dest_key, []).append((r, qty, u'Орлого'))

            if r['partner_id']:
                partner_ids.add(r['partner_id'])
            if r['picking_id']:
                picking_ids.add(r['picking_id'])

        partners = {p.id: p.name for p in partner_obj.browse(list(partner_ids))}
        picking_records = senv['stock.picking'].browse(list(picking_ids))
        pickings = {p.id: p.name for p in picking_records}
        picking_responsible = {p.id: (p.user_id.name or '') for p in picking_records}

        def build_move_dict(r, qty, direction=None):
            is_done = r['state'] == 'done'
            move = {
                'date': r['date'].strftime('%Y-%m-%d %H:%M') if r['date'] else '',
                'reference': escape(pickings.get(r['picking_id']) or r['reference'] or '-'),
                'picking_id': r['picking_id'] or None,
                'partner': escape(partners.get(r['partner_id']) or ''),
                'responsible': escape(picking_responsible.get(r['picking_id']) or ''),
                'quantity': round(qty, 2),
                'done': is_done,
                'state_label': escape(STATE_LABELS.get(r['state'], r['state'] or '')),
            }
            if direction is not None:
                move['direction'] = direction
            return move

        # Агуулах тус бүрийн Эхлэх огнооны өмнөх бодит эхний үлдэгдэл (зөвхөн
        # 'done' хөдөлгөөнөөр) — сонгосон хугацааны Орлого/Зарлагатай нэмж
        # Эцсийн үлдэгдлийг гаргана. Зөвхөн нэг бараа сонгосон үед л утга учиртай.
        opening_balance = {}
        if product_id and date_from:
            date_from_dt = date_from + ' 00:00:00'
            balance_query = """
                SELECT dest.warehouse_id AS warehouse_id, SUM(mvl.qty) AS qty
                FROM stock_move sm
                JOIN stock_location sl ON sm.location_id = sl.id
                JOIN stock_location dest ON sm.location_dest_id = dest.id
                JOIN (SELECT move_id, SUM(quantity) AS qty FROM stock_move_line GROUP BY move_id) mvl
                    ON mvl.move_id = sm.id
                WHERE sm.state = 'done' AND sm.product_id = %s AND sm.company_id = %s
                  AND sm.date < %s
                  AND sl.usage NOT IN ('internal', 'transit') AND dest.usage IN ('internal', 'transit')
                  AND dest.warehouse_id IS NOT NULL
                GROUP BY dest.warehouse_id
            """
            request.env.cr.execute(balance_query, (product_id, company_id, date_from_dt))
            for row in request.env.cr.dictfetchall():
                opening_balance[row['warehouse_id']] = opening_balance.get(row['warehouse_id'], 0.0) + (row['qty'] or 0.0)

            balance_query_out = """
                SELECT sl.warehouse_id AS warehouse_id, SUM(mvl.qty) AS qty
                FROM stock_move sm
                JOIN stock_location sl ON sm.location_id = sl.id
                JOIN stock_location dest ON sm.location_dest_id = dest.id
                JOIN (SELECT move_id, SUM(quantity) AS qty FROM stock_move_line GROUP BY move_id) mvl
                    ON mvl.move_id = sm.id
                WHERE sm.state = 'done' AND sm.product_id = %s AND sm.company_id = %s
                  AND sm.date < %s
                  AND sl.usage IN ('internal', 'transit') AND dest.usage NOT IN ('internal', 'transit')
                  AND sl.warehouse_id IS NOT NULL
                GROUP BY sl.warehouse_id
            """
            request.env.cr.execute(balance_query_out, (product_id, company_id, date_from_dt))
            for row in request.env.cr.dictfetchall():
                opening_balance[row['warehouse_id']] = opening_balance.get(row['warehouse_id'], 0.0) - (row['qty'] or 0.0)

        # Сонгосон хугацаанд бодитоор ДУУССАН (is_done=True) Орлого/Зарлагыг
        # агуулах тус бүрээр нэгтгэнэ — зангилааны зүүн дээд мөрөнд харуулах
        # "Орсон/Гарсан" болон Эцсийн үлдэгдлийн тооцоо хоёулаа зөвхөн дууссан
        # хөдөлгөөнөөр бодогдоно (дуусаагүй/шар сумыг оруулахгүй).
        period_in = {}
        period_out = {}
        for (src_key, dest_key, is_done), qty in edge_qty.items():
            if not is_done:
                continue
            if dest_key[0] == 'wh':
                period_in[dest_key[1]] = period_in.get(dest_key[1], 0.0) + qty
            if src_key[0] == 'wh':
                period_out[src_key[1]] = period_out.get(src_key[1], 0.0) + qty

        node_ids = {}
        nodes = []
        for idx, (key, label) in enumerate(node_labels.items()):
            node_ids[key] = idx
            display_label = label
            font_overrides = {}
            if key[0] == 'wh':
                font_overrides = {'align': 'left'}
                in_total = period_in.get(key[1], 0.0)
                out_total = period_out.get(key[1], 0.0)
                summary_line = u'Орсон: %s   Гарсан: %s' % (round(in_total, 2), round(out_total, 2))
                if product_id:
                    opening = opening_balance.get(key[1], 0.0)
                    closing = opening + period_in.get(key[1], 0.0) - period_out.get(key[1], 0.0)
                    display_label = '%s\n%s\n(Эхний: %s → Эцсийн: %s)' % (
                        summary_line, label, round(opening, 2), round(closing, 2),
                    )
                else:
                    display_label = '%s\n%s' % (summary_line, label)
            nodes.append({
                'id': idx,
                'label': display_label,
                'shape': 'box',
                'color': {'background': '#1F5C73', 'border': '#123847'} if key[0] == 'wh'
                         else {'background': '#B8862E', 'border': '#8A6420'},
                'font': dict({'color': '#FFFFFF'}, **font_overrides),
            })

        # Хос зангилаа (жишээ нь А→Б, Б→А, эсвэл дууссан/дуусаагүй хос
        # хөдөлгөөн) хоорондын судлуудыг ялгаатай муруйлтаар зурж,
        # шугамууд давхцахаас сэргийлнэ.
        pair_seen = {}
        vis_edges = []
        edge_moves_json = {}
        for eid, ((src_key, dest_key, is_done), qty) in enumerate(edge_qty.items()):
            pair = tuple(sorted((node_ids[src_key], node_ids[dest_key])))
            pair_index = pair_seen.get(pair, 0)
            pair_seen[pair] = pair_index + 1
            roundness = 0.15 + 0.18 * pair_index
            curve_type = 'curvedCW' if node_ids[src_key] <= node_ids[dest_key] else 'curvedCCW'

            edge = {
                'id': eid,
                'from': node_ids[src_key],
                'to': node_ids[dest_key],
                'label': str(round(qty, 2)),
                'smooth': {'type': curve_type, 'roundness': min(roundness, 0.7)},
                'color': {'color': '#9BB4BC', 'highlight': '#1F5C73', 'hover': '#1F5C73'},
            }
            if not is_done:
                edge['color'] = {'color': '#D9A62E', 'highlight': '#93691B', 'hover': '#93691B'}
                edge['dashes'] = True
            vis_edges.append(edge)

            move_list = [
                build_move_dict(r, q)
                for r, q in sorted(edge_move_rows[(src_key, dest_key, is_done)],
                                   key=lambda x: x[0]['date'] or datetime.min, reverse=True)
            ]
            edge_moves_json[eid] = move_list

        node_moves_json = {}
        for key, entries in node_move_entries.items():
            node_id = node_ids.get(key)
            if node_id is None:
                continue
            ordered = sorted(entries, key=lambda x: x[0]['date'] or datetime.min, reverse=True)
            node_moves_json[node_id] = [build_move_dict(r, q, direction) for r, q, direction in ordered]

        if not nodes:
            body = '<div id="empty">Сонгосон шүүлтүүрт тохирох бараа хөдөлгөөн олдсонгүй.</div>'
        else:
            body = '<div id="network"></div>'

        html = (
            HTML_TEMPLATE
            .replace('__PRODUCT_NAME__', escape(product.display_name if product_id else 'Бүх бараа'))
            .replace('__DATE_FROM__', escape(date_from or ''))
            .replace('__DATE_TO__', escape(date_to or ''))
            .replace('__BODY__', body)
            .replace('__NODES_JSON__', json.dumps(nodes))
            .replace('__EDGES_JSON__', json.dumps(vis_edges))
            .replace('__EDGE_MOVES_JSON__', json.dumps(edge_moves_json))
            .replace('__NODE_MOVES_JSON__', json.dumps(node_moves_json))
        )
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])
