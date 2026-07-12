# error-notification

## Purpose

Track pipeline progress and failures on the `Article` row and surface them to the dashboard user via toast notifications, a persistent failure banner, and a per-step progress view. This ensures a user always learns which pipeline step failed and why — including 3rd-party API failures (e.g. authentication) that occur before any article content exists.

## Requirements

### Requirement: Pipeline progress tracked on the Article row
The `full` pipeline SHALL track per-step progress on the `Article` row using a `pipeline_progress` field that records each step as `done`, `failed`, or `pending` for the steps: research, brief, draft, fact_check, seo, quality_gates. An `Article` row SHALL be created at the start of the run (before research) so that a failure in any step — including step 1 (keyword research) — is recorded on the article.

#### Scenario: Run starts
- **WHEN** the `full` pipeline begins for a keyword
- **THEN** an `Article` row SHALL be created with `status` indicating the run has started, and `pipeline_progress` with all six steps set to `pending`

#### Scenario: A step completes
- **WHEN** a pipeline step (e.g. research) completes successfully
- **THEN** `pipeline_progress[step]` SHALL be set to `done` and `status` SHALL advance to reflect the next step

#### Scenario: Run completes
- **WHEN** all steps finish without error
- **THEN** the `Article` SHALL reflect the completed pipeline state with all steps `done`

#### Scenario: Failure before content exists
- **WHEN** keyword research fails before any article content has been generated
- **THEN** the failure SHALL still be recorded on the `Article` row, because the row was created at run start

### Requirement: Failure recorded with a human-readable note
On failure, the `Article` row SHALL have `status == "failed"`, `pipeline_progress[failed_step]` set to `failed`, and `pipeline_error` set to a human-readable string produced by grouping the exception into common types. The grouping SHALL cover at minimum: API authentication failure, API rate limit, API timeout, API connection failure, database error, and configuration error; other exceptions SHALL fall back to a generic message including the exception's string representation.

#### Scenario: API authentication error
- **WHEN** the failure is an `APIAuthenticationError` (possibly wrapped by a `ProcessingError`)
- **THEN** `pipeline_error` SHALL indicate API authentication failure and mention checking API keys in `.env`, and `status` SHALL be `failed`

#### Scenario: Wrapped error is unwrapped for grouping
- **WHEN** the failure is a `ProcessingError` whose cause (`__cause__`) is an `APIAuthenticationError`
- **THEN** the grouping SHALL use the cause and produce the API authentication message

#### Scenario: Unknown exception falls back
- **WHEN** the failure does not match any known type
- **THEN** `pipeline_error` SHALL be a generic message that includes `str(exception)`

### Requirement: Failed articles surfaced as toast notifications
The dashboard SHALL surface `Article` rows with `status == "failed"` to the user as a Streamlit toast (`st.toast`) containing the article's `pipeline_error`. The toast SHALL appear on the next dashboard render after a failed article is detected.

#### Scenario: Failed article produces a toast
- **WHEN** the dashboard reads an `Article` with `status == "failed"`
- **THEN** a toast SHALL be displayed containing that article's `pipeline_error`

#### Scenario: Existing inline alerts preserved
- **WHEN** a toast is shown for a failed article
- **THEN** any pre-existing inline `st.error`/`st.warning`/`st.info` alerts SHALL remain unchanged in behavior and placement

### Requirement: Progress bar and per-step status in the UI
The dashboard SHALL display, for in-progress and recently run articles, a progress bar reflecting the fraction of pipeline steps marked `done`, and a per-step list showing each step's status (`done`/`failed`/`pending`) read from `pipeline_progress`.

#### Scenario: Progress bar reflects completed steps
- **WHEN** an article has 3 of 6 steps marked `done` and the rest `pending`
- **THEN** the progress bar SHALL reflect half (3/6) progress

#### Scenario: Per-step list shows failure
- **WHEN** an article has `pipeline_progress` with `research == "done"` and `brief == "failed"`
- **THEN** the step list SHALL show research as done and brief as failed
