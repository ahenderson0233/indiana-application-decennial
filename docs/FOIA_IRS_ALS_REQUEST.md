# IRS FOIA — Automated Lien System (ALS) Database Listing

**Prepared 2026-08-15 for the operator to submit.** This is the D13 (federal tax lien) acquisition
route found by Lane F discovery. It is a letter, not an endpoint — free since 2023, and it covers
**business liens only**, which is exactly this platform's target universe rather than a gap.

## Why this route

Federal tax liens (NFTLs) are perfected by filing with the **county recorder** under IC 36-2-11-25,
so the obvious route is 92 county recorders. Every one of those is gated — Doxpop paid tiers,
Fidlar Tapestry at $8.75/search, or Laredo per-county subscriptions; Fidlar's free Direct Search is
reCAPTCHA-gated and carries an explicit anti-data-mining notice. The ALS FOIA collapses all 92 into
one free national extract.

The IRS states, verbatim, on
`https://www.irs.gov/privacy-disclosure/automated-lien-system-database-listing`:

> *"Starting January 1, 2023, we'll no longer charge for FOIA requests seeking IRS Automated Lien
> System database listings."*

## Submit via — VERIFIED 2026-08-15

An earlier draft of this file gave `irs.gov/privacy-disclosure/foia-guidelines`, which **404s**.
The routes below were read off the IRS's own FOIA guidelines page rather than guessed.

**Online (fastest):** the IRS **FOIA Public Access Portal**
`https://foiapublicaccessportal.for.irs.gov/`

**By fax** (business taxpayer records): **877-891-6035**

**By post** (business taxpayer records):
> Internal Revenue Service
> GLDS Support Services
> Stop 93A
> Post Office Box 621506
> Atlanta, GA 30362

### What the IRS requires a request to contain

Quoted from their guidelines — the drafted text below already satisfies 1, 4 and 7; you supply
2, 3, 5 and 6:

1. *"State that the request is being made under the Freedom of Information Act"*
2. A **hand-written signature** (required when seeking business records protected by statute)
3. Identity verification — *"driver's license or a sworn or notarized statement"*
4. *"Identify or describe the records that are being sought as specifically as possible"*
5. *"The name and address of the requester"*
6. A commitment to pay applicable fees
7. Requester category — **commercial** applies here

Because 2 and 3 require your signature and identification, this is drafted for you to submit
rather than submitted on your behalf.

### What arrives

Confirmed on the IRS's ALS page: *"A standard listing of business liens extracted quarterly from
the IRS Automated Lien System database is available in pipe-delimited text format on compact disc
(CD)."* Fields are **Lien ID Number, TP ID Number, TP Name and Address, Lien Status**.

**Their own accuracy caveat, which must ride with the data into the app:** *"The data, therefore,
may be incomplete and, in some instances, inaccurate"* — the IRS recommends confirming against the
local filing jurisdiction for official purposes. So D13 is a LEAD generator, never a title claim.

---

## REQUEST TEXT — copy from here

> **Freedom of Information Act Request**
>
> This is a request under the Freedom of Information Act, 5 U.S.C. § 552.
>
> **Records requested.** I request the Automated Lien System (ALS) database listing of **Notices of
> Federal Tax Lien filed against business taxpayers** in the **State of Indiana**, for the most
> recent period available, and, if separately maintained, the four most recent quarterly listings.
>
> I request the records in **electronic form** (the standard pipe-delimited text extract), delivered
> by the customary medium for this listing.
>
> For each lien record, I request the standard ALS listing fields — **Lien ID Number, TP ID Number,
> TP Name and Address, and Lien Status** — together with any additional fields carried in the
> standard extract.
>
> **Scope note.** I am requesting only the **business** taxpayer listing. I am not requesting
> records of individual taxpayers.
>
> **Fees.** Per the IRS's published guidance for this listing — *"Starting January 1, 2023, we'll no
> longer charge for FOIA requests seeking IRS Automated Lien System database listings"* — I
> understand no fee applies. If any fee is nonetheless assessed, please contact me before incurring
> it.
>
> **Requester category.** Commercial.
>
> **Purpose.** The records will be used for commercial real-estate market research — identifying
> commercial properties that may become available for sale — as part of an internal energy
> development site-selection platform.
>
> Thank you for your assistance.
>
> [your name]
> [your address]
> [hand-written signature — required for business taxpayer records]

## — copy to here

---

## What happens next, and what it is worth

- **Effort:** ~1 hour to file. Expect **weeks to months** for a response; the media has historically
  arrived on CD, so budget for that annoyance.
- **On arrival:** ~0.5–1 day to write the loader. Same shape as the existing state-bulk loaders —
  `(lien_id, taxpayer_name, taxpayer_address, filing_office, filed_date, lien_status)` → filter to
  Indiana → match name/address to commercial parcels at `quality_mult` 0.6 (owner-keyed), and where
  an address is present, geocode and parcel-join by the strict Indiana method.
- **ALL COLUMNS still applies.** Whatever fields the extract actually carries get stored, not just
  the six above — the same rule that turned up eleven unasked-for signal columns in Lane D.
- **Register on arrival:** append a `registry_sources` row with the FOIA reference number as the
  endpoint, `endpoint_kind='foia_extract'`, and the loader path as `acquisition_method`.

## Related, NOT part of this request

`d10:state-tax-lien:in` (Indiana **state** tax warrants) is a different animal: county-**clerk**
judgment records with a statewide index (OJA INcite, 79 counties) behind a $600/yr individual or
$5,000/yr business subscription, or Doxpop resale from $38/mo. That is a procurement decision, not
a FOIA. Check the OJA agreement's redistribution clause before any purchase.
