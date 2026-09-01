# Insurance Rater Agent Challenge

Build an explainable agent that reads a motor policy, finds the applicable broker commission percentage in the supplied insurer files, and cites exactly how it reached the answer.

There is no deadline and no prescribed stack. Publish your work whenever it is ready and share both the hosted application and the source-code repository when you apply to Vaatun.

## What you are calculating

When a broker places and services an eligible policy, the insurer may pay the broker a percentage called **brokerage** or **commission**. A **commission grid**, also called a brokerage grid or rate card, is the insurer's conditional lookup table for deciding that percentage.

This challenge asks you to find the applicable commission percentage. You are **not** calculating the price charged to the customer.

Motor policies split cover and premium into components:

- **Own Damage (OD)** covers damage to the insured vehicle, such as accident damage, theft or fire.
- **Third Party (TP)** covers legal liability for injury or property damage caused to somebody else.
- A **comprehensive/package policy** contains OD and TP components.
- A **stand-alone TP policy** contains TP only. Its OD rate is _not applicable_, not zero.

Commission grids may publish a separate percentage for OD and TP. Apply each rate only to its relevant premium component. This challenge requires the percentage rates; calculating rupee commission amounts is optional.

### Terms used in the source files

- **RTO:** Regional Transport Office. The vehicle-registration code is a geographic key; an insurer may group several RTOs into its own zone or cluster.
- **CC:** cubic centimetres, the engine's capacity. Grids commonly group CC values into bands.
- **NCB:** No Claim Bonus, a claim-free discount on the OD premium. Some grids use the NCB percentage as a lookup condition.
- **Business type:** When a policy names the same insurer as both the current and previous insurer, classify it as a renewal, not as new business or rollover/ported business.
- **Premium slab:** a range bucket for a premium amount.
- **Vehicle segment:** an insurer-defined bucket based on model, fuel, engine capacity, vehicle age or a combination of those facts.
- **`raters/`:** the supplied folder containing commission-grid files. It is a directory name, not executable rating software.

### Illustrative lookup

This completed example is deliberately fictional; none of its values are answers from the supplied files.

1. Read the fictional policy facts: comprehensive cover, petrol hatchback, registration code `HR-26`, 1,197 cc, 20% NCB and ₹14,000 OD premium. Cite `fictional-policy.pdf · page 1`.
2. Follow the fictional mapping tables: `HR-26` maps to `Zone A`, and the hatchback maps to `Segment H1`. Cite `fictional-grid.xlsx · Geography!B14:C14` and `Vehicles!D8:F8`.
3. Follow every dimension required by this grid: Zone A, Segment H1, petrol, the 1,001–1,500 cc band and the ₹10,001–₹20,000 premium slab. The matching row returns fictional rates of OD `12%` and TP `2%`. Cite `Rates!G22:H22`.
4. Check the applicable footnote. `Rates!A27:H27` excludes diesel vehicles only, so this petrol example remains resolved.
5. Return OD `12%` and TP `2%`, attaching the policy page, both mapping ranges, rate cells and footnote to the decisions they support.

## The problem

Indian insurer commission grids arrive as spreadsheets, PDFs, circulars, and images. Their lookup rules vary by insurer and may depend on RTO or geographic zone, vehicle make and model, fuel, engine capacity, vehicle age, policy type, NCB, premium slabs, and footnotes.

Given a motor policy PDF and the supplied `raters/` corpus, your agent must:

1. Extract the policy facts that affect brokerage.
2. Select and traverse the relevant commission grid deterministically.
3. Return the expected OD and TP brokerage rates.
4. Cite the exact source file and sheet, cell, row, or PDF page used.
5. Explain every transformation between the policy and the result.
6. Refuse to invent an answer when the supplied evidence is incomplete, ambiguous, declined, or outside the grid's coverage.
7. Expose the workflow through a deployed browser frontend where a reviewer can upload a motor policy PDF and receive the result. During review, Vaatun will upload additional policy PDFs that are not included in the supplied samples.
8. Keep previous runs, including uploaded policy PDFs and completed analyses, available after a reviewer refreshes or reopens the browser app, signs out and back in when authentication is used, or the application restarts or redeploys.

LLMs are welcome for document extraction. Grid resolution must be reproducible, testable, and explainable rather than a black-box LLM answer.

## Input

- A motor policy PDF uploaded through the browser frontend.
- The supplied `raters/` directory of commission-grid files. You may package these files with the deployed application.

A CLI or local-file-path interface may be included for development, but it does not replace the browser upload flow. Supporting policy URLs or uploading new commission-grid files is optional.

## Hosted product requirements

The hosted application must:

- Accept additional motor policy PDFs beyond the supplied samples. During review, Vaatun will upload policy PDFs that applicants have not received. A solution that works only with the supplied sample policies does not meet this requirement.
- Show the resulting status, rates, citations, confidence, and decision trace in the browser.
- Keep previous runs, including the uploaded PDFs and completed analyses, accessible from the frontend after a browser refresh or close and reopen. If the application has authentication, the same history must remain available after signing out and back in. It must also survive application, server, or container restarts and redeployments. Container-local or other ephemeral storage alone does not meet this requirement.
- Include a README that states where uploaded PDFs and completed analyses are stored and explains how previous runs remain available across those events.

## Output

Return a structured result containing:

- Extracted insurer, previous insurer and business type where relevant, make/model, fuel, RTO, engine capacity, manufacture year or vehicle age, policy type, NCB, and premium breakup.
- A `resolved`, `unsupported`, or `ambiguous` status.
- Separate OD and TP commission rates with explicit applicability. For a stand-alone TP policy, report OD as not applicable rather than `0%`.
- Granular citations for policy facts, mapping steps, and the final rate lookup. For XLSX, cite the file, sheet and cell/range; for PDF, cite the file, page and table row.
- A confidence level with a short explanation.
- An ordered, human-readable decision trace.
- A clear unsupported or ambiguous result when the evidence cannot determine a rate.

Your agent may ask a clarifying question when a required policy fact is genuinely ambiguous.

## Test corpus

Run the agent against all four synthetic policy fixtures in `sample-policies/`:

1. `pvt-car-comprehensive-hdfc-ergo.pdf`
2. `pvt-car-satp-go-digit.pdf`
3. `pvt-car-comprehensive-reliance.pdf`
4. `pvt-car-satp-tata-aig.pdf`

The policies have been de-identified while preserving the facts required for rate resolution. Treat the source rate cards as authoritative; do not hard-code answers for these four files.

## What to submit

Your submission must include:

- A working browser frontend deployed to a hosted URL that the Vaatun team can open and use.
- A policy-PDF upload flow that works with additional files beyond the supplied samples.
- Previous runs and uploaded files available after browser refreshes, closing and reopening the app, signing out and back in when authentication is used, and application restarts or redeployments.
- A source-code repository.
- Setup, run, and deployment instructions.
- Automated tests for the rating logic and storage boundary.
- Structured outputs and decision traces for all four policies.
- A short note on architecture, assumptions, failure modes, and trade-offs.

Submissions that are not deployed, cannot process policy PDFs beyond the supplied samples, or lose previous runs after a refresh, a sign-out and sign-in when authentication is used, a restart, or a redeployment will be treated as incomplete.

Email both the hosted application link and the source-code repository to **[careers@vaatun.com](mailto:careers@vaatun.com?subject=Insurance%20Rater%20Agent%20Challenge%20Submission)** with the subject **Insurance Rater Agent Challenge Submission**. Include direct links to the four decision traces if they are not easy to find in the repository. If the hosted application requires sign-in, a password, an access code, or any other credentials, share them in the email or through another communication channel agreed with the team.

## Evaluation

The hosted frontend, additional policy upload, and saved-run history requirements above are baseline acceptance criteria. Only submissions that meet them proceed to weighted evaluation.

- **Accuracy, 40%:** correct extraction and rate, or the correct evidence-backed refusal.
- **Traceability, 25%:** inspectable transformations and granular source citations.
- **Resilience, 20%:** missing fields, exclusions, footnotes, ambiguity, and unsupported segments.
- **Engineering, 15%:** readable code, useful tests, sensible boundaries, and clear documentation.

The strongest submission is not necessarily the one that always returns a number. Knowing when the evidence cannot support an answer is part of the problem.

## Privacy note

The supplied policies are metadata-clean synthetic fixtures. Customer names, contact details, addresses, policy identifiers, vehicle-registration suffixes, chassis and engine identifiers, and related personal fields have been replaced. City and RTO-level context, vehicle rating facts, policy type, NCB, and premium figures have deliberately been retained so the brokerage lookup remains solvable.
