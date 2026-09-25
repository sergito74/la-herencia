# La Herencia Constitution

## Core Principles

### I. SQL Server Is the System of Record
**Post-cutover (2026-09-25)**: SQL Server database `WC` is the **production database**. It is the sole system of record for La Herencia going forward. The Access system (`AdmLaHerenciaVer3.accdb` and related `.accdb` files, and the SQL Server database `LaHerencia` they link to via ODBC) is **frozen and deprecated**: it MUST NOT receive new data entry from this point forward, and MUST be preserved read-only as historical reference and audit trail. New application code, scripts, migrations, tests, and agents MUST use the existing SQL Server connection and verified tables, views, and queries against `WC`. Reading `LaHerencia` (never writing) remains permitted for narrow, explicitly justified verification purposes (e.g. one-off reconciliation scripts), following the same pattern established in feature 020.

### II. Real Data Protection Is Non-Negotiable
`WC`, now the production database, MUST be treated with the same care the official `LaHerencia` database received before the cutover: a verified backup MUST exist before any schema change, bulk migration, or risky write, and application code/scripts/tests/agents MUST NOT write to `LaHerencia` under any circumstance (it is frozen, not merely deprioritized). Ordinary, task-scoped feature writes to `WC` remain allowed without a new per-operation confirmation, same as before the cutover — what changes is the backup discipline around anything non-trivial. Automated tests SHOULD use mocks/fixtures; tests that write to `WC` MUST clearly identify that behavior and keep it bounded to test data that doesn't corrupt real production records. No development component may silently write to `LaHerencia`. Access files and data MUST NOT be altered or removed by development work — they remain the historical audit record of everything before the cutover. **Recommended but not yet established**: a separate, disposable working-copy database (restored from `WC`) for risky schema experiments and destructive testing, mirroring the role `WC` played relative to `LaHerencia` before the cutover — to be named and adopted when the next such need arises.

### III. Business Processes Before Raw Tables
Every user-facing module MUST represent a business process, not merely expose database tables. Screens MUST support the user's path from context to result: entity or account selection, filters, summary, detail, origin, and relevant documents. The web navigation MUST reflect administration, production, livestock health, treasury, accounts, sales, purchases, and reporting workflows.

### IV. Traceability and Explicit Financial Meaning
Financial and operational values MUST expose their meaning and origin. Interfaces and queries MUST distinguish debt, credit, balance, payment, collection, commitment, debit, credit, quantity, unit, date, currency, exchange rate, and due date. Records MUST remain traceable through real identifiers such as `IdContacto`, `IdOrigen`, document number, operation, account, campaign, lot, or establishment where available.

### V. Contract-First, Tested Integration
Each module MUST define and verify its SQL/API contract before UI implementation. Queries MUST be parameterized, bounded, and validated against the live schema. Changes MUST include the narrowest useful automated check: SQL read validation, API contract test, UI behavior test, or compilation check. A feature is not complete until its original behavior and relevant empty/error states are verified.

### VI. Specialist Collaboration and Domain Accuracy
SQL Server, web frontend, Python, integrated agro-management, agricultural production, livestock health, and financial direction agents MUST collaborate through explicit assumptions, schemas, formulas, and acceptance criteria. Domain agents define meaning and constraints; engineering agents implement and test them. Ambiguities MUST be recorded and resolved before they become hidden business rules.

### VII. Simplicity, Reviewability, and Reversible Change
Prefer the smallest implementation that satisfies the process and existing architecture. Avoid speculative abstractions and unrelated refactors. Every change MUST be reviewable in Git, preserve a clean build path, and be reversible. Generated artifacts, binaries, local databases, credentials, and temporary files MUST remain out of version control.

### VIII. Approved Migration Technology Stack
The migrated system MUST use Python for backend services, integrations, automation, data analysis, and domain logic; SQL Server for persistence and authoritative data; Next.js with TypeScript for the web application; Tailwind CSS for styling; and TanStack Query for client-side server-state fetching, caching, synchronization, and invalidation. New web functionality MUST NOT introduce ASP.NET Core, JavaScript-only modules, another frontend framework, or another client-state data-fetching library without an approved amendment to this constitution.

## Data and Security Constraints

- The backend uses Python and exposes documented, typed API contracts for the Next.js frontend.
- The frontend uses Next.js, TypeScript, and Tailwind CSS; TanStack Query manages server state and API synchronization.
- SQL Server remains the authoritative persistence layer and is accessed through the Python backend, not directly from the browser.
- Read endpoints MUST use allowlisted objects, parameterized filters, row limits, and pagination where appropriate.
- No endpoint may accept arbitrary SQL from the browser.
- Credentials, tokens, connection secrets, and personal data MUST NOT be committed or logged.
- Backups MUST be stored outside source control and their verification result recorded before authorized writes.
- Production, financial, and health indicators MUST identify their period, units, currency, and calculation source.

## Development Workflow and Quality Gates

For each bounded migration slice:

1. Releve the existing schema, data contract, and current behavior.
2. Define the business outcome and acceptance criteria with the relevant domain agents.
3. Specify, clarify, plan, and break down the work using Spec Kit.
4. Implement against `WC` (production, post-2026-09-25 cutover), following the feature contract; the module may read or write `WC` as specified, with a verified backup before any non-trivial schema change or bulk write.
5. Add focused tests, compile checks, and UI/API verification without writing to `LaHerencia` or altering Access files (frozen, historical reference only).
6. Review the diff and confirm no real database files, secrets, or generated outputs were added.
7. Any future migration/cutover to a different production system would again be a separately approved activity with a verified backup, reconciliation plan, rollback, and auditability — the same discipline used for the 2026-09-25 cutover.

The initial migration target was a read-only web module integrating accounts current, treasury, purchases, operations, and financial navigation. That historical starting point does not restrict later feature specs from defining writes to `WC`.

## Governance

This constitution supersedes informal practices for the La Herencia migration. Every specification, plan, task list, implementation, and convergence review MUST check compliance with these principles. Any exception requires a written reason, explicit user approval, risk assessment, and rollback plan. Amendments MUST update this file, its version, and the affected workflow artifacts. The `.github/agents/README.md` and `.specify/README.md` provide supporting guidance but do not override this constitution.

**Version**: 1.4.0 | **Ratified**: 2026-09-15 | **Last Amended**: 2026-09-25

**Amendment 1.4.0 (2026-09-25) — Production cutover**: Sergio approved the production cutover. `WC` is no longer a disposable development working copy: it is now the production database and the sole system of record. The Access system (`.accdb` files and the `LaHerencia` SQL Server database they link to) is frozen — no new data entry, preserved read-only as historical/audit reference. Principles I and II rewritten accordingly: the backup-before-risky-write discipline that previously protected `LaHerencia` now applies to `WC`. Verified before the cutover: of 139 tables shared between `WC` and `LaHerencia`, only 5 had row-count differences, all explained (one real invoice loaded only in `WC`, two empty/junk Access records, and two tables/one category that are outputs of our own migration scripts, reproducible) — no real business data was at risk of loss. 35 tables exist only in `WC` (all our own feature schema, 010-020) and were not ported to `LaHerencia`, which stays frozen as-is at the moment of cutover.

**Amendment 1.3.0 (2026-09-22)**: Principles I and II clarify that `WC` is the mutable development database, that normal task-scoped development writes there are allowed, and that the official `LaHerencia` database stays unchanged until a separately approved cutover. Access files still used operationally are protected from modification/removal during development. This corrects the previous wording that incorrectly required per-operation write approval even for `WC`.

**Amendment 1.2.0 (2026-09-22)**: Principles I and II named `WC` as the working copy and `LaHerencia` as the protected official database.
