# What is out of scope

The anti-scope-creep ledger. This repo's value is being small, complete, and
honest about what it is and is not.

## Hard boundaries (these protect the honest-scope framing)

- **No proprietary material.** No real vendor assay format, no real clinical
  knowledge base, no patient data, no validated-system code or parameters. The
  three "vendor" schemas are synthetic and loosely inspired by published field
  conventions; the knowledge table is a handful of illustrative rows.
- **Not a validated system and not regulatory advice.** This demonstrates the
  *pattern* behind 21 CFR Part 11 electronic records / signatures. It is not a
  Part 11-validated implementation, has not been through CSV/IQ/OQ/PQ, and must
  not be used for clinical care or submission.
- **Not cryptographic signing.** The "signature" is a content-bound, hash-chained
  record — it shows the binding-and-tamper-evidence pattern. A production system
  would use a real PKI / certificate authority and identity provider.

## Default out-of-scope items

- **Real CDx vendor integrations** (Roche / Thermo / Guardant / Foundation /
  Agilent SDKs or formats). Only synthetic, abstracted schemas are modeled.
- **A real clinical knowledge base** (e.g. OncoKB, CIViC). The therapy-implication
  table is illustrative and intentionally tiny.
- **Persistence / multi-user workflow** (database, web UI, role-based access,
  identity provider). The substrate provides the audit foundation; the portrait
  does not re-implement an LIMS.
- **Cryptographic e-signatures / timestamping authority**. Out of scope; the
  hash-chain pattern stands in for the binding-and-tamper-evidence property.
- **Statistical/benchmark claims.** There are none to make; this is a
  reporting-and-controls portrait, not a modeling result.

## How to add an item

Open a PR that adds the item here with a one-sentence reason and a link to the
proposing issue. The friction is intentional.
