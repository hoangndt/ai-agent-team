# Skill: Report Export

Use this skill for:

- Excel export using ClosedXML
- CSV export using CsvHelper
- PDF export (ReportExport.Pdf project)
- S3 upload of generated reports
- streaming vs in-memory export decisions
- export API endpoint implementation

---

## Goals

- Keep export logic isolated in dedicated export projects (`Excel`, `ReportExport`, `ReportExport.Pdf`, `ReportExport.Csv`)
- Stream large exports to avoid memory pressure
- Upload exports to S3 (`nrc-d-bi-report-exports` bucket) rather than returning binary directly where appropriate
- Keep export format logic separate from business/query logic

---

## Project Structure

- `Nrc.MarketInsights.Excel` — ClosedXML-based Excel generation
- `Nrc.MarketInsights.ReportExport` — shared export abstractions
- `Nrc.MarketInsights.ReportExport.Pdf` — PDF generation
- `Nrc.MarketInsights.ReportExport.Csv` — CsvHelper-based CSV generation
- Export results are uploaded to AWS S3 via `DataAccess.Aws`

---

## Excel (ClosedXML) Rules

1. Keep worksheet structure (columns, headers) defined in one place per export type
2. Apply consistent styling via reusable helpers — do not inline style code
3. Do not load entire datasets into memory if row count can be large — use streaming or chunked writes
4. Dispose workbook objects properly after generation
5. Test column ordering and header labels against acceptance criteria

---

## CSV (CsvHelper) Rules

1. Define a explicit class map for each CSV export — do not rely on reflection-only defaults
2. Use `CultureInfo.InvariantCulture` for number and date formatting
3. Handle nullable fields explicitly in class maps
4. Stream output to avoid large in-memory buffers

---

## PDF Rules

1. PDF generation belongs in `ReportExport.Pdf`
2. Keep layout and data logic separate
3. Test output rendering for known data shapes before declaring done

---

## S3 Upload Rules

- Generated export files are uploaded to S3 bucket `nrc-d-bi-report-exports`
- Object key must be deterministic and scoped per request/user/export type
- Return a pre-signed URL or download token to the client — never return raw S3 paths
- Upload errors must be surfaced explicitly

---

## Export API Checklist

For export endpoints, verify:

- export format is explicitly requested by client (Excel/CSV/PDF)
- appropriate Content-Type and Content-Disposition headers are set if streaming
- large result sets stream rather than buffer entirely in memory
- S3 upload errors return a meaningful error response, not a 500
- export job is scoped correctly (user permissions, data filters applied)
- test with empty result set — empty export file should still be valid

---

## Avoid

- Returning raw binary exports from endpoints without proper headers
- Loading entire export datasets into a single in-memory list without size awareness
- Mixing export format logic with business/query logic
- Hardcoding S3 bucket names outside of configuration
