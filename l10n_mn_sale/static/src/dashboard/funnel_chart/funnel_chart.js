/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

const { AbstractChart, CommandResult } = spreadsheet;
const { chartRegistry, chartComponentRegistry } = spreadsheet.registries;

function createValidRange(getters, sheetId, xc) {
    if (!xc) {
        return undefined;
    }
    try {
        const range = getters.getRangeFromSheetXC(sheetId, xc);
        return !(range.invalidSheetName || range.invalidXc) ? range : undefined;
    } catch {
        return undefined;
    }
}

function getCellValue(getters, range) {
    if (!range) {
        return 0;
    }
    try {
        const cell = getters.getEvaluatedCell({
            sheetId: range.sheetId,
            col: range.zone.left,
            row: range.zone.top,
        });
        if (!cell || cell.value === undefined || cell.value === null) {
            return 0;
        }
        const num = Number(cell.value);
        return isNaN(num) ? 0 : num;
    } catch {
        return 0;
    }
}

export function formatMoney(amount) {
    if (!amount || isNaN(amount)) {
        return "0 ₮";
    }
    const rounded = Math.round(amount);
    const formatted = rounded.toLocaleString("en-US").replace(/,/g, "'");
    return `${formatted} ₮`;
}

export class FunnelChart extends AbstractChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.type = definition.type || "funnel";
        this.title = definition.title || _t("Quotation to Order Funnel");
        this.background = definition.background || "#FFFFFF";
        this.mode = definition.mode || "amount";

        // Amount ranges
        this.quotationsAmountRange = createValidRange(
            getters,
            sheetId,
            definition.quotationsAmountRange || definition.quotationsRange
        );
        this.ordersAmountRange = createValidRange(
            getters,
            sheetId,
            definition.ordersAmountRange || definition.ordersRange
        );
        this.draftAmountRange = createValidRange(
            getters,
            sheetId,
            definition.draftAmountRange || definition.draftRange
        );
        this.sentAmountRange = createValidRange(
            getters,
            sheetId,
            definition.sentAmountRange || definition.sentRange
        );

        // Count ranges (for supplementary details)
        this.quotationsCountRange = createValidRange(getters, sheetId, definition.quotationsCountRange);
        this.ordersCountRange = createValidRange(getters, sheetId, definition.ordersCountRange);
        this.draftCountRange = createValidRange(getters, sheetId, definition.draftCountRange);
        this.sentCountRange = createValidRange(getters, sheetId, definition.sentCountRange);
    }

    static validateChartDefinition(validator, definition) {
        return CommandResult.Success;
    }

    static transformDefinition(definition, executed) {
        return { ...definition };
    }

    static getDefinitionFromContextCreation(context) {
        return {
            type: "funnel",
            title: context.title || _t("Quotation to Order Funnel"),
            background: context.background || "#FFFFFF",
            mode: "amount",
            quotationsAmountRange: "Data!B11",
            ordersAmountRange: "Data!B12",
            draftAmountRange: "Data!B9",
            sentAmountRange: "Data!B10",
            quotationsCountRange: "Data!B4",
            ordersCountRange: "Data!B5",
            draftCountRange: "Data!B2",
            sentCountRange: "Data!B3",
        };
    }

    copyForSheetId(sheetId) {
        return new FunnelChart(this.getDefinition(), sheetId, this.getters);
    }

    copyInSheetId(sheetId) {
        return new FunnelChart(this.getDefinition(), sheetId, this.getters);
    }

    getDefinition() {
        return {
            type: this.type,
            title: this.title,
            background: this.background,
            mode: this.mode,
            quotationsAmountRange: this.quotationsAmountRange
                ? this.getters.getRangeString(this.quotationsAmountRange, this.sheetId)
                : undefined,
            ordersAmountRange: this.ordersAmountRange
                ? this.getters.getRangeString(this.ordersAmountRange, this.sheetId)
                : undefined,
            draftAmountRange: this.draftAmountRange
                ? this.getters.getRangeString(this.draftAmountRange, this.sheetId)
                : undefined,
            sentAmountRange: this.sentAmountRange
                ? this.getters.getRangeString(this.sentAmountRange, this.sheetId)
                : undefined,
            quotationsCountRange: this.quotationsCountRange
                ? this.getters.getRangeString(this.quotationsCountRange, this.sheetId)
                : undefined,
            ordersCountRange: this.ordersCountRange
                ? this.getters.getRangeString(this.ordersCountRange, this.sheetId)
                : undefined,
            draftCountRange: this.draftCountRange
                ? this.getters.getRangeString(this.draftCountRange, this.sheetId)
                : undefined,
            sentCountRange: this.sentCountRange
                ? this.getters.getRangeString(this.sentCountRange, this.sheetId)
                : undefined,
        };
    }

    getContextCreation() {
        return {
            background: this.background,
            title: this.title,
        };
    }

    getDefinitionForExcel() {
        return undefined;
    }

    updateRanges(applyChange) {
        return this;
    }
}

export function createFunnelChartRuntime(chart, getters) {
    const background = chart.background || "#FFFFFF";

    // Amounts
    const draftAmount = getCellValue(getters, chart.draftAmountRange);
    const sentAmount = getCellValue(getters, chart.sentAmountRange);
    const pendingRawAmount = getCellValue(getters, chart.quotationsAmountRange);
    const ordersAmount = getCellValue(getters, chart.ordersAmountRange);

    const pendingAmount = (draftAmount + sentAmount > 0) ? (draftAmount + sentAmount) : pendingRawAmount;
    const totalQuotationsAmount = (pendingAmount + ordersAmount > 0)
        ? (pendingAmount + ordersAmount)
        : (pendingRawAmount > 0 ? pendingRawAmount : ordersAmount);

    const conversionRate = totalQuotationsAmount > 0
        ? Math.min(100, Math.round((ordersAmount / totalQuotationsAmount) * 1000) / 10)
        : 0;

    // Counts (supplementary)
    const draftCount = getCellValue(getters, chart.draftCountRange);
    const sentCount = getCellValue(getters, chart.sentCountRange);
    const pendingRawCount = getCellValue(getters, chart.quotationsCountRange);
    const ordersCount = getCellValue(getters, chart.ordersCountRange);

    const pendingCount = (draftCount + sentCount > 0) ? (draftCount + sentCount) : pendingRawCount;
    const totalQuotationsCount = (pendingCount + ordersCount > 0)
        ? (pendingCount + ordersCount)
        : (pendingRawCount > 0 ? pendingRawCount : ordersCount);

    const totalQuotationsFormatted = formatMoney(totalQuotationsAmount);
    const ordersFormatted = formatMoney(ordersAmount);
    const pendingFormatted = formatMoney(pendingAmount);

    const stage1Title = _t("Quotations");
    const stage2Title = _t("Confirmed Orders");

    const stage1Text = `${totalQuotationsFormatted} (100%)`;
    const stage2Text = `${ordersFormatted} (${conversionRate}%)`;

    const stage1FontSize = stage1Text.length > 20 ? "12px" : (stage1Text.length > 15 ? "13px" : "14.5px");
    const stage2FontSize = stage2Text.length > 20 ? "11px" : (stage2Text.length > 15 ? "12px" : "13.5px");

    const footerText = (totalQuotationsCount > 0)
        ? `Хүлээгдэж буй: ${pendingFormatted} (${pendingCount} ш) | Батлагдсан: ${ordersFormatted} (${ordersCount} ш)`
        : `Хүлээгдэж буй: ${pendingFormatted} | Батлагдсан: ${ordersFormatted}`;

    return {
        title: chart.title ? _t(chart.title) : _t("Quotation to Order Funnel"),
        background,
        totalQuotationsAmount,
        ordersAmount,
        pendingAmount,
        totalQuotationsFormatted,
        ordersFormatted,
        pendingFormatted,
        conversionRate,
        totalQuotationsCount,
        ordersCount,
        pendingCount,
        stage1Title,
        stage2Title,
        stage1Text,
        stage2Text,
        stage1FontSize,
        stage2FontSize,
        footerText,
    };
}

export class FunnelChartComponent extends Component {
    static template = "l10n_mn_sale.FunnelChartComponent";
    static props = {
        figure: Object,
    };

    get runtime() {
        try {
            return this.env.model.getters.getChartRuntime(this.props.figure.id);
        } catch {
            return {
                title: _t("Quotation to Order Funnel"),
                background: "#FFFFFF",
                totalQuotationsAmount: 0,
                ordersAmount: 0,
                pendingAmount: 0,
                totalQuotationsFormatted: "0 ₮",
                ordersFormatted: "0 ₮",
                pendingFormatted: "0 ₮",
                conversionRate: 0,
                totalQuotationsCount: 0,
                ordersCount: 0,
                pendingCount: 0,
                stage1Title: _t("Quotations"),
                stage2Title: _t("Confirmed Orders"),
                stage1Text: "0 ₮ (100%)",
                stage2Text: "0 ₮ (0%)",
                stage1FontSize: "14.5px",
                stage2FontSize: "13.5px",
                footerText: "Хүлээгдэж буй: 0 ₮ | Батлагдсан: 0 ₮",
            };
        }
    }
}

chartRegistry.add("funnel", {
    match: (type) => type === "funnel",
    createChart: (definition, sheetId, getters) => new FunnelChart(definition, sheetId, getters),
    getChartRuntime: createFunnelChartRuntime,
    validateChartDefinition: (validator, definition) => FunnelChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition, executed) => FunnelChart.transformDefinition(definition, executed),
    getChartDefinitionFromContextCreation: (context) => FunnelChart.getDefinitionFromContextCreation(context),
    name: _t("Funnel"),
    sequence: 60,
});

chartComponentRegistry.add("funnel", FunnelChartComponent);
