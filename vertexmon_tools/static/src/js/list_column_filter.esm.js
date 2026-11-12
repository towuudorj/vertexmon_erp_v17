/* @odoo-module */

/**
 * vertexmon_tools: x2many / list хүснэгтийн толгойн доор багана бүрээр шууд шүүх мөр.
 *
 * Хэрэглээ:  <tree class="o_list_column_filter" ...>
 *
 * Багана бүрт нөхцөл сонгох товч (=, ≠, Эхэлсэн, ≥, ≤, >, <, Агуулсан, Хоосон ...)
 * болон утга оруулах талбар гарна. Шүүлт нь аль хэдийн ачаалагдсан мөрүүд дээр
 * (client талд) хийгдэх ба таарахгүй мөрүүд нуугдаж, "Нийт" дүн зөвхөн харагдаж
 * буй мөрүүдээр бодогдоно.
 */

import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { parseDate, parseDateTime } from "@web/core/l10n/dates";
import { useState, useEffect, useExternalListener } from "@odoo/owl";

const FILTER_CLASS = "o_list_column_filter";
const NUMERIC_TYPES = ["integer", "float", "monetary"];
const DATE_TYPES = ["date", "datetime"];

export const FILTER_OPERATORS = [
    { id: "eq", icon: "=", label: "Тэнцүү" },
    { id: "ne", icon: "≠", label: "Тэнцүү биш" },
    { id: "starts", icon: "a…", label: "Эхэлсэн" },
    { id: "ge", icon: "≥", label: "Их буюу тэнцүү" },
    { id: "le", icon: "≤", label: "Бага буюу тэнцүү" },
    { id: "gt", icon: ">", label: "Их" },
    { id: "lt", icon: "<", label: "Бага" },
    { id: "not_starts", icon: "a̸…", label: "Эхлээгүй" },
    { id: "contains", icon: "[A]", label: "Агуулсан" },
    { id: "not_contains", icon: "[A̸]", label: "Агуулаагүй" },
    { id: "ends", icon: "…a", label: "Төгссөн" },
    { id: "not_ends", icon: "…a̸", label: "Төгсөөгүй" },
    { id: "empty", icon: "∅", label: "Хоосон" },
    { id: "not_empty", icon: "●", label: "Хоосон биш" },
];
const NO_VALUE_OPS = ["empty", "not_empty"];

function normalize(str) {
    return String(str ?? "").toLowerCase().trim();
}

function parseNumber(str) {
    const cleaned = String(str).replace(/[\s,']/g, "");
    if (cleaned === "") {
        return NaN;
    }
    return Number(cleaned);
}

function compare(a, b, op) {
    switch (op) {
        case "eq":
            return a === b;
        case "ne":
            return a !== b;
        case "gt":
            return a > b;
        case "ge":
            return a >= b;
        case "lt":
            return a < b;
        case "le":
            return a <= b;
    }
    return true;
}

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.columnFilterOperators = FILTER_OPERATORS;
        this.columnFilter = useState({ filters: {}, menu: null });
        this._columnFilterTimers = {};
        if (!this.hasColumnFilter) {
            return;
        }
        useEffect(() => this._syncColumnFilterRowNumberCell());
        useExternalListener(window, "mousedown", (ev) => {
            if (this.columnFilter.menu && !ev.target.closest(".o_list_cf_menu, .o_list_cf_op")) {
                this.columnFilter.menu = null;
            }
        });
        useExternalListener(window, "scroll", () => {
            if (this.columnFilter.menu) {
                this.columnFilter.menu = null;
            }
        }, true);
    },

    get hasColumnFilter() {
        const cls = this.props.archInfo?.className || "";
        return cls.split(/\s+/).includes(FILTER_CLASS);
    },

    get columnFilterActive() {
        return Object.values(this.columnFilter.filters).some((f) => this._isFilterUsable(f));
    },

    // ------------------------------------------------------------------
    // Filter state
    // ------------------------------------------------------------------

    _defaultFilterOp(column) {
        const type = this.props.list.fields[column.name]?.type;
        return NUMERIC_TYPES.includes(type) || DATE_TYPES.includes(type) ? "eq" : "contains";
    },

    getColumnFilter(column) {
        return (
            this.columnFilter.filters[column.name] || {
                op: this._defaultFilterOp(column),
                value: "",
            }
        );
    },

    getColumnFilterOperator(column) {
        const op = this.getColumnFilter(column).op;
        return FILTER_OPERATORS.find((o) => o.id === op) || FILTER_OPERATORS[0];
    },

    _isFilterUsable(filter) {
        return filter && (NO_VALUE_OPS.includes(filter.op) || String(filter.value).trim() !== "");
    },

    onColumnFilterInput(column, ev) {
        const value = ev.target.value;
        clearTimeout(this._columnFilterTimers[column.name]);
        this._columnFilterTimers[column.name] = setTimeout(() => {
            this.columnFilter.filters[column.name] = { ...this.getColumnFilter(column), value };
        }, 200);
    },

    onColumnFilterKeydown(column, ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            clearTimeout(this._columnFilterTimers[column.name]);
            this.columnFilter.filters[column.name] = {
                ...this.getColumnFilter(column),
                value: ev.target.value,
            };
        } else if (ev.key === "Escape") {
            ev.target.value = "";
            this.onColumnFilterInput(column, ev);
        }
        ev.stopPropagation();
    },

    toggleColumnFilterMenu(column, ev) {
        if (this.columnFilter.menu?.column === column.name) {
            this.columnFilter.menu = null;
            return;
        }
        const rect = ev.currentTarget.getBoundingClientRect();
        this.columnFilter.menu = {
            column: column.name,
            top: rect.bottom + 2,
            left: rect.left,
        };
    },

    selectColumnFilterOperator(opId) {
        const name = this.columnFilter.menu?.column;
        if (!name) {
            return;
        }
        const column = this.state.columns.find((c) => c.name === name);
        const current = column ? this.getColumnFilter(column) : { value: "" };
        this.columnFilter.filters[name] = { ...current, op: opId };
        this.columnFilter.menu = null;
    },

    clearColumnFilters() {
        this.columnFilter.filters = {};
        this.columnFilter.menu = null;
        const row = this.tableRef?.el?.querySelector(".o_list_cf_row");
        if (row) {
            row.querySelectorAll("input.o_list_cf_input").forEach((input) => (input.value = ""));
        }
    },

    // ------------------------------------------------------------------
    // Matching
    // ------------------------------------------------------------------

    _columnFilterText(record, field, value) {
        switch (field.type) {
            case "many2one":
                if (!value) {
                    return "";
                }
                return Array.isArray(value) ? value[1] || "" : value.display_name || "";
            case "selection": {
                const opt = (field.selection || []).find((o) => o[0] === value);
                return opt ? opt[1] : "";
            }
            case "many2many":
            case "one2many":
                return (value?.records || []).map((r) => r.data.display_name || "").join(", ");
            case "boolean":
                return value ? "1" : "";
            case "date":
            case "datetime": {
                if (!value) {
                    return "";
                }
                const formatter = registry.category("formatters").get(field.type, null);
                return formatter ? formatter(value) : String(value);
            }
            default:
                return value === false || value === null || value === undefined ? "" : String(value);
        }
    },

    _recordMatchesColumnFilter(record, name, filter) {
        const field = this.props.list.fields[name];
        if (!field) {
            return true;
        }
        const raw = record.data[name];
        const op = filter.op;
        const isNumeric = NUMERIC_TYPES.includes(field.type);
        const isDate = DATE_TYPES.includes(field.type);
        const isEmpty = isNumeric ? !raw : this._columnFilterText(record, field, raw) === "";
        if (op === "empty") {
            return isEmpty;
        }
        if (op === "not_empty") {
            return !isEmpty;
        }
        const query = String(filter.value).trim();

        if (["eq", "ne", "gt", "ge", "lt", "le"].includes(op)) {
            if (isNumeric) {
                const num = parseNumber(query);
                if (!isNaN(num)) {
                    return compare(Number(raw) || 0, num, op);
                }
            } else if (isDate && raw) {
                let target = null;
                try {
                    target = field.type === "date" ? parseDate(query) : parseDateTime(query);
                } catch {
                    target = null;
                }
                if (target && target.isValid) {
                    const unit = field.type === "date" ? "day" : "minute";
                    return compare(
                        raw.startOf(unit).toMillis(),
                        target.startOf(unit).toMillis(),
                        op
                    );
                }
            }
            const text = normalize(this._columnFilterText(record, field, raw));
            const q = normalize(query);
            const cmp = text.localeCompare(q, undefined, { sensitivity: "base" });
            return compare(cmp, 0, op);
        }

        let text = this._columnFilterText(record, field, raw);
        let q = query;
        if (isNumeric) {
            // "2,800,000" гэж бичсэн ч 2800000-тай тааруулна
            q = q.replace(/[\s,']/g, "");
            text = raw ? String(raw) : "";
        }
        text = normalize(text);
        q = normalize(q);
        switch (op) {
            case "contains":
                return text.includes(q);
            case "not_contains":
                return !text.includes(q);
            case "starts":
                return text.startsWith(q);
            case "not_starts":
                return !text.startsWith(q);
            case "ends":
                return text.endsWith(q);
            case "not_ends":
                return !text.endsWith(q);
        }
        return true;
    },

    isRecordFilteredOut(record) {
        if (!this.hasColumnFilter || !this.columnFilterActive) {
            return false;
        }
        const visible = new Set(this.state.columns.map((c) => c.name));
        for (const [name, filter] of Object.entries(this.columnFilter.filters)) {
            if (!visible.has(name) || !this._isFilterUsable(filter)) {
                continue;
            }
            if (!this._recordMatchesColumnFilter(record, name, filter)) {
                return true;
            }
        }
        return false;
    },

    get columnFilterCount() {
        const records = this.props.list.records || [];
        const shown = records.filter((r) => !this.isRecordFilteredOut(r)).length;
        return { shown, total: records.length };
    },

    // ------------------------------------------------------------------
    // Rendering hooks
    // ------------------------------------------------------------------

    getRowClass(record) {
        const classes = super.getRowClass(record);
        return this.isRecordFilteredOut(record) ? `${classes} d-none` : classes;
    },

    get aggregates() {
        const list = this.props.list;
        if (!this.hasColumnFilter || !this.columnFilterActive || list.isGrouped ||
            (list.selection && list.selection.length)) {
            return super.aggregates;
        }
        const filtered = list.records.filter((r) => !this.isRecordFilteredOut(r));
        const proxyList = new Proxy(list, {
            get(target, key) {
                return key === "records" ? filtered : Reflect.get(target, key);
            },
        });
        const originalProps = this.props;
        this.props = { ...originalProps, list: proxyList };
        try {
            return super.aggregates;
        } finally {
            this.props = originalProps;
        }
    },

    /**
     * rowno_in_tree модуль толгойн мөрөнд "###" нүдийг DOM-оор нэмдэг тул
     * шүүлтүүрийн мөрөнд ч мөн адил хоосон нүд нэмж баганыг тэгшилнэ.
     */
    _syncColumnFilterRowNumberCell() {
        const table = this.tableRef?.el;
        if (!table) {
            return;
        }
        const filterRow = table.querySelector(":scope > thead > tr.o_list_cf_row");
        if (!filterRow) {
            return;
        }
        const hasRowNo = !!table.querySelector(":scope > thead > tr > th.o_list_row_count_sheliya");
        const cell = filterRow.querySelector(":scope > th.o_list_cf_rowno");
        if (hasRowNo && !cell) {
            const th = document.createElement("th");
            th.className = "o_list_cf_rowno";
            filterRow.prepend(th);
        } else if (!hasRowNo && cell) {
            cell.remove();
        }
    },

    freezeColumnWidths() {
        const res = super.freezeColumnWidths(...arguments);
        if (this.hasColumnFilter) {
            this._syncColumnFilterRowNumberCell();
        }
        return res;
    },
});
