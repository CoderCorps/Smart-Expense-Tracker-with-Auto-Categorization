# Smart Expense Tracker - Data Model

## Architecture Overview

CSV Upload ───┐
a              │
PDF Upload ───┼──→ Standard Transaction Format → Database
              │
Manual Entry ─┘
                        ↓
              Categorization Service
                        ↓
                 Analytics APIs

Each source produces a normalized transaction record before it reaches the database. That shared model is used by upload parsers, categorization logic, manual CRUD endpoints, and dashboard analytics. This keeps Person B, C, and D working against the same contract instead of separate CSV/PDF tables.

## User Model

The User model stores each person’s authentication and account metadata.

Fields:
- id: Primary key for the user.
- email: Unique login identifier.
- full_name: Display name for the account.
- hashed_password: Password hash used for authentication.
- created_at: UTC timestamp when the user was created.

Relationships:
- One user can have many transactions.

## Category Model

The Category table holds the shared category vocabulary used across the app.

Fields:
- id: Primary key.
- name: Unique category name such as Food & Dining or Travel & Transport.
- description: Optional human-readable explanation for a category.
- is_default: Whether this category is part of the seeded default list.
- created_at: UTC timestamp when the category was created.

Relationships:
- One category can be assigned to many transactions.

## Transaction Model

The Transaction model is the common canonical record for all income and expense data.

Fields:
- id: Primary key.
- user_id: Foreign key to the owning user.
- date: Transaction date.
- description: Cleaned description shown in the app.
- raw_description: Original source text before cleaning. Stored for debugging and future ML training.
- amount: Monetary value stored as a positive number. Direction is tracked by type.
- type: Transaction direction: spend or earn.
- category_id: Foreign key to the category, or null if still uncategorized.
- category_source: How the category was assigned: rule_based, ml, manual_correction, or uncategorized.
- source: Where the transaction came from: manual, csv, or pdf.
- created_at: UTC timestamp when the record was inserted.

Important rule:
- amount is always stored as a positive magnitude.
- type tells whether it was a spend or earn.
- This lets CSV, PDF, and manual data share one storage format.

## Relationships

User → Transactions
- Each transaction belongs to exactly one user.
- A user can have many transactions.

Category → Transactions
- Each transaction may belong to one category.
- A category can have many transactions.
- If no category is assigned yet, category_id is null and category_source = uncategorized.

## Transaction Sources

The source field tells where the transaction came from:
- manual: created by a user manually in the app.
- csv: imported from a CSV bank/export file.
- pdf: parsed from a PDF bank statement.

All sources share the same transaction table and schema, which avoids duplicate tables and keeps analytics and categorization logic simple.

## Category Sources

The category_source field tells how the category was assigned:
- rule_based: assigned by the keyword-based categorizer.
- ml: assigned by a future ML classifier.
- manual_correction: the user corrected a previous category assignment; this is valuable training data.
- uncategorized: no category assignment exists yet.

This field is important for training and auditability.

## Data Flow

Person B (Upload & Parsing)
- Parses CSV/PDF rows.
- Maps source columns to the shared transaction schema.
- Saves each row as a Transaction using the same model.

Person C (Categorization)
- Reads transactions and assigns category_id.
- Records whether the category came from rule-based logic, ML, or a user correction.
- Uses manual_correction rows as future training examples.

Person D (Dashboard & Analytics)
- Queries transactions with the standard fields.
- Aggregates by date, category, type, and source.
- Produces summaries and insights without needing to know where each transaction originated.

This shared contract ensures all modules can work independently without schema conflicts.
