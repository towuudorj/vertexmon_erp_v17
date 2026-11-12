/* @odoo-module */

/**
 * vertexmon_tools: list / x2many хүснэгтийн толгойн доор багана бүрээр шууд шүүх мөр
 * (Infor LN-ийн шүүлтүүрийн мөртэй адил).
 *
 * Хэрэглээ:  <tree class="o_list_column_filter" ...>
 *            эсвэл өв залгамжлалаар:
 *            <xpath expr="//tree" position="attributes">
 *                <attribute name="class" add="o_list_column_filter" separator=" "/>
 *            </xpath>
 *
 * - Үндсэн жагсаалт (хуудаслагдсан list view): шүүлтүүр domain болж server талд
 *   хайгдана — бүх бичлэгээс хайж, pager/нийт дүн/бүлэглэлт шүүгдсэн өгөгдлөөр гарна.
 *   Хайлтын самбарын (search bar) шүүлтүүртэй AND-аар нийлнэ.
 * - x2many (маягт доторх хүснэгт): ачаалагдсан мөрүүд дээр client талд шүүж,
 *   таарахгүй мөрүүдийг нууна; "Нийт" дүн харагдаж буй мөрүүдээр бодогдоно.
 */

import { ListRenderer } from "@web/views/list/list_renderer";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { Domain } from "@web/core/domain";
import {
    parseDate,
    parseDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { useState, useEffect, useExternalListener, onWillUnmount } from "@odoo/owl";

const FILTER_CLASS = "o_list_column_filter";
const NUMERIC_TYPES = ["integer", "float", "monetary"];
const DATE_TYPES = ["date", "datetime"];
const TEXT_TYPES = ["char", "text", "html"];
const RELATIONAL_TYPES = ["many2one", "many2many", "one2many"];

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
const COMPARE_OPS = ["eq", "ne", "gt", "ge", "lt", "le"];
const TEXT_OPS = ["starts", "not_starts", "contains", "not_contains", "ends", "not_ends"];

const OPS_BY_KIND = {
    numeric: ["eq", "ne", "ge", "le", "gt", "lt", "empty", "not_empty"],
    date: ["eq", "ne", "ge", "le", "gt", "lt", "empty", "not_empty"],
    boolean: ["eq", "ne"],
    relational: ["eq", "ne", "starts", "not_starts", "contains", "not_contains", "ends", "not_ends", "empty", "not_empty"],
    text: FILTER_OPERATORS.map((o) => o.id),
};

function fieldKind(field) {
    const type = field?.type;
    if (NUMERIC_TYPES.includes(type)) {
        return "numeric";
    }
    if (DATE_TYPES.includes(type)) {
        return "date";
    }
    if (type === "boolean") {
        return "boolean";
    }
    if (RELATIONAL_TYPES.includes(type)) {
        return "relational";
    }
    return "text";
}

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

function parseBoolean(str) {
    return /^(1|true|yes|y|тийм|т|үнэн)$/i.test(String(str).trim());
}

function parseDateInput(field, str) {
    let value = null;
    try {
        value = field.type === "date" ? parseDate(str) : parseDateTime(str);
    } catch {
        value = null;
    }
    return value && value.isValid ? value : null;
}

function escapeLike(str) {
    return str.replace(/\\/g, "\\\\").replace(/%/g, "\\%").replace(/_/g, "\\_");
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

function textMatch(text, query, op) {
    const t = normalize(text);
    const q = normalize(query);
    switch (op) {
        case "contains":
            return t.includes(q);
        case "not_contains":
            return !t.includes(q);
        case "starts":
            return t.startsWith(q);
        case "not_starts":
            return !t.startsWith(q);
        case "ends":
            return t.endsWith(q);
        case "not_ends":
            return !t.endsWith(q);
        case "empty":
            return t === "";
        case "not_empty":
            return t !== "";
    }
    if (COMPARE_OPS.includes(op)) {
        return compare(t.localeCompare(q, undefined, { sensitivity: "base" }), 0, op);
    }
    return true;
}

// ---------------------------------------------------------------------------
// Model: шүүлтүүрийн domain-ийг хайлтын domain-тэй үргэлж AND хийнэ
// ---------------------------------------------------------------------------

patch(RelationalModel.prototype, {
    async load(params = {}) {
        if (this._cfDomain && this._cfDomain.length && this.config && !this.config.isMonoRecord) {
            if ("domain" in params) {
                this._cfBaseDomain = params.domain;
            }
            const base = this._cfBaseDomain ?? this.config.domain;
            params = { ...params, domain: Domain.and([base, this._cfDomain]).toList() };
        } else if ("domain" in params) {
            this._cfBaseDomain = params.domain;
        }
        return super.load(params);
    },

    async setColumnFilterDomain(domain) {
        if (this._cfBaseDomain === undefined) {
            this._cfBaseDomain = this.config.domain;
        }
        this._cfDomain = domain;
        await this.load({ domain: this._cfBaseDomain });
        this.notify();
    },
});

// ---------------------------------------------------------------------------
// ListRenderer
// ---------------------------------------------------------------------------

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.columnFilterOperators = FILTER_OPERATORS;
        const enabled = this.hasColumnFilter;
        const saved = enabled && this.columnFilterServerMode ? this.props.list.model._cfFilters : null;
        this.columnFilter = useState({ filters: { ...(saved || {}) }, menu: null });
        this._columnFilterTimers = {};
        if (!enabled) {
            return;
        }
        useEffect(() => this._syncColumnFilterRowNumberCell());
        useExternalListener(window, "mousedown", (ev) => {
            if (this.columnFilter.menu && !ev.target.closest(".o_list_cf_menu, .o_list_cf_op")) {
                this.columnFilter.menu = null;
            }
        });
        useExternalListener(
            window,
            "scroll",
            (ev) => {
                if (this.columnFilter.menu && !ev.target.closest?.(".o_list_cf_menu")) {
                    this.columnFilter.menu = null;
                }
            },
            true
        );
        onWillUnmount(() => {
            Object.values(this._columnFilterTimers).forEach((t) => clearTimeout(t));
        });
    },

    get hasColumnFilter() {
        // archInfo нь renderer-ийн амьдралын туршид өөрчлөгддөггүй тул нэг удаа тооцоолно
        // (getRowClass мөр бүрд дуудагддаг тул шүүлтүүргүй хүснэгтэд ч зардал гаргахгүй)
        if (this._cfEnabled === undefined) {
            const cls = this.props.archInfo?.className || "";
            this._cfEnabled = cls.split(/\s+/).includes(FILTER_CLASS);
        }
        return this._cfEnabled;
    },

    /** Үндсэн (хуудаслагдсан) жагсаалт бол server талд, x2many бол client талд шүүнэ */
    get columnFilterServerMode() {
        const list = this.props.list;
        return !!list?.model && list.model.root === list && !list.model.config?.isMonoRecord;
    },

    get columnFilterActive() {
        return Object.values(this.columnFilter.filters).some((f) => this._isFilterUsable(f));
    },

    // ------------------------------------------------------------------
    // Filter state
    // ------------------------------------------------------------------

    _columnFilterField(column) {
        return this.props.list.fields[column.name];
    },

    isColumnFilterable(column) {
        if (column.type !== "field" || column.widget === "handle") {
            return false;
        }
        const field = this._columnFilterField(column);
        if (!field || field.type === "properties" || field.type === "binary") {
            return false;
        }
        if (this.columnFilterServerMode && field.searchable === false) {
            return false;
        }
        return true;
    },

    getColumnFilterOperators(column) {
        const allowed = OPS_BY_KIND[fieldKind(this._columnFilterField(column))];
        return FILTER_OPERATORS.filter((o) => allowed.includes(o.id));
    },

    _defaultFilterOp(column) {
        const kind = fieldKind(this._columnFilterField(column));
        return kind === "text" || kind === "relational" ? "contains" : "eq";
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

    _setColumnFilter(name, filter) {
        const before = this.columnFilter.filters[name];
        const wasUsable = this._isFilterUsable(before);
        this.columnFilter.filters[name] = filter;
        const changed =
            this._isFilterUsable(filter) || wasUsable
                ? !before || before.op !== filter.op || before.value !== filter.value
                : false;
        if (changed && this.columnFilterServerMode) {
            this._applyServerColumnFilter();
        }
    },

    onColumnFilterInput(column, ev) {
        const value = ev.target.value;
        const delay = this.columnFilterServerMode ? 600 : 200;
        clearTimeout(this._columnFilterTimers[column.name]);
        this._columnFilterTimers[column.name] = setTimeout(() => {
            this._setColumnFilter(column.name, { ...this.getColumnFilter(column), value });
        }, delay);
    },

    onColumnFilterKeydown(column, ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            clearTimeout(this._columnFilterTimers[column.name]);
            this._setColumnFilter(column.name, {
                ...this.getColumnFilter(column),
                value: ev.target.value,
            });
        } else if (ev.key === "Escape") {
            ev.preventDefault();
            ev.target.value = "";
            clearTimeout(this._columnFilterTimers[column.name]);
            this._setColumnFilter(column.name, { ...this.getColumnFilter(column), value: "" });
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

    get columnFilterMenuColumn() {
        const name = this.columnFilter.menu?.column;
        return name ? this.state.columns.find((c) => c.name === name) : null;
    },

    selectColumnFilterOperator(opId) {
        const column = this.columnFilterMenuColumn;
        this.columnFilter.menu = null;
        if (!column) {
            return;
        }
        const input = this.tableRef?.el?.querySelector(
            `tr.o_list_cf_row th[data-name="${column.name}"] input.o_list_cf_input`
        );
        const value = input ? input.value : this.getColumnFilter(column).value;
        clearTimeout(this._columnFilterTimers[column.name]);
        this._setColumnFilter(column.name, { op: opId, value });
        if (input && !NO_VALUE_OPS.includes(opId)) {
            input.focus();
        }
    },

    clearColumnFilters() {
        Object.values(this._columnFilterTimers).forEach((t) => clearTimeout(t));
        const hadFilter = this.columnFilterActive;
        this.columnFilter.filters = {};
        this.columnFilter.menu = null;
        const row = this.tableRef?.el?.querySelector(".o_list_cf_row");
        if (row) {
            row.querySelectorAll("input.o_list_cf_input").forEach((input) => (input.value = ""));
        }
        if (hadFilter && this.columnFilterServerMode) {
            this._applyServerColumnFilter();
        }
    },

    // ------------------------------------------------------------------
    // Server mode: domain
    // ------------------------------------------------------------------

    async _applyServerColumnFilter() {
        const list = this.props.list;
        const model = list.model;
        const domain = this._buildColumnFilterDomain();
        model._cfFilters = { ...this.columnFilter.filters };
        if (list.editedRecord && list.leaveEditMode) {
            const ok = await list.leaveEditMode();
            if (ok === false) {
                return;
            }
        }
        await model.setColumnFilterDomain(domain);
    },

    _buildColumnFilterDomain() {
        const domains = [];
        const byName = Object.fromEntries(this.allColumns.map((c) => [c.name, c]));
        for (const [name, filter] of Object.entries(this.columnFilter.filters)) {
            const column = byName[name];
            if (!column || !this._isFilterUsable(filter) || !this.isColumnFilterable(column)) {
                continue;
            }
            const leaf = this._columnFilterDomain(this.props.list.fields[name], name, filter);
            if (leaf) {
                domains.push(leaf);
            }
        }
        return domains.length ? Domain.and(domains).toList() : [];
    },

    _columnFilterDomain(field, name, { op, value }) {
        const kind = fieldKind(field);
        const q = String(value).trim();
        const not = (d) => Domain.not(d).toList();

        if (op === "empty" || op === "not_empty") {
            let empty;
            if (kind === "numeric") {
                empty = ["|", [name, "=", false], [name, "=", 0]];
            } else if (TEXT_TYPES.includes(field.type)) {
                empty = ["|", [name, "=", false], [name, "=", ""]];
            } else {
                empty = [[name, "=", false]];
            }
            return op === "empty" ? empty : not(empty);
        }

        if (kind === "numeric") {
            const num = parseNumber(q);
            if (isNaN(num)) {
                return null;
            }
            const sqlOp = { eq: "=", ne: "!=", gt: ">", ge: ">=", lt: "<", le: "<=" }[op] || "=";
            return [[name, sqlOp, num]];
        }

        if (kind === "date") {
            const parsed = parseDateInput(field, q);
            if (!parsed) {
                return null;
            }
            let start;
            let end;
            if (field.type === "date") {
                start = end = serializeDate(parsed);
            } else {
                start = serializeDateTime(parsed.startOf("day"));
                end = serializeDateTime(parsed.endOf("day"));
            }
            const sameDay = [[name, ">=", start], [name, "<=", end]];
            switch (op) {
                case "eq":
                    return sameDay;
                case "ne":
                    return not(sameDay);
                case "gt":
                    return [[name, ">", end]];
                case "ge":
                    return [[name, ">=", start]];
                case "lt":
                    return [[name, "<", start]];
                case "le":
                    return [[name, "<=", end]];
            }
            return null;
        }

        if (kind === "boolean") {
            const bool = parseBoolean(q);
            return [[name, op === "ne" ? "!=" : "=", bool]];
        }

        if (field.type === "selection") {
            const keys = (field.selection || [])
                .filter(([, label]) => textMatch(label, q, op))
                .map(([key]) => key);
            return [[name, "in", keys]];
        }

        // char / text / html / many2one / many2many / one2many
        const like = escapeLike(q);
        switch (op) {
            case "contains":
                return [[name, "ilike", q]];
            case "not_contains":
                return not([[name, "ilike", q]]);
            case "starts":
                return [[name, "=ilike", `${like}%`]];
            case "not_starts":
                return not([[name, "=ilike", `${like}%`]]);
            case "ends":
                return [[name, "=ilike", `%${like}`]];
            case "not_ends":
                return not([[name, "=ilike", `%${like}`]]);
            case "eq":
                return [[name, "=ilike", like]];
            case "ne":
                return not([[name, "=ilike", like]]);
            case "gt":
                return [[name, ">", q]];
            case "ge":
                return [[name, ">=", q]];
            case "lt":
                return [[name, "<", q]];
            case "le":
                return [[name, "<=", q]];
        }
        return null;
    },

    // ------------------------------------------------------------------
    // Client mode (x2many): matching
    // ------------------------------------------------------------------

    _columnFilterText(field, value) {
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
        const kind = fieldKind(field);
        const q = String(filter.value).trim();

        if (kind === "numeric") {
            if (op === "empty") {
                return !raw;
            }
            if (op === "not_empty") {
                return !!raw;
            }
            const num = parseNumber(q);
            return isNaN(num) ? true : compare(Number(raw) || 0, num, op);
        }
        if (kind === "boolean") {
            const match = !!raw === parseBoolean(q);
            return op === "ne" ? !match : match;
        }
        if (kind === "date") {
            if (op === "empty") {
                return !raw;
            }
            if (op === "not_empty") {
                return !!raw;
            }
            const target = parseDateInput(field, q);
            if (!target) {
                return true;
            }
            if (!raw) {
                return false;
            }
            const a = raw.startOf("day").toMillis();
            const b = target.startOf("day").toMillis();
            return compare(a, b, op);
        }
        return textMatch(this._columnFilterText(field, raw), q, op);
    },

    isRecordFilteredOut(record) {
        if (!this.hasColumnFilter || this.columnFilterServerMode || !this.columnFilterActive) {
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
        const list = this.props.list;
        if (this.columnFilterServerMode) {
            return { shown: list.count, total: null };
        }
        const records = list.records || [];
        const shown = records.filter((r) => !this.isRecordFilteredOut(r)).length;
        return { shown, total: records.length };
    },

    get columnFilterClearTitle() {
        const { shown, total } = this.columnFilterCount;
        const count = total === null ? `${shown}` : `${shown} / ${total}`;
        return `Шүүлтүүр арилгах (${count})`;
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
        if (
            !this.hasColumnFilter ||
            this.columnFilterServerMode ||
            !this.columnFilterActive ||
            list.isGrouped ||
            (list.selection && list.selection.length)
        ) {
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
