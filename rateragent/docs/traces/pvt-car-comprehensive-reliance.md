# Decision trace — `pvt-car-comprehensive-reliance.pdf`

- **Status:** `resolved`
- **Insurer:** Reliance  (grid: `Reliance Broking Premier  FEB 26 Grid.xlsx`)
- **Policy type:** comprehensive  ·  **Business type:** unknown
- **OD commission:** 17.5% on OD premium
- **TP commission:** 0.0% on TP / net premium
- **Confidence:** medium — fuel type not printed on the schedule; inferred from make/model

## Extracted facts

| Fact | Value | Page | Confidence |
|---|---|---|---|
| insurer | Reliance General Insurance Company Limited | 2 | 0.99 |
| previous insurer | None |  | 0.0 |
| business type | unknown |  |  |
| policy type | comprehensive |  |  |
| make | RENAULT | 2 | 0.97 |
| model | KWID 1.0 RXT O | 2 | 0.95 |
| fuel | petrol |  | 0.6 |
| engine cc | 999 | 2 | 0.97 |
| RTO code | UP-16 | 2 | 0.9 |
| RTO location | UTTAR PRADESH - Noida | 2 | 0.95 |
| manufacture year | 2020 | 2 | 0.95 |
| registration year | None |  | 0.0 |
| vehicle age (years) | 6 |  |  |
| NCB % | 25 | 2 | 0.95 |
| zero depreciation cover | True | 2 | 0.85 |
| OD premium | 4714 | 2 | 0.9 |
| TP premium | 2094 | 2 | 0.92 |
| net premium | 7233 | 2 | 0.85 |
| total premium (incl GST) | 8535 | 2 | 0.9 |

## Ordered decision trace

### 1. Map RTO code to Reliance zone

RTO UP-16 -> region city 'Delhi', zone 'NORTH' via the 'RTO List' sheet.

- `pvt-car-comprehensive-reliance.pdf` → `page 2` = `UP-16`  
  _RTO Location UTTAR PRADESH - Noida; Registration No. UP16CS5830_
- `Reliance Broking Premier  FEB 26 Grid.xlsx` → `RTO List!E1253` = `NORTH`
- `Reliance Broking Premier  FEB 26 Grid.xlsx` → `RTO List!C1253` = `Delhi`

### 2. Select the Zone x region rate row

Zone 'NORTH' + region 'Delhi' -> grid row 'Delhi' (row 11).

- `Reliance Broking Premier  FEB 26 Grid.xlsx` → `PRIVATE CAR COMP, SAOD & STP!B11` = `Delhi`

### 3. Read the base OD commission

Fuel 'petrol', comprehensive -> Petrol/Bifuel comprehensive column (C) = 22.5 -> 22.5%.

- `Reliance Broking Premier  FEB 26 Grid.xlsx` → `PRIVATE CAR COMP, SAOD & STP!C11` = `22.5`

### 4. Apply < 1000 cc footnote

Engine 999 cc < 1000 -> subtract 5 points: 22.5% -> 17.5%.

- `pvt-car-comprehensive-reliance.pdf` → `page 2` = `999`  
  _CC / HP 999_
- `Reliance Broking Premier  FEB 26 Grid.xlsx` → `PRIVATE CAR COMP, SAOD & STP!H3`  
  _Payout for < 1000 CC, PO will be 5% lesser than the above Grid_

### 5. Read TP (STP) rate

STP column = 0 -> 0.0% on the TP component.

- `Reliance Broking Premier  FEB 26 Grid.xlsx` → `PRIVATE CAR COMP, SAOD & STP!F11` = `0`

## All citations

- **policy** `pvt-car-comprehensive-reliance.pdf` → `page 2` = `UP-16` — RTO Location UTTAR PRADESH - Noida; Registration No. UP16CS5830
- **xlsx** `Reliance Broking Premier  FEB 26 Grid.xlsx` → `RTO List!E1253` = `NORTH`
- **xlsx** `Reliance Broking Premier  FEB 26 Grid.xlsx` → `RTO List!C1253` = `Delhi`
- **xlsx** `Reliance Broking Premier  FEB 26 Grid.xlsx` → `PRIVATE CAR COMP, SAOD & STP!B11` = `Delhi`
- **xlsx** `Reliance Broking Premier  FEB 26 Grid.xlsx` → `PRIVATE CAR COMP, SAOD & STP!C11` = `22.5`
- **xlsx** `Reliance Broking Premier  FEB 26 Grid.xlsx` → `PRIVATE CAR COMP, SAOD & STP!H3` — Payout for < 1000 CC, PO will be 5% lesser than the above Grid
- **xlsx** `Reliance Broking Premier  FEB 26 Grid.xlsx` → `PRIVATE CAR COMP, SAOD & STP!F11` = `0`
- **xlsx** `Reliance Broking Premier  FEB 26 Grid.xlsx` → `PRIVATE CAR COMP, SAOD & STP!H2` — payout will made on OD Premium
- **xlsx** `Reliance Broking Premier  FEB 26 Grid.xlsx` → `PRIVATE CAR COMP, SAOD & STP!H4` — Standlone ZD policies 2.5%will be redused from the above Grid
- **xlsx** `Reliance Broking Premier  FEB 26 Grid.xlsx` → `PRIVATE CAR COMP, SAOD & STP!H5` — EW of Pvivate car will be Flat 20% Payout
- **xlsx** `Reliance Broking Premier  FEB 26 Grid.xlsx` → `PRIVATE CAR COMP, SAOD & STP!H6` — Addon Bundle (Tyre / RTI) if Sourced, 2.5% Additional Payout Shall be offered
