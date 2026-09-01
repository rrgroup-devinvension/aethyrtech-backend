# AI Agent Root Instructions

You are an advanced AI Developer operating in this Django Backend repository. 
Before writing any code or proposing any solutions, you MUST read the specific documentation files below that match the user's task.

## 1. Core Architecture (MANDATORY FOR ALL API & DB TASKS)
If you are building ViewSets, Models, or writing Database Queries, **read**:
- `docs/ai/ARCHITECTURE.md`
*(Contains critical rules on `BaseViewSet`, custom pagination like `no_page=true`, multi-database routing, and MySQL-specific quirks.)*

## 2. Existing Functionality (MANDATORY FOR NEW FEATURES)
If the user asks you to build a new feature (like a file processor, async task, or API endpoint), **read**:
- `docs/ai/FEATURES.md`
*(Contains a directory of our existing scalable solutions, like our Celery-based Chunked Data Imports. Reuse existing systems rather than building from scratch.)*

## 3. Code Standards (MANDATORY FOR ALL TASKS)
If you are writing Python code, **read**:
- `docs/ai/STYLEGUIDE.md`
*(Contains strict rules on Type Hinting, Pandas DataFrame processing, and standard naming conventions.)*

---
**Agent Directive:** 
When the user gives you a task, do not start coding immediately. First, use your file-reading tools to open and read the relevant files listed above. Once you have read them, state: *"I have reviewed the backend architecture rules for this task,"* and then proceed.
