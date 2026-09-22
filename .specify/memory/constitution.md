# La Herencia Constitution

## Core Principles

### I. SQL Server Is the System of Record
SQL Server database `WC` — a full working copy of `LaHerencia` — is the only database new code, scripts, migrations, tests, or agents may write to. `LaHerencia` is the protected original: read-only, never written to by application code. New code MUST use the existing SQL Server connection and verified tables, views, and queries against `WC`. Access databases, `.accdb` files, local queries, DataSets, TableAdapters, and duplicated data stores are obsolete and MUST NOT be used for new functionality.

### II. Real Data Protection Is Non-Negotiable
`LaHerencia` contains the protected original production data and MUST NEVER receive `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, `ALTER`, `DROP`, or any side-effecting procedure from application code, scripts, tests, migrations, or agents, under any circumstance. `WC` is a full working copy and the only database authorized writes may target; even there, no feature, script, test, migration, or agent may write without explicit user authorization and a recent full backup of `WC` verified with SQL Server. Tests MUST NOT write to either database unless explicitly authorized against `WC`.

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
4. Implement the read path first and validate it against real data without writes.
5. Add focused tests, compile checks, and UI/API verification.
6. Review the diff and confirm no real database files, secrets, or generated outputs were added.
7. Only after explicit authorization, create a verified backup and design the write path with rollback and auditability.

The first implementation target for the migration is a read-only web module that integrates accounts current, treasury, purchases, operations, and financial navigation using existing SQL Server views and tables.

## Governance

This constitution supersedes informal practices for the La Herencia migration. Every specification, plan, task list, implementation, and convergence review MUST check compliance with these principles. Any exception requires a written reason, explicit user approval, risk assessment, and rollback plan. Amendments MUST update this file, its version, and the affected workflow artifacts. The `.github/agents/README.md` and `.specify/README.md` provide supporting guidance but do not override this constitution.

**Version**: 1.2.0 | **Ratified**: 2026-09-15 | **Last Amended**: 2026-09-22

**Amendment 1.2.0 (2026-09-22)**: Principles I and II amended to name `WC` explicitly as the working copy that authorized writes target, and `LaHerencia` explicitly as the protected, never-written-to original. This codifies a practice already in effect since 010-remitos (and consistently documented in every module's `FR-0xx` "toda escritura va exclusivamente contra `WC`") that the original text of v1.1.0 did not name, flagged as a CRITICAL finding (C1) by `/speckit-analyze` while planning 011-ordenes-trabajo. No behavioral change: this amendment brings the written principle in line with practice already followed by every shipped module.
