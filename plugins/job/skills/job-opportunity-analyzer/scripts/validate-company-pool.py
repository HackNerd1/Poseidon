#!/usr/bin/env python3
"""Validate job-opportunity-analyzer sample assets with deterministic checks.

Purpose:
- Provide a stable local check for the city sample JSON and report sample.
- Catch missing entity fields, invalid enum values, broken company/source
  references, and malformed date strings with precise locations.

Inputs:
- --schema: optional path to `company-pool.schema.json`
- --sample: optional path to `<city>-company-pool.sample.json`
- --report: optional path to `<city>-<position>-report.sample.md`

Outputs:
- Exit 0 when all checks pass.
- Exit 1 with concrete file/index/field errors when any deterministic rule fails.

Non-goals:
- No network access.
- No open-ended reasoning or ranking.
- No full JSON Schema engine. The repo does not currently carry a JSON Schema
  dependency, so this script keeps a small deterministic rule set that is easy
  to maintain and produces targeted errors.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable


DATE_FIELDS_BY_ENTITY = {
    "sample": {"generated_at"},
    "source_ref": {"observed_at"},
    "company": {"last_verified"},
    "sentiment": {"observed_at"},
}

REQUIRED_REPORT_SECTIONS = (
    "## Analysis Scope",
    "## Executive Summary",
    "## Opportunity Table",
    "## Strategy Recommendations",
    "## Market Summary",
    "## Overall Assessment",
    "## Fact Sources",
    "## Missing Data And Exceptions",
)

REQUIRED_SCOPE_LINES = (
    "- `location`:",
    "- `position`:",
)

SOURCE_REF_PATTERN = re.compile(r"\[(src-[a-z0-9-]+)\]")
FACT_SOURCE_LINE_PATTERN = re.compile(
    r"^- \[(src-[a-z0-9-]+)\] ([a-z_]+) \| .+ \| observed: ([0-9]{4}-[0-9]{2}-[0-9]{2}) \| .+$",
    re.MULTILINE,
)


def default_paths() -> tuple[Path, Path, Path]:
    """Resolve default schema, sample, and report paths relative to this script."""
    root = Path(__file__).resolve().parent.parent
    return (
        root / "assets" / "company-pool.schema.json",
        root / "assets" / "hangzhou-company-pool.sample.json",
        root / "assets" / "hangzhou-frontend-report.sample.md",
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for deterministic local validation."""
    default_schema, default_sample, default_report = default_paths()
    parser = argparse.ArgumentParser(
        description=(
            "Validate the local company-pool sample and report sample with "
            "deterministic checks only. This script does not fetch data or "
            "perform recommendation logic."
        )
    )
    parser.add_argument(
        "--schema",
        default=str(default_schema),
        help="Path to the local company-pool schema JSON file.",
    )
    parser.add_argument(
        "--sample",
        default=str(default_sample),
        help="Path to the local city sample JSON file.",
    )
    parser.add_argument(
        "--report",
        default=str(default_report),
        help="Path to the local sample report markdown file.",
    )
    return parser.parse_args()


def load_json(path: Path) -> object:
    """Load UTF-8 JSON from disk and raise a readable error on failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def load_text(path: Path) -> str:
    """Load UTF-8 text from disk and raise a readable error on failure."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Missing file: {path}") from exc


def ensure_dict(value: object, label: str) -> dict:
    """Ensure a loaded JSON document is an object."""
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return value


def ensure_list(
    value: object,
    path: str,
    errors: list[str],
    *,
    file_name: str,
) -> list[dict]:
    """Ensure a field is a list of objects and report precise failures."""
    if not isinstance(value, list):
        errors.append(f"{file_name}:{path} must be an array.")
        return []

    normalized: list[dict] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{file_name}:{path}[{index}] must be an object.")
            continue
        normalized.append(item)
    return normalized


def add_error(errors: list[str], file_name: str, path: str, reason: str) -> None:
    """Add a stable error string with file and field location."""
    errors.append(f"{file_name}:{path} {reason}")


def parse_iso_date(value: str) -> bool:
    """Return True when the string is a strict YYYY-MM-DD date."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") == value
    except ValueError:
        return False


def require_non_empty_string(
    value: object,
    *,
    file_name: str,
    path: str,
    errors: list[str],
) -> str | None:
    """Validate that a field is a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        add_error(errors, file_name, path, "must be a non-empty string.")
        return None
    return value.strip()


def require_string_list(
    value: object,
    *,
    file_name: str,
    path: str,
    errors: list[str],
    min_items: int = 0,
) -> list[str]:
    """Validate that a field is a list of non-empty strings."""
    if not isinstance(value, list):
        add_error(errors, file_name, path, "must be an array of strings.")
        return []

    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            add_error(
                errors,
                file_name,
                f"{path}[{index}]",
                "must be a non-empty string.",
            )
            continue
        normalized.append(item.strip())

    if len(normalized) < min_items:
        add_error(errors, file_name, path, f"must contain at least {min_items} item(s).")
    return normalized


def require_enum(
    value: object,
    *,
    file_name: str,
    path: str,
    allowed: Iterable[str],
    errors: list[str],
) -> str | None:
    """Validate that a field is one of a deterministic set of strings."""
    normalized = require_non_empty_string(value, file_name=file_name, path=path, errors=errors)
    if normalized is None:
        return None

    allowed_values = tuple(allowed)
    if normalized not in allowed_values:
        add_error(
            errors,
            file_name,
            path,
            f"must be one of {', '.join(allowed_values)}; got `{normalized}`.",
        )
        return None
    return normalized


def validate_date_field(
    value: object,
    *,
    file_name: str,
    path: str,
    errors: list[str],
) -> None:
    """Validate strict YYYY-MM-DD date strings."""
    normalized = require_non_empty_string(value, file_name=file_name, path=path, errors=errors)
    if normalized is None:
        return
    if not parse_iso_date(normalized):
        add_error(errors, file_name, path, "must use YYYY-MM-DD format.")


def validate_optional_uri(
    value: object,
    *,
    file_name: str,
    path: str,
    errors: list[str],
) -> None:
    """Apply a lightweight URI check without pulling in extra dependencies."""
    if value is None:
        return
    normalized = require_non_empty_string(value, file_name=file_name, path=path, errors=errors)
    if normalized is None:
        return
    if not re.match(r"^https?://", normalized):
        add_error(errors, file_name, path, "must start with http:// or https://.")


def validate_optional_number(
    value: object,
    *,
    file_name: str,
    path: str,
    errors: list[str],
    minimum: float | None = None,
    maximum: float | None = None,
    integer_only: bool = False,
) -> None:
    """Validate optional numeric fields used in sample assets."""
    if value is None:
        return
    valid_type = isinstance(value, int) and not isinstance(value, bool)
    if not integer_only:
        valid_type = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
        )
    if not valid_type:
        add_error(
            errors,
            file_name,
            path,
            "must be a number." if not integer_only else "must be an integer.",
        )
        return

    if minimum is not None and value < minimum:
        add_error(errors, file_name, path, f"must be >= {minimum}.")
    if maximum is not None and value > maximum:
        add_error(errors, file_name, path, f"must be <= {maximum}.")


def schema_required(schema: dict, definition_name: str) -> set[str]:
    """Read required fields from the local schema for one entity definition."""
    definition = schema.get("$defs", {}).get(definition_name, {})
    required = definition.get("required", [])
    if not isinstance(required, list):
        return set()
    return {item for item in required if isinstance(item, str)}


def schema_enum(schema: dict, definition_name: str, property_name: str) -> tuple[str, ...]:
    """Read enum values from the local schema for one property."""
    definition = schema.get("$defs", {}).get(definition_name, {})
    properties = definition.get("properties", {})
    field = properties.get(property_name, {})
    enum_values = field.get("enum", [])
    if not isinstance(enum_values, list):
        return ()
    return tuple(item for item in enum_values if isinstance(item, str))


def validate_required_fields(
    entity: dict,
    required_fields: set[str],
    *,
    file_name: str,
    path: str,
    errors: list[str],
) -> None:
    """Validate presence of required fields before deeper type checks."""
    for field_name in sorted(required_fields):
        if field_name not in entity:
            add_error(errors, file_name, f"{path}.{field_name}", "is required.")


def validate_source_ref(
    source_ref: dict,
    *,
    schema: dict,
    file_name: str,
    path: str,
    errors: list[str],
) -> str | None:
    """Validate one source reference object and return its source_id."""
    validate_required_fields(
        source_ref,
        schema_required(schema, "SourceRef"),
        file_name=file_name,
        path=path,
        errors=errors,
    )
    source_id = require_non_empty_string(
        source_ref.get("source_id"),
        file_name=file_name,
        path=f"{path}.source_id",
        errors=errors,
    )
    require_enum(
        source_ref.get("source_type"),
        file_name=file_name,
        path=f"{path}.source_type",
        allowed=schema_enum(schema, "SourceRef", "source_type"),
        errors=errors,
    )
    require_non_empty_string(
        source_ref.get("label"),
        file_name=file_name,
        path=f"{path}.label",
        errors=errors,
    )
    validate_optional_uri(
        source_ref.get("url"),
        file_name=file_name,
        path=f"{path}.url",
        errors=errors,
    )
    validate_date_field(
        source_ref.get("observed_at"),
        file_name=file_name,
        path=f"{path}.observed_at",
        errors=errors,
    )
    if "note" in source_ref:
        require_non_empty_string(
            source_ref.get("note"),
            file_name=file_name,
            path=f"{path}.note",
            errors=errors,
        )
    return source_id


def source_ref_identity(source_ref: dict) -> str:
    """Build a stable identity signature for one source reference.

    `note` is intentionally excluded because the same source may support
    different entities with different local context explanations.
    """
    identity = {
        "source_id": source_ref.get("source_id"),
        "source_type": source_ref.get("source_type"),
        "label": source_ref.get("label"),
        "url": source_ref.get("url"),
        "observed_at": source_ref.get("observed_at"),
    }
    return json.dumps(identity, ensure_ascii=False, sort_keys=True)


def validate_company(
    company: dict,
    *,
    schema: dict,
    file_name: str,
    path: str,
    errors: list[str],
) -> str | None:
    """Validate one company profile entry."""
    validate_required_fields(
        company,
        schema_required(schema, "CompanyProfile"),
        file_name=file_name,
        path=path,
        errors=errors,
    )
    company_id = require_non_empty_string(
        company.get("company_id"),
        file_name=file_name,
        path=f"{path}.company_id",
        errors=errors,
    )
    require_non_empty_string(
        company.get("name"),
        file_name=file_name,
        path=f"{path}.name",
        errors=errors,
    )
    require_non_empty_string(
        company.get("city"),
        file_name=file_name,
        path=f"{path}.city",
        errors=errors,
    )
    require_enum(
        company.get("tier"),
        file_name=file_name,
        path=f"{path}.tier",
        allowed=schema_enum(schema, "CompanyProfile", "tier"),
        errors=errors,
    )
    require_string_list(
        company.get("known_business"),
        file_name=file_name,
        path=f"{path}.known_business",
        errors=errors,
        min_items=1,
    )
    validate_optional_number(
        company.get("employee_count"),
        file_name=file_name,
        path=f"{path}.employee_count",
        errors=errors,
        minimum=1,
        integer_only=True,
    )
    validate_optional_number(
        company.get("avg_rating"),
        file_name=file_name,
        path=f"{path}.avg_rating",
        errors=errors,
        minimum=0,
        maximum=5,
    )
    if "tags" in company:
        require_string_list(
            company.get("tags"),
            file_name=file_name,
            path=f"{path}.tags",
            errors=errors,
        )
    for optional_field in ("notes", "include_reason"):
        if optional_field in company:
            require_non_empty_string(
                company.get(optional_field),
                file_name=file_name,
                path=f"{path}.{optional_field}",
                errors=errors,
            )
    for optional_field in ("official_website", "career_url"):
        if optional_field in company:
            validate_optional_uri(
                company.get(optional_field),
                file_name=file_name,
                path=f"{path}.{optional_field}",
                errors=errors,
            )
    validate_date_field(
        company.get("last_verified"),
        file_name=file_name,
        path=f"{path}.last_verified",
        errors=errors,
    )
    return company_id


def validate_opportunity(
    opportunity: dict,
    *,
    schema: dict,
    file_name: str,
    path: str,
    errors: list[str],
) -> str | None:
    """Validate one job opportunity entry."""
    validate_required_fields(
        opportunity,
        schema_required(schema, "JobOpportunity"),
        file_name=file_name,
        path=path,
        errors=errors,
    )
    opportunity_id = require_non_empty_string(
        opportunity.get("opportunity_id"),
        file_name=file_name,
        path=f"{path}.opportunity_id",
        errors=errors,
    )
    require_non_empty_string(
        opportunity.get("company_id"),
        file_name=file_name,
        path=f"{path}.company_id",
        errors=errors,
    )
    require_non_empty_string(
        opportunity.get("job_title"),
        file_name=file_name,
        path=f"{path}.job_title",
        errors=errors,
    )
    require_enum(
        opportunity.get("source_type"),
        file_name=file_name,
        path=f"{path}.source_type",
        allowed=schema_enum(schema, "JobOpportunity", "source_type"),
        errors=errors,
    )
    require_non_empty_string(
        opportunity.get("match_reason"),
        file_name=file_name,
        path=f"{path}.match_reason",
        errors=errors,
    )
    if "tech_stack" in opportunity:
        require_string_list(
            opportunity.get("tech_stack"),
            file_name=file_name,
            path=f"{path}.tech_stack",
            errors=errors,
        )
    for optional_field in ("experience_required", "salary_range"):
        if optional_field in opportunity:
            require_non_empty_string(
                opportunity.get(optional_field),
                file_name=file_name,
                path=f"{path}.{optional_field}",
                errors=errors,
            )
    if "job_url" in opportunity:
        validate_optional_uri(
            opportunity.get("job_url"),
            file_name=file_name,
            path=f"{path}.job_url",
            errors=errors,
        )
    if "salary_match" in opportunity:
        require_enum(
            opportunity.get("salary_match"),
            file_name=file_name,
            path=f"{path}.salary_match",
            allowed=schema_enum(schema, "JobOpportunity", "salary_match"),
            errors=errors,
        )
    if "risk_flags" in opportunity:
        require_string_list(
            opportunity.get("risk_flags"),
            file_name=file_name,
            path=f"{path}.risk_flags",
            errors=errors,
        )
    return opportunity_id


def validate_sentiment(
    sentiment: dict,
    *,
    schema: dict,
    file_name: str,
    path: str,
    errors: list[str],
) -> str | None:
    """Validate one company sentiment entry."""
    validate_required_fields(
        sentiment,
        schema_required(schema, "CompanySentiment"),
        file_name=file_name,
        path=path,
        errors=errors,
    )
    sentiment_id = require_non_empty_string(
        sentiment.get("sentiment_id"),
        file_name=file_name,
        path=f"{path}.sentiment_id",
        errors=errors,
    )
    require_non_empty_string(
        sentiment.get("company_id"),
        file_name=file_name,
        path=f"{path}.company_id",
        errors=errors,
    )
    require_non_empty_string(
        sentiment.get("summary"),
        file_name=file_name,
        path=f"{path}.summary",
        errors=errors,
    )
    validate_date_field(
        sentiment.get("observed_at"),
        file_name=file_name,
        path=f"{path}.observed_at",
        errors=errors,
    )
    for optional_field in ("community_source", "news_source"):
        if optional_field in sentiment:
            require_non_empty_string(
                sentiment.get(optional_field),
                file_name=file_name,
                path=f"{path}.{optional_field}",
                errors=errors,
            )
    for optional_field in ("pros", "cons"):
        if optional_field in sentiment:
            require_string_list(
                sentiment.get(optional_field),
                file_name=file_name,
                path=f"{path}.{optional_field}",
                errors=errors,
            )
    return sentiment_id


def validate_source_refs_array(
    entity: dict,
    *,
    schema: dict,
    file_name: str,
    path: str,
    errors: list[str],
) -> list[tuple[str, dict]]:
    """Validate the source_refs array and return referenced source IDs."""
    source_refs = entity.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs:
        add_error(errors, file_name, f"{path}.source_refs", "must be a non-empty array.")
        return []

    source_refs_with_ids: list[tuple[str, dict]] = []
    for index, source_ref in enumerate(source_refs):
        if not isinstance(source_ref, dict):
            add_error(errors, file_name, f"{path}.source_refs[{index}]", "must be an object.")
            continue
        source_id = validate_source_ref(
            source_ref,
            schema=schema,
            file_name=file_name,
            path=f"{path}.source_refs[{index}]",
            errors=errors,
        )
        if source_id is not None:
            source_refs_with_ids.append((source_id, source_ref))
    return source_refs_with_ids


def validate_sample_top_level(
    sample: dict,
    *,
    schema: dict,
    file_name: str,
    errors: list[str],
) -> None:
    """Validate top-level sample fields and required arrays."""
    required = schema.get("required", [])
    if isinstance(required, list):
        for key in required:
            if isinstance(key, str) and key not in sample:
                add_error(errors, file_name, key, "is required.")
    else:
        add_error(errors, file_name, "required", "schema top-level `required` must be an array.")

    require_non_empty_string(
        sample.get("schema_version"),
        file_name=file_name,
        path="schema_version",
        errors=errors,
    )
    require_non_empty_string(
        sample.get("city"),
        file_name=file_name,
        path="city",
        errors=errors,
    )
    if "generated_at" in sample:
        validate_date_field(
            sample.get("generated_at"),
            file_name=file_name,
            path="generated_at",
            errors=errors,
        )


def validate_documents(schema: dict, sample: dict, sample_path: Path) -> tuple[list[str], set[str], set[str]]:
    """Run deterministic JSON checks and return errors plus collected references."""
    errors: list[str] = []
    file_name = sample_path.name

    validate_sample_top_level(sample, schema=schema, file_name=file_name, errors=errors)

    companies = ensure_list(sample.get("companies"), "companies", errors, file_name=file_name)
    opportunities = ensure_list(
        sample.get("job_opportunities"),
        "job_opportunities",
        errors,
        file_name=file_name,
    )
    sentiments = ensure_list(
        sample.get("company_sentiments"),
        "company_sentiments",
        errors,
        file_name=file_name,
    )

    company_ids: set[str] = set()
    seen_opportunity_ids: set[str] = set()
    seen_sentiment_ids: set[str] = set()
    source_ref_catalog: dict[str, str] = {}
    seen_risk_flags: set[str] = set()

    for index, company in enumerate(companies):
        path = f"companies[{index}]"
        company_id = validate_company(
            company,
            schema=schema,
            file_name=file_name,
            path=path,
            errors=errors,
        )
        if company_id is not None:
            if company_id in company_ids:
                add_error(errors, file_name, f"{path}.company_id", f"duplicates `{company_id}`.")
            company_ids.add(company_id)
        for source_id, source_ref in validate_source_refs_array(
            company,
            schema=schema,
            file_name=file_name,
            path=path,
            errors=errors,
        ):
            serialized = source_ref_identity(source_ref)
            existing = source_ref_catalog.get(source_id)
            if existing is None:
                source_ref_catalog[source_id] = serialized
            elif existing != serialized:
                add_error(
                    errors,
                    file_name,
                    f"{path}.source_refs",
                    f"reuses source_id `{source_id}` with conflicting content.",
                )

    for index, opportunity in enumerate(opportunities):
        path = f"job_opportunities[{index}]"
        opportunity_id = validate_opportunity(
            opportunity,
            schema=schema,
            file_name=file_name,
            path=path,
            errors=errors,
        )
        if opportunity_id is not None:
            if opportunity_id in seen_opportunity_ids:
                add_error(errors, file_name, f"{path}.opportunity_id", f"duplicates `{opportunity_id}`.")
            seen_opportunity_ids.add(opportunity_id)

        company_id = opportunity.get("company_id")
        if isinstance(company_id, str) and company_id not in company_ids:
            add_error(
                errors,
                file_name,
                f"{path}.company_id",
                f"references unknown company_id `{company_id}`.",
            )

        risk_flags = opportunity.get("risk_flags", [])
        if isinstance(risk_flags, list):
            for risk_flag in risk_flags:
                if isinstance(risk_flag, str) and risk_flag.strip():
                    seen_risk_flags.add(risk_flag.strip())

        for source_id, source_ref in validate_source_refs_array(
            opportunity,
            schema=schema,
            file_name=file_name,
            path=path,
            errors=errors,
        ):
            serialized = source_ref_identity(source_ref)
            existing = source_ref_catalog.get(source_id)
            if existing is None:
                source_ref_catalog[source_id] = serialized
            elif existing != serialized:
                add_error(
                    errors,
                    file_name,
                    f"{path}.source_refs",
                    f"reuses source_id `{source_id}` with conflicting content.",
                )

    for index, sentiment in enumerate(sentiments):
        path = f"company_sentiments[{index}]"
        sentiment_id = validate_sentiment(
            sentiment,
            schema=schema,
            file_name=file_name,
            path=path,
            errors=errors,
        )
        if sentiment_id is not None:
            if sentiment_id in seen_sentiment_ids:
                add_error(errors, file_name, f"{path}.sentiment_id", f"duplicates `{sentiment_id}`.")
            seen_sentiment_ids.add(sentiment_id)

        company_id = sentiment.get("company_id")
        if isinstance(company_id, str) and company_id not in company_ids:
            add_error(
                errors,
                file_name,
                f"{path}.company_id",
                f"references unknown company_id `{company_id}`.",
            )

        for source_id, source_ref in validate_source_refs_array(
            sentiment,
            schema=schema,
            file_name=file_name,
            path=path,
            errors=errors,
        ):
            serialized = source_ref_identity(source_ref)
            existing = source_ref_catalog.get(source_id)
            if existing is None:
                source_ref_catalog[source_id] = serialized
            elif existing != serialized:
                add_error(
                    errors,
                    file_name,
                    f"{path}.source_refs",
                    f"reuses source_id `{source_id}` with conflicting content.",
                )

    return errors, set(source_ref_catalog.keys()), seen_risk_flags


def validate_report(
    report_text: str,
    *,
    report_path: Path,
    valid_source_ids: set[str],
    valid_risk_flags: set[str],
) -> list[str]:
    """Run deterministic report checks against the sample JSON references."""
    errors: list[str] = []
    file_name = report_path.name

    for heading in REQUIRED_REPORT_SECTIONS:
        if heading not in report_text:
            add_error(errors, file_name, heading, "section is required.")
    for scope_line in REQUIRED_SCOPE_LINES:
        if scope_line not in report_text:
            add_error(errors, file_name, "Analysis Scope", f"must include `{scope_line}`.")

    missing_buckets = [
        bucket
        for bucket in ("### 冲刺型", "### 稳妥型", "### 待人工判断")
        if bucket not in report_text
    ]
    for bucket in missing_buckets:
        add_error(errors, file_name, "Strategy Recommendations", f"missing `{bucket}` subsection.")

    fact_source_matches = FACT_SOURCE_LINE_PATTERN.findall(report_text)
    if not fact_source_matches:
        add_error(errors, file_name, "Fact Sources", "must include at least one structured source line.")
    seen_report_fact_sources: set[str] = set()
    for source_id, source_type, observed_at in fact_source_matches:
        if source_id not in valid_source_ids:
            add_error(errors, file_name, f"Fact Sources[{source_id}]", "does not exist in sample JSON.")
        if source_id in seen_report_fact_sources:
            add_error(errors, file_name, f"Fact Sources[{source_id}]", "is listed more than once.")
        seen_report_fact_sources.add(source_id)
        if not parse_iso_date(observed_at):
            add_error(errors, file_name, f"Fact Sources[{source_id}].observed_at", "must use YYYY-MM-DD format.")
        if source_type not in {
            "official",
            "job_board",
            "school_board",
            "industry_list",
            "community",
            "news",
            "manual_note",
        }:
            add_error(
                errors,
                file_name,
                f"Fact Sources[{source_id}].source_type",
                f"has unsupported value `{source_type}`.",
            )

    report_source_ids = set(SOURCE_REF_PATTERN.findall(report_text))
    missing_source_ids = sorted(report_source_ids - valid_source_ids)
    for source_id in missing_source_ids:
        add_error(errors, file_name, f"source_ref[{source_id}]", "does not exist in sample JSON.")

    report_risk_flags: set[str] = set()
    for line in report_text.splitlines():
        if "|" not in line:
            continue
        for risk_flag in valid_risk_flags:
            if risk_flag in line:
                report_risk_flags.add(risk_flag)

    missing_exception_rows = sorted(report_risk_flags - valid_risk_flags)
    for risk_flag in missing_exception_rows:
        add_error(errors, file_name, f"risk_flag[{risk_flag}]", "does not exist in sample JSON.")

    return errors


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    schema_path = Path(args.schema).resolve()
    sample_path = Path(args.sample).resolve()
    report_path = Path(args.report).resolve()

    try:
        schema = ensure_dict(load_json(schema_path), "Schema")
        sample = ensure_dict(load_json(sample_path), "Sample")
        report_text = load_text(report_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors, valid_source_ids, valid_risk_flags = validate_documents(schema, sample, sample_path)
    errors.extend(
        validate_report(
            report_text,
            report_path=report_path,
            valid_source_ids=valid_source_ids,
            valid_risk_flags=valid_risk_flags,
        )
    )

    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "OK: validated sample "
        f"`{sample_path.name}` and report `{report_path.name}` with deterministic checks."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
