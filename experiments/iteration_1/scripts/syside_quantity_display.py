from __future__ import annotations

"""
Format Syside ``evaluate_feature`` results for extraction reports.

Kerbal evaluates length-typed quantities in **SI base metres**. We detect
attributes whose usage types include ``LengthValue`` and optionally display them
as **centimetres** for mirror / beam tooling.

When evaluation fails for tuple quantity literals (e.g. ``(10, 10) [cm]``),
we fall back to walking the ``feature_value_expression`` AST (Quantity + Comma).
"""

from dataclasses import dataclass
import math
from typing import Any, Literal

import syside

try:
    from syside.core import Operator
except Exception:  # pragma: no cover - defensive for older syside layouts
    Operator = None  # type: ignore[misc, assignment]


# Syside types iterator names seen on Length-specialized quantities.
LENGTH_SEMANTICS_MARKERS: frozenset[str] = frozenset({"LengthValue"})


@dataclass(frozen=True, slots=True)
class AttributeDisplayConfig:
    """Presentation rules for extractor output (machine + human-readable)."""

    length_unit: Literal["cm", "m"] = "cm"

    def length_banner_line(self) -> str:
        if self.length_unit == "cm":
            return (
                "  Length quantities: centimetres  "
                "(Syside evaluates SI base metres; values are scaled ×100 here)."
            )
        return "  Length quantities: metres  (Kerbal SI base)."


def attribute_usage_has_length_semantics(attribute_usage: Any) -> bool:
    if type(attribute_usage) is not syside.AttributeUsage:
        return False
    try:
        names = {t.name for t in attribute_usage.types if hasattr(t, "name")}
    except Exception:
        return False
    return bool(names & LENGTH_SEMANTICS_MARKERS)


def format_length_quantity(metres: float, unit: Literal["cm", "m"]) -> str:
    if unit == "m":
        return f"{_format_real(float(metres))} m"
    centimetres = float(metres) * 100.0
    return f"{_format_real(centimetres)} cm"


def _format_real(x: float) -> str:
    if not math.isfinite(x):
        return str(x)
    xr = round(x)
    if math.isfinite(xr) and abs(x - xr) < 1e-9:
        return str(int(xr))
    return f"{x:.12g}"


def _literal_floats_from_comma_expression(comma_expr: Any) -> list[float]:
    """Extract ordered numeric literals from a Comma operator expression."""
    if Operator is None or getattr(comma_expr, "operator", None) != Operator.Comma:
        return []
    out: list[float] = []
    for feat in comma_expr.owned_elements:
        if type(feat).__name__ != "Feature":
            continue
        for lit in feat.owned_elements:
            tn = type(lit).__name__
            if tn == "LiteralInteger":
                out.append(float(lit.value))
            elif tn == "LiteralRational":
                num = float(getattr(lit, "numerator", getattr(lit, "value", 0)))
                den = float(getattr(lit, "denominator", 1)) or 1.0
                out.append(num / den)
    return out


def _referent_is_centimetre(referent: Any) -> bool:
    s = str(referent).lower()
    return "centimetre" in s or s.endswith("::cm") or "cm" in s


def _referent_is_metre(referent: Any) -> bool:
    s = str(referent).lower()
    return "metre" in s or "meter" in s


def try_format_quantity_operator_expression(
    expr: Any,
    display: AttributeDisplayConfig,
) -> str | None:
    """
    Best-effort string for ``(n1, n2, ...) [unit]`` when ``evaluate_feature`` fails.

    Source literals are interpreted in the **written** unit (e.g. ``[cm]``).
    """
    if Operator is None or type(expr).__name__ != "OperatorExpression":
        return None
    if getattr(expr, "operator", None) != Operator.Quantity:
        return None

    feature_children = [c for c in expr.owned_elements if type(c).__name__ == "Feature"]
    if len(feature_children) < 2:
        return None

    comma_block: Any | None = None
    for inner in feature_children[0].owned_elements:
        if type(inner).__name__ == "OperatorExpression" and getattr(inner, "operator", None) == Operator.Comma:
            comma_block = inner
            break
    if comma_block is None:
        return None

    nums = _literal_floats_from_comma_expression(comma_block)
    if not nums:
        return None

    unit_ref: Any | None = None
    for inner in feature_children[1].owned_elements:
        if type(inner).__name__ == "FeatureReferenceExpression":
            unit_ref = getattr(inner, "referent", None) or getattr(inner, "referenced_feature", None)
            break
    if unit_ref is None:
        return None

    parts_out: list[str] = []
    for n in nums:
        if _referent_is_centimetre(unit_ref):
            if display.length_unit == "cm":
                parts_out.append(f"{_format_real(n)} cm")
            else:
                parts_out.append(format_length_quantity(n / 100.0, "m"))
        elif _referent_is_metre(unit_ref):
            if display.length_unit == "cm":
                parts_out.append(format_length_quantity(n, "cm"))
            else:
                parts_out.append(f"{_format_real(n)} m")
        else:
            parts_out.append(f"{_format_real(n)} ({unit_ref})")
    return "[" + ", ".join(parts_out) + "]"


def try_format_feature_value_expression(
    feature: Any,
    display: AttributeDisplayConfig,
) -> str | None:
    expr = getattr(feature, "feature_value_expression", None)
    if expr is None:
        return None
    return try_format_quantity_operator_expression(expr, display)


def format_evaluated_kernel_value(
    raw: Any,
    attribute_usage: Any,
    display: AttributeDisplayConfig,
) -> str:
    if isinstance(raw, bool):
        return str(raw)
    if isinstance(raw, (int, float)):
        if attribute_usage_has_length_semantics(attribute_usage):
            return format_length_quantity(float(raw), display.length_unit)
        return str(raw)
    if isinstance(raw, (list, tuple)):
        if raw and type(raw[0]).__name__ == "EnumerationUsage":
            names = [str(getattr(x, "name", "") or x) for x in raw]
            return "[" + ", ".join(names) + "]"
        if raw and all(isinstance(x, (int, float)) for x in raw) and attribute_usage_has_length_semantics(
            attribute_usage,
        ):
            parts = [format_length_quantity(float(x), display.length_unit) for x in raw]
            return "[" + ", ".join(parts) + "]"
    if hasattr(raw, "name") and getattr(raw, "name", None):
        return str(raw.name)
    return str(raw)


def evaluate_feature_as_display_string(
    compiler: Any,
    stdlib: Any,
    feature: Any,
    scope: Any,
    display: AttributeDisplayConfig,
) -> str | None:
    value, report = compiler.evaluate_feature(
        feature=feature,
        scope=scope,
        stdlib=stdlib,
        experimental_quantities=True,
    )
    if not report.fatal and value is not None:
        return format_evaluated_kernel_value(value, feature, display)

    expr_fallback = try_format_feature_value_expression(feature, display)
    if expr_fallback is not None:
        return expr_fallback

    if value is not None:
        return format_evaluated_kernel_value(value, feature, display)

    return None


def _is_preferred_attribute_display(text: str) -> bool:
    """Heuristic: real evaluated / serialized values vs symbolic feature paths."""
    if text in ("True", "False"):
        return True
    if text.startswith("[") and text.endswith("]"):
        return True
    if any(ch.isdigit() for ch in text) and ("cm" in text or " m" in text):
        return True
    return False


def display_string_score(attr_name: str, text: str) -> tuple[int, int, int]:
    """Higher is better: prefer non-self-reference, then concrete displays, then length."""
    is_self = text == attr_name
    preferred = _is_preferred_attribute_display(text)
    return (0 if is_self else 1, 1 if preferred else 0, len(text))
