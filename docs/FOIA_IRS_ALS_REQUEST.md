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

## Submit via

**IRS FOIA Public Access Portal** — `https://www.irs.gov/privacy-disclosure/foia-guidelines`
(the portal route is fastest; the same text works as a mailed letter to the IRS FOIA office).

You will need to supply your own identity and contact details, which is why this is drafted for
you to submit rather than submitted on your behalf.

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
> For each lien record, I request the standard ALS listing fields, including but not limited to:
> serial/lien identification number, taxpayer name, taxpayer address, filing office, date of filing,
> and lien status.
>
> **Scope note.** I am requesting only the **business** taxpayer listing. I am not requesting
> records of individual taxpayers.
>
> **Fees.** Per the IRS's published guidance for this listing — *"Starting January 1, 2023, we'll no
> longer charge for FOIA requests seeking IRS Automated Lien System database listings"* — I
> understand no fee applies. If any fee is nonetheless assessed, please contact me before incurring
> it.
>
> **Purpose.** The records will be used for commercial real-estate market research — identifying
> commercial properties that may become available for sale — as part of an internal energy
> development site-selection platform.
>
> Thank you for your assistance.

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
