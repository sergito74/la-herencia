# La Herencia Constitution

## Core Principles

### I. SQL Server Is the System of Record
SQL Server database `WC` is the mutable development and validation working copy. New application code, scripts, migrations, tests, and agents MUST use the existing SQL Server connection and verified tables, views, and queries against `WC`. The official `LaHerencia` database is protected and MUST remain unchanged throughout development. Connecting the completed system to the official database is a separate cutover decision requiring explicit user approval and a reviewed migration/reconciliation and backup plan. Access databases and `.accdb` files are the current operational legacy system and MUST be preserved unchanged while it remains in use; they MUST NOT be used as persistence for new functionality.

### II. Real Data Protection Is Non-Negotiable
During development, the official `LaHerencia` database MUST NOT receive writes, schema changes, migrations, or side-effecting procedures from application code, scripts, tests, or agents. The development application MUST target `WC`; its intended writes to `WC` are allowed as part of development and do not require a new per-operation confirmation when they are within the user's task. Automated tests SHOULD use mocks/fixtures; tests that write to `WC` MUST clearly identify that behavior and keep it bounded to test data. No development component may silently fall back to `LaHerencia`. The future production cutover is outside this development authorization and requires explicit approval. Access files and data used by the current system MUST NOT be altered or removed by development work.

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
4. Implement against `WC`, following the feature contract; the module may read or write `WC` as specified.
5. Add focused tests, compile checks, and UI/API verification without touching the official database or altering Access files.
6. Review the diff and confirm no real database files, secrets, or generated outputs were added.
7. Treat migration/cutover to the official database as a separately approved activity with a verified backup, reconciliation plan, rollback, and auditability.

The initial migration target was a read-only web module integrating accounts current, treasury, purchases, operations, and financial navigation. That historical starting point does not restrict later feature specs from defining writes to `WC`.

## Governance

This constitution supersedes informal practices for the La Herencia migration. Every specification, plan, task list, implementation, and convergence review MUST check compliance with these principles. Any exception requires a written reason, explicit user approval, risk assessment, and rollback plan. Amendments MUST update this file, its version, and the affected workflow artifacts. The `.github/agents/README.md` and `.specify/README.md` provide supporting guidance but do not override this constitution.

**Version**: 1.3.0 | **Ratified**: 2026-09-15 | **Last Amended**: 2026-09-22

**Amendment 1.3.0 (2026-09-22)**: Principles I and II clarify that `WC` is the mutable development database, that normal task-scoped development writes there are allowed, and that the official `LaHerencia` database stays unchanged until a separately approved cutover. Access files still used operationally are protected from modification/removal during development. This corrects the previous wording that incorrectly required per-operation write approval even for `WC`.

**Amendment 1.2.0 (2026-09-22)**: Principles I and II named `WC` as the working copy and `LaHerencia` as the protected official database.
