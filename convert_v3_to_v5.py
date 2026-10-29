#!/usr/bin/env python3
"""
Convert a v3 NextSwitch FI-profile JSON into the v5 layout.

Design principle
----------------
v5's `transaction_type` is the only fixed vocabulary. Every other VALUE
(mti, processing_cde, cond_cde, entry_mde, mac_fld, uuids, timers, keys, ...)
is taken dynamically from the v3 input - nothing is copied from a v5 sample.
Only the STRUCTURE changes (renamed / dropped / added keys, regrouped
transaction_type, key ordering).

What the converter does
-----------------------
metadata      add `parent_version` (null unless --parent-version is given)
fi            add iso_packager_name, swift_code
profile       drop saf_mti_queue_enabled, saf_reversal_drop_after_t1
              add asym_chp99_sampling_rate, cutover_schedule_enabled,
                  key_exchange_schedule_enabled, sign_on_schedule_enabled
station       drop cio_internal_port, proxy; add ext_ip_addr, ext_port;
              channel ids "cio001" -> "cio-001"
bin           unchanged
msg_profile   v3 `transaction_type` (e.g. CNP_PURCHASE_REQ) becomes v5 `name`;
              v5 `transaction_type` is the parent (CNP_PURCHASE) = name minus
              _REQ / _RES / _RT; `msgProfileId` -> `msg_profile_id`;
              `reversible` = "REVERSAL" not in transaction_type
txn_req_rule  `msgProfileId` -> `msg_profile_id`;
              description -> "<name> | <transaction_type>"
key_profile   drop dek_des_mode, dek_master_key_len

Profiles whose derived transaction_type is not in v5's vocabulary (e.g.
CARD_LCM, TOKEN_PROVISION_NOTIFICATION) are dropped together with their rules,
unless --keep-unmapped is given.

Usage
-----
    python convert_v3_to_v5.py v3.json                 # -> v5_output/v3.json
    python convert_v3_to_v5.py A.json B.json C.json    # several files at once
    python convert_v3_to_v5.py *.json -d converted     # all json in folder
    python convert_v3_to_v5.py *.json --pretty --keep-unmapped
"""
import argparse
import json
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# The fixed vocabulary: every distinct `transaction_type` found in v5.
# --------------------------------------------------------------------------
V5_TRANSACTION_TYPES = {
    "CNP_ADJUSTMENT", "CNP_ADJUSTMENT_REVERSAL",
    "CNP_PRE_AUTH", "CNP_PRE_AUTH_REVERSAL",
    "CNP_PURCHASE", "CNP_PURCHASE_CANCELLATION",
    "CNP_PURCHASE_CANCELLATION_REVERSAL", "CNP_PURCHASE_REVERSAL",
    "CNP_SALES_COMPLETION",
    "CP_CASH_OUT", "CP_CASH_OUT_REVERSAL",
    "CP_PRE_AUTH", "CP_PRE_AUTH_REVERSAL",
    "CP_PURCHASE", "CP_PURCHASE_CANCELLATION",
    "CP_PURCHASE_CANCELLATION_REVERSAL", "CP_PURCHASE_REVERSAL",
    "CP_SALES_COMPLETION",
    "OEM_CNP_PRE_AUTH", "OEM_CNP_PURCHASE", "OEM_CNP_PURCHASE_CANCELLATION",
    "OEM_CNP_SALES_COMPLETION",
    "REFUND", "REFUND_REVERSAL",
}

# --------------------------------------------------------------------------
# Structural differences v3 -> v5 (values for NEW keys use v5's defaults).
# --------------------------------------------------------------------------
FI_ADD = {"iso_packager_name": "j8583", "swift_code": None}

PROFILE_DROP = {"saf_mti_queue_enabled", "saf_reversal_drop_after_t1"}
PROFILE_ADD = {
    "asym_chp99_sampling_rate": None,
    "cutover_schedule_enabled": True,
    "key_exchange_schedule_enabled": True,
    "sign_on_schedule_enabled": True,
}

STATION_DROP = {"cio_internal_port", "proxy"}
STATION_ADD = {"ext_ip_addr": None, "ext_port": None}
STATION_ORDER = [
    "id", "tcp_role", "ip_addr", "port", "ext_ip_addr", "ext_port",
    "tls_enabled", "tls_version", "bypass_cert_validation",
    "force_accept_new_con", "enabled",
]

KEY_PROFILE_DROP = {"dek_des_mode", "dek_master_key_len"}

_SUFFIX = re.compile(r"_(REQ|RES|RT)(_RT)?$")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def derive_names(raw_type: str):
    """v3 transaction_type -> (v5 name, v5 transaction_type).

    v3 sometimes carries an alias after a pipe, e.g.
    'REFUND_REQ | ADJUSTMENT_CREDIT_REQ ' -> name 'REFUND_REQ'.
    """
    name = raw_type.split("|")[0].strip()
    return name, _SUFFIX.sub("", name)


def alpha(d: dict) -> dict:
    return {k: d[k] for k in sorted(d)}


def ordered(d: dict, first: list) -> dict:
    head = {k: d[k] for k in first if k in d}
    tail = {k: d[k] for k in sorted(d) if k not in head}
    return {**head, **tail}


def fix_channel(ch):
    """'cio001' -> 'cio-001' (already-dashed values are left alone)."""
    if isinstance(ch, str):
        return re.sub(r"^cio(\d+)$", r"cio-\1", ch)
    return ch


# --------------------------------------------------------------------------
# section converters
# --------------------------------------------------------------------------
def convert_metadata(md, parent_version, version):
    out = dict(md)
    if version is not None:
        out["version"] = version
    out["parent_version"] = parent_version
    return alpha(out)


def convert_fi(fi):
    return alpha({**FI_ADD, **fi})


def convert_profile(p):
    return alpha({**PROFILE_ADD, **{k: v for k, v in p.items() if k not in PROFILE_DROP}})


def convert_station(s):
    out = {k: v for k, v in s.items() if k not in STATION_DROP}
    for k, v in STATION_ADD.items():
        out.setdefault(k, v)
    if isinstance(out.get("enabled"), list):
        out["enabled"] = [fix_channel(c) for c in out["enabled"]]
    return ordered(out, STATION_ORDER)


def convert_key_profile(kp):
    return alpha({k: v for k, v in kp.items() if k not in KEY_PROFILE_DROP})


def convert_msg_profile(p):
    name, ttype = derive_names(p["transaction_type"])
    out = {k: v for k, v in p.items() if k not in ("transaction_type", "msgProfileId")}
    out["msg_profile_id"] = p["msgProfileId"]
    out["reversible"] = "REVERSAL" not in ttype
    out = alpha(out)
    # v5 layout: mti, transaction_type, name, then everything else A-Z
    head = {"mti": out.pop("mti"), "transaction_type": ttype, "name": name}
    return {**head, **out}


def convert_rule(r, profile_by_id):
    out = {k: v for k, v in r.items() if k not in ("msgProfileId", "description")}
    out["msg_profile_id"] = r["msgProfileId"]
    prof = profile_by_id.get(r["msgProfileId"])
    if prof is not None:
        name, ttype = prof["name"], prof["transaction_type"]
    else:  # orphan rule: fall back to its own description
        name, ttype = derive_names(r.get("description", ""))
    out = alpha(out)
    head = {"mti": out.pop("mti"), "description": f"{name} | {ttype}"}
    return {**head, **out}


# --------------------------------------------------------------------------
# main conversion
# --------------------------------------------------------------------------
def convert(v3: dict, keep_unmapped=False, parent_version=None, version=None, log=None):
    log = log or (lambda m: None)
    out = {}
    out["metadata"] = convert_metadata(v3.get("metadata", {}), parent_version, version)
    out["fi"] = convert_fi(v3["fi"])
    out["profile"] = convert_profile(v3["profile"])
    out["station"] = [convert_station(s) for s in v3.get("station", [])]
    out["bin"] = list(v3.get("bin", []))

    # ---- msg_profile ------------------------------------------------------
    kept, dropped_ids, dropped_names = [], set(), []
    for p in v3.get("msg_profile", []):
        conv = convert_msg_profile(p)
        if conv["transaction_type"] in V5_TRANSACTION_TYPES or keep_unmapped:
            if conv["transaction_type"] not in V5_TRANSACTION_TYPES:
                log(f"  kept non-v5 transaction_type: {conv['transaction_type']} ({conv['name']})")
            kept.append(conv)
        else:
            dropped_ids.add(conv["msg_profile_id"])
            dropped_names.append(conv["name"])
    # v5 orders profiles by (transaction_type, first mti)
    kept.sort(key=lambda m: (m["transaction_type"], m["mti"][0] if m["mti"] else ""))
    out["msg_profile"] = kept
    profile_by_id = {m["msg_profile_id"]: m for m in kept}

    # ---- txn_req_rule -----------------------------------------------------
    rules, dropped_rules = [], 0
    for r in v3.get("txn_req_rule", []):
        if r["msgProfileId"] in dropped_ids:
            dropped_rules += 1
            continue
        if r["msgProfileId"] not in profile_by_id:
            log(f"  WARNING orphan rule (no matching profile): {r.get('description')}")
        if r.get("type") is None:
            log(f"  WARNING rule '{r.get('description')}' has type=null in v3 (v5 only uses A/I); kept as-is")
        rules.append(convert_rule(r, profile_by_id))
    out["txn_req_rule"] = rules

    out["key_profile"] = convert_key_profile(v3["key_profile"])

    log(f"msg_profile : {len(v3.get('msg_profile', []))} -> {len(kept)}")
    log(f"txn_req_rule: {len(v3.get('txn_req_rule', []))} -> {len(rules)}")
    if dropped_names:
        log(f"  dropped {len(dropped_names)} profile(s) and {dropped_rules} rule(s) "
            f"whose transaction_type is not in v5:")
        for n in dropped_names:
            log(f"    - {n}")
        log("  (use --keep-unmapped to keep them)")
    return out


def looks_like_v3(doc: dict) -> bool:
    """v3 uses camelCase `msgProfileId`; v5 already uses `msg_profile_id`."""
    profiles = doc.get("msg_profile") or []
    return bool(profiles) and "msgProfileId" in profiles[0]


def main():
    ap = argparse.ArgumentParser(description="Convert v3 JSON file(s) to v5 JSON")
    ap.add_argument("inputs", nargs="+", type=Path, help="one or more v3 json files")
    ap.add_argument("-d", "--out-dir", type=Path, default=Path("v5_output"),
                    help="folder for converted files (default: ./v5_output). "
                         "Each output keeps its input file name.")
    ap.add_argument("--pretty", action="store_true", help="indent output (default: minified, like v5)")
    ap.add_argument("--keep-unmapped", action="store_true",
                    help="keep profiles whose transaction_type is not in v5's vocabulary")
    ap.add_argument("--parent-version", default=None, help="value for metadata.parent_version (default: null)")
    ap.add_argument("--version", default=None, help="override metadata.version (default: keep v3 value)")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    kwargs = {"indent": 2} if args.pretty else {"separators": (",", ":")}
    ok, skipped, failed = [], [], []

    for path in args.inputs:
        print(f"\n=== {path.name} ===", file=sys.stderr)
        try:
            with path.open(encoding="utf-8") as f:
                v3 = json.load(f)
            if not looks_like_v3(v3):
                print("  SKIPPED: does not look like v3 (no 'msgProfileId'); already v5?", file=sys.stderr)
                skipped.append(path.name)
                continue
            result = convert(
                v3,
                keep_unmapped=args.keep_unmapped,
                parent_version=args.parent_version,
                version=args.version,
                log=lambda m: print(m, file=sys.stderr),
            )
            out_path = args.out_dir / path.name
            out_path.write_text(json.dumps(result, ensure_ascii=False, **kwargs), encoding="utf-8")
            print(f"  written: {out_path}", file=sys.stderr)
            ok.append(path.name)
        except Exception as e:  # keep going so one bad file doesn't stop the batch
            print(f"  FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            failed.append(path.name)

    print(f"\nDone: {len(ok)} converted, {len(skipped)} skipped, {len(failed)} failed", file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()