import ExcelJS from 'exceljs'
import { VERDICT_TEXT, type BatchTotals, type ExportRow } from './batchTest'

/**
 * The batch run, in the three formats people actually ask for.
 *
 * Every one of them carries the whole run, right and wrong. The misses are the
 * useful half - they are the list of products that need a photograph, which is
 * the one change that measurably improves the search - so an export that kept
 * only the successes would answer "how did we do" while hiding "what do we do
 * next".
 *
 * Excel is the one to open: it lays the same rows out so the failures are
 * visible without sorting. CSV is for whatever consumes files; JSON is for
 * whatever consumes data.
 */

/** The formats offered, in the order the menu lists them. */
export const EXPORT_FORMATS = [
  { id: 'excel', label: 'Excel', hint: '.xlsx, formatted' },
  { id: 'csv', label: 'CSV', hint: 'for spreadsheets and scripts' },
  { id: 'json', label: 'JSON', hint: 'with totals, for code' },
] as const

export type ExportFormat = (typeof EXPORT_FORMATS)[number]['id']

const HEADERS = [
  { header: 'Photo', key: 'fileName', width: 30 },
  { header: 'Expected SKU', key: 'expectedSku', width: 16 },
  { header: 'Found SKU', key: 'foundSku', width: 16 },
  { header: 'Product', key: 'productName', width: 52 },
  { header: 'Brand', key: 'brand', width: 18 },
  { header: 'Score', key: 'score', width: 10 },
  { header: 'Matched by', key: 'matchedBy', width: 14 },
  { header: 'Result', key: 'result', width: 15 },
]

/**
 * How each outcome is painted.
 *
 * `row` tints the whole line so a failure is visible while scrolling, without
 * reading a word; `chip` is the stronger fill behind the Result cell itself.
 * An exact match gets no row tint at all - if everything is coloured, nothing
 * stands out, and the successes are the ones nobody needs to act on.
 *
 * Deliberately not the app's accent palette. A spreadsheet is read on white,
 * often printed, and sometimes by someone who is red-green colourblind - so
 * every row carries its verdict as a word as well as a colour, and the fills
 * stay pale enough for black text on paper.
 */
const RESULT_STYLE: Record<string, { row?: string; chip: string; ink: string }> = {
  exact: { chip: 'FFD9EFDD', ink: 'FF1B5E20' },
  'in top five': { row: 'FFFFF7E6', chip: 'FFFDE8B8', ink: 'FF8A5A00' },
  'not found': { row: 'FFFDECEC', chip: 'FFF8CFCF', ink: 'FF9B1C1C' },
  'not counted': { row: 'FFF7F7F8', chip: 'FFEDEDEF', ink: 'FF6B6B6B' },
}

const INK = 'FF1F2A37'
const RULE = 'FFD6DCE4'

export async function buildResultsWorkbook(
  rows: ExportRow[],
  totals: BatchTotals,
): Promise<Blob> {
  const workbook = new ExcelJS.Workbook()
  workbook.creator = 'RigidHitch Part Finder'
  workbook.created = new Date()

  const sheet = workbook.addWorksheet('Batch results', {
    views: [{ state: 'frozen', ySplit: 6 }],
    pageSetup: { orientation: 'landscape', fitToPage: true, fitToWidth: 1, fitToHeight: 0 },
  })
  sheet.columns = HEADERS.map(({ key, width }) => ({ key, width }))
  const lastColumn = HEADERS.length

  // --- title block ----------------------------------------------------------
  sheet.mergeCells(1, 1, 1, lastColumn)
  const title = sheet.getCell('A1')
  title.value = 'RigidHitch Part Finder - batch results'
  title.font = { name: 'Calibri', size: 16, bold: true, color: { argb: INK } }
  sheet.getRow(1).height = 24

  sheet.mergeCells(2, 1, 2, lastColumn)
  const subtitle = sheet.getCell('A2')
  subtitle.value = new Date().toLocaleString(undefined, { dateStyle: 'long', timeStyle: 'short' })
  subtitle.font = { name: 'Calibri', size: 10, color: { argb: 'FF6B7280' } }

  sheet.mergeCells(3, 1, 3, lastColumn)
  const summary = sheet.getCell('A3')
  summary.value =
    totals.scored > 0
      ? `${totals.top1} of ${totals.scored} found the exact product  ·  `
        + `${totals.top5} of ${totals.scored} in the top five`
        + (totals.unscored ? `  ·  ${totals.unscored} not counted` : '')
      : `${rows.length} photographs searched, none named a SKU so none were scored`
  summary.font = { name: 'Calibri', size: 11, bold: true, color: { argb: INK } }

  sheet.mergeCells(4, 1, 4, lastColumn)
  const caveat = sheet.getCell('A4')
  // Stated in the file itself, because a spreadsheet outlives the conversation
  // that produced it and someone will quote this number in a meeting.
  caveat.value =
    'Indicative, not a measurement - a small folder of photographs. The catalogue-wide figures '
    + 'are 89.7% category and 70.2% top-five, from thousands of held-out queries. '
    + 'Highlighted rows did not find the exact product.'
  caveat.font = { name: 'Calibri', size: 9, italic: true, color: { argb: 'FF6B7280' } }
  sheet.getRow(5).height = 6

  // --- table ----------------------------------------------------------------
  const headerRow = sheet.getRow(6)
  HEADERS.forEach(({ header }, index) => {
    const cell = headerRow.getCell(index + 1)
    cell.value = header
    cell.font = { name: 'Calibri', size: 11, bold: true, color: { argb: 'FFFFFFFF' } }
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: INK } }
    cell.alignment = { vertical: 'middle', horizontal: index >= 5 ? 'center' : 'left' }
  })
  headerRow.height = 20

  rows.forEach((row) => {
    const result = VERDICT_TEXT[row.verdict]
    const style = RESULT_STYLE[result]
    const added = sheet.addRow({
      fileName: row.fileName,
      expectedSku: row.expectedSku || '-',
      foundSku: row.foundSku,
      productName: row.productName,
      brand: row.brand,
      score: row.score,
      matchedBy: row.matchedBy,
      result,
    })
    added.font = { name: 'Calibri', size: 11, color: { argb: INK } }
    added.alignment = { vertical: 'top' }
    added.height = 18

    for (let column = 1; column <= lastColumn; column += 1) {
      const cell = added.getCell(column)
      cell.border = { bottom: { style: 'hair', color: { argb: RULE } } }
      if (style.row) {
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: style.row } }
      }
    }

    added.getCell('fileName').font = { name: 'Consolas', size: 10, color: { argb: INK } }
    added.getCell('expectedSku').font = { name: 'Consolas', size: 10, color: { argb: INK } }
    // The found SKU is the thing to look at on a row that went wrong, so on
    // those rows it is bold and in the verdict's ink rather than plain.
    added.getCell('foundSku').font = {
      name: 'Consolas',
      size: 10,
      bold: row.verdict !== 'top1',
      color: { argb: row.verdict === 'top1' ? INK : style.ink },
    }

    // A percentage rather than a raw cosine: everyone reading this file sees
    // percentages in the app, and two representations of one number invites
    // someone to quote 0.94 as "0.94% accurate".
    const score = added.getCell('score')
    score.numFmt = '0.0%'
    score.alignment = { horizontal: 'center' }
    added.getCell('matchedBy').alignment = { horizontal: 'center' }

    const verdictCell = added.getCell('result')
    verdictCell.alignment = { horizontal: 'center' }
    verdictCell.font = { name: 'Calibri', size: 11, bold: true, color: { argb: style.ink } }
    verdictCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: style.chip } }
  })

  // Sort and filter from the header, so "show me only the misses" is two clicks.
  if (rows.length) {
    sheet.autoFilter = {
      from: { row: 6, column: 1 },
      to: { row: 6 + rows.length, column: lastColumn },
    }
  }

  const buffer = await workbook.xlsx.writeBuffer()
  return new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
}

/**
 * The same rows as CSV.
 *
 * Quoting is not optional. Product names carry commas ("ST-400D 4 Universal
 * Valcrum Aluminum Threaded Hub Cap, Fits Dexter 9K...") and inch marks (3/4"),
 * either of which would otherwise break the columns halfway down.
 */
export function resultsCsv(rows: ExportRow[]): Blob {
  const header = [
    'photo', 'expected_sku', 'found_sku', 'product', 'brand', 'score', 'matched_by', 'result',
  ]
  const quote = (value: string | number) => `"${String(value).replace(/"/g, '""')}"`
  const lines = rows.map((row) =>
    [
      row.fileName,
      row.expectedSku,
      row.foundSku,
      row.productName,
      row.brand,
      row.score.toFixed(3),
      row.matchedBy,
      VERDICT_TEXT[row.verdict],
    ]
      .map(quote)
      .join(','),
  )
  const csv = [header.join(','), ...lines].join('\r\n')
  // The BOM makes Excel read it as UTF-8; without it an accented brand name
  // arrives mangled.
  return new Blob(['﻿', csv], { type: 'text/csv;charset=utf-8' })
}

/** The same rows as JSON, with the totals so the file stands on its own. */
export function resultsJson(rows: ExportRow[], totals: BatchTotals): Blob {
  const payload = {
    generated: new Date().toISOString(),
    note:
      'Indicative, not a measurement - a small folder of photographs. Catalogue-wide figures are '
      + '89.7% category and 70.2% top-five, from thousands of held-out queries.',
    totals,
    results: rows.map((row) => ({
      photo: row.fileName,
      expected_sku: row.expectedSku || null,
      found_sku: row.foundSku,
      product: row.productName,
      brand: row.brand,
      score: Number(row.score.toFixed(4)),
      matched_by: row.matchedBy,
      result: VERDICT_TEXT[row.verdict],
      exact: row.verdict === 'top1',
    })),
  }
  return new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
}

/** Hands the browser a file to save. */
export function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
