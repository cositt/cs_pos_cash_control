/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";

/**
 * Estilos del ticket custom embebidos para un .html autónomo (mismo aspecto que en TPV con cash_control.scss).
 * Mantener alineado con static/src/scss/cash_control.scss → bloque .cs-pos-cash-closing-receipt
 */
const CLOSING_RECEIPT_EMBEDDED_STYLES = `
body { margin: 0; padding: 12px; background: #e9ecef; font-family: system-ui, sans-serif; }
.preview-wrap {
  max-width: 80mm;
  margin: 0 auto;
  padding: 10px 8px 16px;
  background: #fff;
  box-shadow: 0 1px 6px rgba(0,0,0,0.12);
}
.pos-receipt { font-size: 13px; line-height: 1.2; color: #000; }
.cs-pos-cash-closing-receipt {
    font-size: 14px;
    line-height: 1.25;
    color: #000;
}
.cs-pos-cash-closing-receipt .cs-receipt-center { text-align: center; }
.cs-pos-cash-closing-receipt .cs-receipt-title,
.cs-pos-cash-closing-receipt .cs-receipt-company { font-weight: 700; }
.cs-pos-cash-closing-receipt .cs-receipt-separator {
    border-top: 1px dashed #000;
    margin: 8px 0;
}
.cs-pos-cash-closing-receipt .cs-section-title {
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 3px;
}
.cs-pos-cash-closing-receipt .cs-section-spaced { margin-top: 6px; }
.cs-pos-cash-closing-receipt .cs-line {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    align-items: baseline;
}
.cs-pos-cash-closing-receipt .cs-line span:first-child {
    min-width: 0;
    overflow-wrap: anywhere;
}
.cs-pos-cash-closing-receipt .cs-line span:last-child {
    text-align: right;
    white-space: nowrap;
}
.cs-pos-cash-closing-receipt .cs-cash-move-line {
    padding-left: 0.35rem;
    font-size: 0.95em;
}
.cs-pos-cash-closing-receipt .cs-cash-move-line span:first-child {
    font-style: italic;
}
.cs-pos-cash-closing-receipt .cs-total-line {
    font-weight: 700;
    border-top: 1px solid #000;
    margin-top: 3px;
    padding-top: 3px;
}
.cs-pos-cash-closing-receipt .cs-tax-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.15fr) 0.95fr 0.85fr 0.95fr;
    gap: 4px;
    align-items: baseline;
}
.cs-pos-cash-closing-receipt .cs-tax-grid span:not(:first-child) {
    text-align: right;
    white-space: nowrap;
}
.cs-pos-cash-closing-receipt .cs-tax-header {
    font-weight: 700;
    border-bottom: 1px solid #000;
    margin-bottom: 3px;
    padding-bottom: 2px;
}
`;

/** @param {object} pos instancia TPV (pos.data, pos.session, pos.env.utils) */
export async function fetchSessionSaleDetails(pos) {
    return pos.data.call(
        "report.point_of_sale.report_saledetails",
        "get_sale_details",
        [false, false, false, [pos.session.id]]
    );
}

/** @param {object} saleDetails @param {object} pos @returns {HTMLElement} */
export function renderClosingReceiptElement(saleDetails, pos) {
    const template = saleDetails.cs_pos_cash_closing
        ? "cs_pos_cash_control.PosCashClosingReport"
        : "point_of_sale.SaleDetailsReport";
    return renderToElement(
        template,
        Object.assign({}, saleDetails, {
            date: new Date().toLocaleString(),
            pos,
            formatCurrency: pos.env.utils.formatCurrency,
        })
    );
}

/**
 * Descarga un HTML autocontenido (abrir en navegador ≈ aspecto ticket 80mm).
 * @param {HTMLElement} reportEl nodo raíz del informe (p. ej. .pos-receipt)
 * @param {number} sessionId
 * @param {{ isCustomClosing?: boolean }} [opts]
 */
export function downloadClosingReceiptAsHtml(reportEl, sessionId, opts = {}) {
    const title = opts.isCustomClosing
        ? `cierre_caja_sesion_${sessionId}`
        : `informe_ventas_sesion_${sessionId}`;
    const html = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>${title}</title>
<style>${CLOSING_RECEIPT_EMBEDDED_STYLES}</style>
</head>
<body>
<p style="text-align:center;font-size:12px;color:#666;margin:0 0 8px">Vista previa (HTML). Misma maqueta que enviaría el TPV a la impresora térmica.</p>
<div class="preview-wrap">${reportEl.outerHTML}</div>
</body>
</html>`;
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title}.html`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}
