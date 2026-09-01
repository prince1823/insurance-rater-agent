# Decision trace — `pvt-car-satp-go-digit.pdf`

- **Status:** `resolved`
- **Insurer:** Go Digit  (grid: `Large Insurance Brokers Mar'26 - Shared.xlsx`)
- **Policy type:** standalone_tp  ·  **Business type:** renewal
- **OD commission:** _not applicable_
- **TP commission:** 29.5% on TP / net premium
- **Confidence:** high — all driver facts extracted with high confidence and matched grid keys exactly

## Extracted facts

| Fact | Value | Page | Confidence |
|---|---|---|---|
| insurer | Go Digit General Insurance Ltd. | 1 | 0.99 |
| previous insurer | Go Digit General Insurance Limited | 2 | 0.97 |
| business type | renewal |  |  |
| policy type | standalone_tp |  |  |
| make | HYUNDAI | 1 | 0.99 |
| model | SANTRO NEW/1.1MT CORPORATE | 1 | 0.95 |
| fuel | petrol | 1 | 0.98 |
| engine cc | 1086 | 1 | 0.97 |
| RTO code | UP-78 | 1 | 0.92 |
| RTO location | Kanpur Nagar,UTTAR PRADESH | 1 | 0.95 |
| manufacture year | None | 1 | 0.1 |
| registration year | 2019 | 1 | 0.95 |
| vehicle age (years) | 7 |  |  |
| NCB % | None |  | 0.0 |
| zero depreciation cover | False |  | 0.6 |
| OD premium | None |  | 0.0 |
| TP premium | 3416 | 2 | 0.95 |
| net premium | 3466 | 2 | 0.9 |
| total premium (incl GST) | 4089.88 | 2 | 0.9 |

## Ordered decision trace

### 1. Map RTO code to Go Digit TP cluster

RTO UP-78 -> TP cluster 'UP_Bad' via the '4W  RTO' sheet (4WTP column).

- `pvt-car-satp-go-digit.pdf` → `page 1` = `UP-78`  
  _RTO Location Kanpur Nagar,UTTAR PRADESH; Registration UP78FZ1372_
- `Large Insurance Brokers Mar'26 - Shared.xlsx` → `4W  RTO!C1609` = `UP_Bad`

### 2. Select Cluster x Segment x Age row

Cluster 'UP_Bad', segment 'Petrol>1000' (fuel petrol, 1086 cc), age band 'All' (vehicle age 7) -> row 293.

- `pvt-car-satp-go-digit.pdf` → `page 1` = `1086`  
  _Cubic Capacity 1086 CC_
- `pvt-car-satp-go-digit.pdf` → `policy schedule`
- `Large Insurance Brokers Mar'26 - Shared.xlsx` → `4W SATP!E293` = `0.295`

### 3. Return TP commission

'Max CD2' = 0.295 -> 29.5% on the TP (net) premium. OD is not applicable for a stand-alone TP policy.

- `Large Insurance Brokers Mar'26 - Shared.xlsx` → `4W SATP!E293` = `0.295`

## All citations

- **policy** `pvt-car-satp-go-digit.pdf` → `page 1` = `UP-78` — RTO Location Kanpur Nagar,UTTAR PRADESH; Registration UP78FZ1372
- **xlsx** `Large Insurance Brokers Mar'26 - Shared.xlsx` → `4W  RTO!C1609` = `UP_Bad`
- **policy** `pvt-car-satp-go-digit.pdf` → `policy schedule`
- **xlsx** `Large Insurance Brokers Mar'26 - Shared.xlsx` → `4W SATP!E293` = `0.295`
