#!/usr/bin/env python3
"""Create review-only BOM and SKU inventory CSVs from PADS/EasyEDA ASCII attributes."""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from parse_pads_ascii_netlist import PadsAsciiNetlist


AUTHORITY = "Reconstructed from source attributes; not an approved procurement BOM"


def _get(attrs, *keys):
    for key in keys:
        value = attrs.get(key, "").strip()
        if value:
            return value
    return ""


def _assembly(attrs):
    value = _get(attrs, "Add into BOM").lower()
    if value in {"yes", "true", "1", "y"}:
        return "include"
    if value in {"no", "false", "0", "n"}:
        return "exclude"
    return "unspecified"


def _row(ref, package, attrs):
    mpn = _get(attrs, "Manufacturer Part", "MPN")
    device = _get(attrs, "Device")
    footprint = _get(attrs, "Footprint", "Supplier Footprint")
    if not footprint:
        footprint = package.partition("@")[2] or package
    value = _get(attrs, "Value", "Name")
    required = ["Manufacturer Part", "Manufacturer", "Footprint"]
    missing = [key for key, val in zip(required, (mpn, _get(attrs, "Manufacturer"), footprint)) if not val]
    return {
        "Authority": AUTHORITY,
        "Reference": ref,
        "Quantity per board": 1,
        "Assembly status": _assembly(attrs),
        "MPN": mpn,
        "MPN status": "explicit source field" if mpn else ("missing; device identifier is unverified" if device else "missing"),
        "Device identifier (unverified)": device,
        "Symbol": _get(attrs, "Symbol"),
        "Name": _get(attrs, "Name"),
        "Value": value,
        "Manufacturer": _get(attrs, "Manufacturer"),
        "Supplier": _get(attrs, "Supplier"),
        "Supplier Part": _get(attrs, "Supplier Part"),
        "Footprint": footprint,
        "Tolerance": _get(attrs, "Tolerance", "Resistance Tolerance"),
        "Voltage rating": _get(attrs, "Voltage Rating", "Voltage Rated"),
        "Temperature coefficient / dielectric": _get(attrs, "Temperature Coefficient", "Dielectric"),
        "Current rating": _get(attrs, "Current Rating", "Current - Saturation(Isat)"),
        "Description": _get(attrs, "Description", "LCSC Part Name"),
        "Datasheet": _get(attrs, "Datasheet"),
        "Missing fields": "; ".join(missing),
        "Source attributes (JSON)": json.dumps(attrs, ensure_ascii=False, sort_keys=True),
    }


def _sku_rows(rows):
    groups = defaultdict(list)
    for row in rows:
        status = row["Assembly status"]
        if row["MPN"]:
            key = ("manufacturer MPN", row["MPN"], row["Manufacturer"], status)
        elif row["Device identifier (unverified)"]:
            key = ("unverified device grouping", row["Device identifier (unverified)"], row["Footprint"], status)
        else:
            key = (
                "electrical/package placeholder",
                row["Value"], row["Tolerance"], row["Voltage rating"],
                row["Temperature coefficient / dielectric"], row["Footprint"], status,
            )
        groups[key].append(row)

    result = []
    for key, members in sorted(groups.items(), key=lambda item: tuple(str(v) for v in item[0])):
        explicit_mpn = key[0] == "manufacturer MPN"
        result.append({
            "Authority": AUTHORITY,
            "Grouping basis": key[0],
            "Explicit MPN present": "yes" if explicit_mpn else "no",
            "Identifier / grouping key": " | ".join(key[1:-1]),
            "Assembly status": key[-1],
            "Quantity per board": len(members),
            "References": ", ".join(row["Reference"] for row in members),
            "Values": ", ".join(sorted({row["Value"] for row in members if row["Value"]})),
            "Footprints": ", ".join(sorted({row["Footprint"] for row in members if row["Footprint"]})),
            "Missing fields": "; ".join(sorted({field for row in members for field in row["Missing fields"].split("; ") if field})),
        })
    return result


def _write_csv(path, rows, fields, overwrite):
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite to replace it")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="PADS/EasyEDA ASCII netlist with *PART*/*SIGNAL* sections")
    parser.add_argument("--output-dir", help="defaults to <input directory>/ee-review")
    parser.add_argument("--overwrite", action="store_true", help="replace same-named generated CSVs")
    args = parser.parse_args()

    source = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else source.parent / "ee-review"
    try:
        netlist = PadsAsciiNetlist.from_file(source)
        sanity = netlist.sanity()
        if any(sanity[key] for key in ("duplicate_nets", "pin_conflicts", "unknown_refs", "attributes_without_part")):
            raise ValueError(f"PADS parser sanity gate failed: {sanity}")

        rows = [_row(ref, package, netlist.attributes.get(ref, {})) for ref, package in sorted(netlist.parts.items())]
        summary = _sku_rows(rows)
        output_dir.mkdir(parents=True, exist_ok=True)
        detail_path = output_dir / f"{source.stem}_reconstructed_bom.csv"
        summary_path = output_dir / f"{source.stem}_reconstructed_sku_summary.csv"
        if not args.overwrite and (detail_path.exists() or summary_path.exists()):
            existing = [str(path) for path in (detail_path, summary_path) if path.exists()]
            raise FileExistsError(f"Refusing to overwrite existing outputs: {', '.join(existing)}")
        _write_csv(detail_path, rows, list(rows[0]) if rows else [], args.overwrite)
        _write_csv(summary_path, summary, list(summary[0]) if summary else [], args.overwrite)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    included = sum(row["Assembly status"] == "include" for row in rows)
    excluded = sum(row["Assembly status"] == "exclude" for row in rows)
    unspecified = sum(row["Assembly status"] == "unspecified" for row in rows)
    explicit_mpn_refs = sum(bool(row["MPN"]) for row in rows if row["Assembly status"] == "include")
    print(f"parts={len(rows)} include={included} exclude={excluded} unspecified={unspecified}")
    print(f"included_with_explicit_mpn={explicit_mpn_refs}; see per-reference Missing fields before procurement use")
    print(detail_path)
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
