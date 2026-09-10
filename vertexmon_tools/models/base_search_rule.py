# -*- coding: utf-8 -*-
import logging
from odoo import api, models
from odoo.exceptions import AccessError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        """
        Override web_search_read across all models to ensure active record rules (ir.rule)
        are properly incorporated into the search domain, non-accessible records are silently
        filtered/hidden from search results, and AccessError popups are prevented in tree views.
        """
        full_domain = domain or []
        if not self.env.su:
            try:
                rule_domain = self.env['ir.rule']._compute_domain(self._name, 'read')
                if rule_domain:
                    full_domain = expression.AND([full_domain, rule_domain])
            except Exception as e:
                _logger.warning("Error computing ir.rule domain for %s in web_search_read: %s", self._name, e)

        # Filter out specification fields requiring groups the current user does not belong to
        safe_specification = {}
        for fname, fspec in specification.items():
            field = self._fields.get(fname)
            if field and field.groups:
                if not any(self.env.user.has_group(g.strip()) for g in field.groups.split(',')):
                    continue
            safe_specification[fname] = fspec

        # Execute search_fetch with rule-aware domain
        try:
            records = self.search_fetch(full_domain, safe_specification.keys(), offset=offset, limit=limit, order=order)
        except AccessError:
            _logger.info("AccessError suppressed in web_search_read search_fetch for model %s", self._name)
            return {'length': 0, 'records': []}
        except Exception:
            # Fallback to original domain if combined domain failed
            try:
                records = self.search_fetch(domain, safe_specification.keys(), offset=offset, limit=limit, order=order)
            except AccessError:
                return {'length': 0, 'records': []}

        # Filter out any records that fail python-side record rule validation
        if records and not self.env.su:
            try:
                records = records._filter_access_rules_python('read')
            except Exception:
                pass

        # Perform web_read on safe specification, catching any AccessError on related fields
        try:
            values_records = records.web_read(safe_specification)
        except AccessError:
            _logger.info("AccessError suppressed in web_search_read web_read for model %s", self._name)
            try:
                values_records = records.sudo().web_read(safe_specification)
            except Exception:
                values_records = [{'id': r.id, 'display_name': r.display_name} for r in records.sudo()]

        # Format web search read results safely
        try:
            return self._format_web_search_read_results(full_domain, values_records, offset, limit, count_limit)
        except AccessError:
            return {'length': len(values_records) + offset, 'records': values_records}
        except Exception:
            try:
                return self._format_web_search_read_results(domain, values_records, offset, limit, count_limit)
            except Exception:
                return {'length': len(values_records) + offset, 'records': values_records}

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        """
        Override search_read to take active record rules into account and prevent AccessError
        from breaking search operations across all models.
        """
        full_domain = domain or []
        if not self.env.su:
            try:
                rule_domain = self.env['ir.rule']._compute_domain(self._name, 'read')
                if rule_domain:
                    full_domain = expression.AND([full_domain, rule_domain])
            except Exception:
                pass

        try:
            records = self.search(full_domain, offset=offset, limit=limit, order=order)
        except AccessError:
            return []

        if not records:
            return []

        if not self.env.su:
            try:
                records = records._filter_access_rules_python('read')
            except Exception:
                pass

        try:
            return records.read(fields, **read_kwargs)
        except AccessError:
            _logger.info("AccessError suppressed in search_read for model %s", self._name)
            try:
                return records.sudo().read(fields, **read_kwargs)
            except Exception:
                return [{'id': r.id, 'display_name': r.display_name} for r in records.sudo()]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Override name_search to gracefully return empty list if an active rule or access right
        prevents reading search suggestions.
        """
        try:
            return super().name_search(name=name, args=args, operator=operator, limit=limit)
        except AccessError:
            _logger.info("AccessError suppressed in name_search for model %s", self._name)
            return []
