# Decision trace — `pvt-car-satp-tata-aig.pdf`

- **Status:** `resolved`
- **Insurer:** Tata AIG  (grid: `Tata AIG Standard Grid_Communication_Mar'26_F_v2_0212.xlsx`)
- **Policy type:** standalone_tp  ·  **Business type:** unknown
- **OD commission:** _not applicable_
- **TP commission:** 38.0% on Net premium
- **Confidence:** high — all driver facts extracted with high confidence and matched grid keys exactly

> segment/business-type ambiguity collapsed: every candidate (Mini/Renewal, Mini/Rollover) gives 38.0%

## Extracted facts

| Fact | Value | Page | Confidence |
|---|---|---|---|
| insurer | TATA AIG General Insurance Company Limited | 1 | 0.99 |
| previous insurer | None |  | 0.0 |
| business type | unknown |  |  |
| policy type | standalone_tp |  |  |
| make | MARUTI | 4 | 0.97 |
| model | ZEN ESTILO LXI CNG | 4 | 0.95 |
| fuel | cng | 4 | 0.97 |
| engine cc | 998 | 4 | 0.96 |
| RTO code | DL-9C | 4 | 0.92 |
| RTO location | DELHI | 4 | 0.96 |
| manufacture year | 2011 | 4 | 0.95 |
| registration year | 2011 | 4 | 0.95 |
| vehicle age (years) | 15 |  |  |
| NCB % | None |  | 0.0 |
| zero depreciation cover | False |  | 0.6 |
| OD premium | None |  | 0.0 |
| TP premium | 2094 | 5 | 0.95 |
| net premium | 2154 | 5 | 0.92 |
| total premium (incl GST) | 2542 | 5 | 0.92 |

## Ordered decision trace

### 1. Map RTO to Tata AIG cluster column

RTO location 'DELHI' matched cluster column 'DELHI' (score 100).

- `pvt-car-satp-tata-aig.pdf` → `page 4` = `DELHI`  
  _RTO Location DELHI; Zone A_

### 2. Classify vehicle segment

model 'ZEN ESTILO LXI CNG' matched curated entry 'zen estilo' -> Mini. Candidate segment(s): ['Mini'].

- `pvt-car-satp-tata-aig.pdf` → `page 4` = `ZEN ESTILO LXI CNG`  
  _MARUTI / ZEN ESTILO / LXI CNG_

### 3. Determine business type

Extracted business type 'unknown' (previous insurer not stated). Grid business-type candidate(s): ['Renewal', 'Rollover'].

- `pvt-car-satp-tata-aig.pdf` → `policy schedule`  
  _no previous-insurer / previous-policy field printed on this schedule_

### 4. Look up the commission cell

Section 'SATP', fuel 'CNG', column 'DELHI' -> 38.0% (Pvtcar!V527). segment/business-type ambiguity collapsed: every candidate (Mini/Renewal, Mini/Rollover) gives 38.0%

- `Tata AIG Standard Grid_Communication_Mar'26_F_v2_0212.xlsx` → `Pvtcar!V527` = `38.0`
- `Tata AIG Standard Grid_Communication_Mar'26_F_v2_0212.xlsx` → `Pvtcar!V529` = `38.0`
- `Tata AIG Standard Grid_Communication_Mar'26_F_v2_0212.xlsx` → `Pvtcar!V555` = `38.0`
- `Tata AIG Standard Grid_Communication_Mar'26_F_v2_0212.xlsx` → `Pvtcar!V557` = `38.0`

## All citations

- **policy** `pvt-car-satp-tata-aig.pdf` → `page 4` = `DELHI` — RTO Location DELHI; Zone A
- **policy** `pvt-car-satp-tata-aig.pdf` → `policy schedule` — no previous-insurer / previous-policy field printed on this schedule
- **xlsx** `Tata AIG Standard Grid_Communication_Mar'26_F_v2_0212.xlsx` → `Pvtcar!V527` = `38.0`
- **xlsx** `Tata AIG Standard Grid_Communication_Mar'26_F_v2_0212.xlsx` → `Pvtcar!V529` = `38.0`
- **xlsx** `Tata AIG Standard Grid_Communication_Mar'26_F_v2_0212.xlsx` → `Pvtcar!V555` = `38.0`
- **xlsx** `Tata AIG Standard Grid_Communication_Mar'26_F_v2_0212.xlsx` → `Pvtcar!V557` = `38.0`
- **xlsx** `Tata AIG Standard Grid_Communication_Mar'26_F_v2_0212.xlsx` → `General Guidelines!C6` — Payout % for CV on Net Premium
- **xlsx** `Tata AIG Standard Grid_Communication_Mar'26_F_v2_0212.xlsx` → `General Guidelines!C7` — Payout % for Pvt Car- SATP on Net Premium; Package and SAOD on OD premium
