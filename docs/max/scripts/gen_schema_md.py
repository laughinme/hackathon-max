"""Render docs/max/openapi/schema.yaml into a compact Markdown reference: docs/max/openapi/SCHEMA.md.

Usage (from repo root):
    uv run --with pyyaml python docs/max/scripts/gen_schema_md.py
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "openapi/schema.yaml"
OUT = ROOT / "openapi/SCHEMA.md"


def type_of(p: dict) -> str:
    if "$ref" in p:
        name = p["$ref"].split("/")[-1]
        return f"[{name}](#{name.lower()})"
    if "allOf" in p:
        return " & ".join(type_of(x) for x in p["allOf"])
    if "oneOf" in p or "anyOf" in p:
        return " | ".join(type_of(x) for x in p.get("oneOf", p.get("anyOf")))
    t = p.get("type", "object")
    if t == "array":
        return f"{type_of(p.get('items', {}))}[]"
    if "enum" in p:
        return f"{t} enum: " + ", ".join(f"`{e}`" for e in p["enum"])
    if p.get("format"):
        t += f" <{p['format']}>"
    return t


def constraints(p: dict) -> str:
    parts = []
    for k in ("minLength", "maxLength", "minimum", "maximum", "minItems", "maxItems", "pattern", "default"):
        if k in p:
            parts.append(f"{k}={p[k]!r}")
    if p.get("nullable"):
        parts.append("nullable")
    return ", ".join(parts)


def one_line(text) -> str:
    return " ".join(str(text or "").split()).replace("|", "\\|")


def render_schema(name: str, s: dict) -> list[str]:
    out = [f"### {name}", ""]
    if s.get("description"):
        out += [one_line(s["description"]), ""]
    if "discriminator" in s:
        mapping = s["discriminator"].get("mapping", {})
        out.append(f"Discriminator `{s['discriminator']['propertyName']}`:")
        out += [f"- `{k}` → {type_of({'$ref': v})}" for k, v in mapping.items()]
        out.append("")
    if "enum" in s:
        out += ["Values: " + ", ".join(f"`{e}`" for e in s["enum"]), ""]
    props, required, parents = {}, set(s.get("required", [])), []
    for part in s.get("allOf", []):
        if "$ref" in part:
            parents.append(type_of(part))
        props.update(part.get("properties", {}))
        required |= set(part.get("required", []))
    props.update(s.get("properties", {}))
    if parents:
        out += ["Extends: " + ", ".join(parents), ""]
    if props:
        out += ["| Field | Type | Req | Constraints | Description |", "|---|---|---|---|---|"]
        for field, p in props.items():
            out.append(
                f"| `{field}` | {type_of(p)} | {'✓' if field in required else ''} | "
                f"{constraints(p)} | {one_line(p.get('description'))} |"
            )
        out.append("")
    elif "type" in s and s["type"] != "object" and "enum" not in s:
        out += [f"Type: {type_of(s)} {constraints(s)}", ""]
    return out


def render_param(p: dict) -> str:
    schema = p.get("schema", {})
    return (
        f"| `{p['name']}` | {p['in']} | {type_of(schema)} | {'✓' if p.get('required') else ''} | "
        f"{constraints(schema)} | {one_line(p.get('description'))} |"
    )


def main():
    spec = yaml.safe_load(SRC.read_text())
    params = spec.get("components", {}).get("parameters", {})
    out = [
        f"# MAX Bot API — OpenAPI reference (v{spec['info']['version']})",
        "",
        "_Generated from `schema.yaml` by `scripts/gen_schema_md.py` — do not edit by hand._",
        "",
        "Base URL: `https://platform-api2.max.ru`, auth header `Authorization: <access_token>`.",
        "",
        "## Endpoints",
        "",
    ]
    for path, ops in spec["paths"].items():
        for verb, op in ops.items():
            if verb not in ("get", "post", "put", "patch", "delete"):
                continue
            out += [f"### {verb.upper()} `{path}`", ""]
            if op.get("summary"):
                out += [f"**{one_line(op['summary'])}**", ""]
            if op.get("description"):
                out += [one_line(op["description"])[:1500], ""]
            ps = [params[p["$ref"].split("/")[-1]] if "$ref" in p else p for p in op.get("parameters", [])]
            if ps:
                out += ["| Param | In | Type | Req | Constraints | Description |", "|---|---|---|---|---|---|"]
                out += [render_param(p) for p in ps]
                out.append("")
            body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
            if body:
                out += [f"Body: {type_of(body)}", ""]
            for code, resp in op.get("responses", {}).items():
                sch = resp.get("content", {}).get("application/json", {}).get("schema")
                out.append(f"- `{code}` {one_line(resp.get('description'))}" + (f" → {type_of(sch)}" if sch else ""))
            out.append("")
    out += ["## Schemas", ""]
    for name, s in spec["components"]["schemas"].items():
        out += render_schema(name, s)
    OUT.write_text("\n".join(out))
    print(f"wrote {OUT} ({len(out)} lines)")


if __name__ == "__main__":
    main()
