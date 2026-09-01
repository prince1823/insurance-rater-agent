# Decision trace — `pvt-car-comprehensive-hdfc-ergo.pdf`

- **Status:** `resolved`
- **Insurer:** HDFC ERGO  (grid: `Pvt Car New Grid Eff 1st Feb'25 (HDFC ergo) 1.pdf`)
- **Policy type:** comprehensive  ·  **Business type:** rollover
- **OD commission:** 15.0% on OD premium
- **TP commission:** 0.0% on TP premium
- **Confidence:** medium — low-confidence extraction for: fuel; fuel type not printed on the schedule; inferred from make/model

## Extracted facts

| Fact | Value | Page | Confidence |
|---|---|---|---|
| insurer | HDFC ERGO General Insurance Company Limited | 1 | 0.99 |
| previous insurer | TATA AIG GENERAL INSURANCE CO.LTD. | 1 | 0.95 |
| business type | rollover |  |  |
| policy type | comprehensive |  |  |
| make | MAHINDRA | 1 | 0.99 |
| model | BOLERO NEO-N10 (R) | 1 | 0.98 |
| fuel | diesel |  | 0.5 |
| engine cc | 1493 | 1 | 0.98 |
| RTO code | HR-26 | 1 | 0.92 |
| RTO location | GURGAON | 1 | 0.97 |
| manufacture year | 2023 | 1 | 0.97 |
| registration year | None |  | 0.0 |
| vehicle age (years) | 3 |  |  |
| NCB % | 25 | 1 | 0.5 |
| zero depreciation cover | True | 1 | 0.95 |
| OD premium | 8053 | 1 | 0.95 |
| TP premium | 3416 | 1 | 0.95 |
| net premium | 11869 | 1 | 0.9 |
| total premium (incl GST) | 14005 | 1 | 0.9 |

## Ordered decision trace

### 1. Map RTO to HDFC ERGO zone

RTO HR-26 -> Haryana -> Zone 2 (state 'Haryana' default zone 2).

- `pvt-car-comprehensive-hdfc-ergo.pdf` → `page 1` = `HR-26`  
  _Registration No HR-26-FB-8239 / RTO GURGAON_
- `Pvt Car New Grid Eff 1st Feb'25 (HDFC ergo) 1.pdf` → `page 1-2, 'Zone / State Name / Zone-1 / Zone-2' table` = `2`  
  _state Haryana, page 2_

### 2. Select premium slab

OD GWP ₹8,053 -> slab '<10k'.

- `pvt-car-comprehensive-hdfc-ergo.pdf` → `policy schedule`
- `Pvt Car New Grid Eff 1st Feb'25 (HDFC ergo) 1.pdf` → `page 1, slab column` = `<10k`

### 3. Read the OD commission cell

Zone 2, slab '<10k', Non-Petrol (NCB) column (footnote: Non-Petrol = Diesel/CNG/LPG) -> 15.0%.

- `Pvt Car New Grid Eff 1st Feb'25 (HDFC ergo) 1.pdf` → `page 1, 'Zone 2' table, row '<10k', column 'package_nonpetrol_ncb'` = `15.0`

### 4. Third-party commission

The HDFC ERGO Pvt Car grid publishes Package/SAOD (OD) rates only; TP = 0%.

- `Pvt Car New Grid Eff 1st Feb'25 (HDFC ergo) 1.pdf` → `page 1 (no TP column present)` = `0.0`

## All citations

- **policy** `pvt-car-comprehensive-hdfc-ergo.pdf` → `page 1` = `HR-26` — Registration No HR-26-FB-8239 / RTO GURGAON
- **pdf** `Pvt Car New Grid Eff 1st Feb'25 (HDFC ergo) 1.pdf` → `page 1-2, 'Zone / State Name / Zone-1 / Zone-2' table` = `2` — state Haryana, page 2
- **policy** `pvt-car-comprehensive-hdfc-ergo.pdf` → `policy schedule`
- **pdf** `Pvt Car New Grid Eff 1st Feb'25 (HDFC ergo) 1.pdf` → `page 1, slab column` = `<10k`
- **pdf** `Pvt Car New Grid Eff 1st Feb'25 (HDFC ergo) 1.pdf` → `page 1, 'Zone 2' table, row '<10k', column 'package_nonpetrol_ncb'` = `15.0`
- **pdf** `Pvt Car New Grid Eff 1st Feb'25 (HDFC ergo) 1.pdf` → `page 1 (no TP column present)` = `0.0`
- **pdf** `Pvt Car New Grid Eff 1st Feb'25 (HDFC ergo) 1.pdf` → `page 1` — Slab will be calculated basis comprehensive + SAOD GWP on PVT CAR (SATP premium is excluded for slab achievement)
