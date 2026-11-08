"""
LLM tool interface for ASM (ASM_DESIGN section 6 binding, WORKQUEUE T1).

A thin, deterministic adaptation layer that lets an LLM harness or agent
call ASM the way tool/function calling does - through a structured
request document in a common format - instead of the raw
`asm_main.py <file> <budget>` argv convention. Timing contracts
(internal ns, process ns) stay with `asm_main.py` / `benchmark.py`; this
layer measures nothing, it only adapts formats and dispatches ops.

Request -> response over a file, stdin, or CLI flags:

  python asm_tool.py --request req.json
  python asm_tool.py --input asm_input.txt --op serve --budget 600 \\
      --question "..." --format json
  cat req.xml | python asm_tool.py

Request document schema (unknown/extra keys are ignored):

  op       "serve" | "list" | "inspect"
  question str     (serve only; single line, verbatim)
  budget   int > 0 (serve only; unit = WORDS, rule R4)
  store    path string | list of units (or the --input CLI flag); a unit
           is {"address": str, "text": str}
  address  str     (inspect only; exactly-resolved stable ID, section 6.1)
  format   "json" | "xml" | "yaml" | "txt" — optional response format;
           the response echoes the request format unless overridden by
           the `format` key or the --format CLI flag.

Accepted request formats (the "JSON, XML, other common formats" rule):
  json  object - the standard function-calling/tool-call payload
  xml   any element tree whose nested structure mirrors the schema;
        arrays render as repeated <item> children under the key element
        and an element whose children are ALL <item> tags reads back as
        a list (schema keys never collide with the reserved 'item' tag)
  yaml  the double-quoted-scalar block SUBSET (below); unsupported yaml
        fails through honestly to a format_parse error, never guessed
  toml  via tomllib (Python 3.11+; on older runtimes the response is an
        honest unsupported_runtime error - never a hand-rolled parser)
  csv   ONE flat request: header row + one data row (via csv module -
        quoted commas in question texts round-trip); csv is
        REQUEST-ONLY (nested stores don't fit rows); responses default
        to json (list accepts ?format=csv address rows)
  txt   plain "key value" lines

LLM-harness binding: `python asm_tool.py --schema [openai|anthropic|
jsonschema]` prints the tool-for-function-calling definition
(name "asm", op enum, WORD-budget parameter) so any harness can bind
this CLI directly; the suite commits results/tool_schema.json.

yaml subset: indent = 2 spaces; `key: value` scalars, or `key:` with the
child block on following lines at deeper indent; sequences as `- item`
or `- key: value` with that item's remaining pairs on following lines at
deeper indent; full-line `#` comments only; TABs rejected; single-line
scalars; double-quoted scalars decode exactly like JSON strings (so \\n
escapes round-trip) and every emitted string IS double-quoted; ints
match ^-?[0-9]+$.

Responses by format:
  json - json.dumps (serve is byte-identical with `asm_main.py` stdout
         for the same store + budget); xml as <asm_response>...</>;
  yaml - the same subset (all strings double-quoted);
  toml - key = value scalars, arrays inline, [[key]] array-of-tables
         for selected/inline-store units (tomllib 3.11+ on emit side is
         not required: emission is deterministic and subset-checked);
  txt:
    serve   -> the served context text (what a model would read)
    list    -> one address per line
    inspect -> the unit text
    error   -> "error <code>: <message>" single line
  csv   -> list: address header + rows (explicit `format: csv` only)
Structured errors render as {"error": {"code", "message"}} in
json/xml/yaml/toml (txt/csv single-line) and exit 1; success exits 0.

Ops (DESIGN section 6 mapping, flat-store boundary of the current
reference implementation):
  serve    rank + select under a WORD budget (section 7 assembly)
  list     every stored address, file order (stable IDs, section 6.1)
  inspect  exact-ID resolve of one address to verbatim text + word count
  expand   reports unsupported_op: this store has no abstraction ladder
           yet (section 5.2 ladder is future work); per section 6.2 the
           response reports the gap explicitly instead of faking it.
"""

import argparse
import csv
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from asm import ASM, Fragment, WORD_RE
from asm_main import unescape

try:  # tomllib is stdlib from 3.11 on; older runtimes error honestly
    import tomllib
    _HAS_TOMLLIB = True
except ImportError:  # Python 3.10: keep the surface, gate the format
    tomllib = None
    _HAS_TOMLLIB = False

SUPPORTED_FORMATS = ("json", "xml", "yaml", "toml", "csv", "txt")
RESPONSE_FORMATS = ("json", "xml", "yaml", "toml", "txt", "csv")
SUPPORTED_OPS = ("serve", "list", "inspect")

TOOL_NAME = "asm"
TOOL_DESCRIPTION = (
    "Deterministic Addressable Semantic Memory (ASM) retrieval over a "
    "flat addressed store. ops: serve = rank + select units under a WORD "
    "budget (needs question + budget + store); list = every stored "
    "address in file order (needs store); inspect = resolve one address "
    "to verbatim text + word count (needs address + store). Ladder ops "
    "(expand) are reported as unsupported_op by this reference "
    "implementation, never approximated.")

_TXT_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_YAML_INT_RE = re.compile(r"^-?[0-9]+$")


class ToolError(Exception):
    """Tool-level failure with a stable, structured code."""

    def __init__(self, code, message):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def error_document(code, message):
    return {"error": {"code": code, "message": message}}


# ------------------------------------------------------------- requests ---

def detect_format(text):
    """Prefix-sniff the request format; everything else errors."""
    stripped = text.strip()
    if not stripped:
        raise ToolError("format_parse", "empty request document")
    first = stripped[0]
    if first == "{":
        return "json"
    if first == "<":
        return "xml"
    if first == "-" or re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:", stripped):
        return "yaml"
    first_line = stripped.split("\n", 1)[0].strip()
    if "," in first_line and all(
            _TXT_KEY_RE.match(chunk) for chunk in first_line.split(",")):
        return "csv"
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=\s", first_line):
        return "toml"
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s+\S", stripped):
        return "txt"
    raise ToolError(
        "format_parse",
        "cannot detect format: use --format "
        "{json,xml,yaml,toml,csv,txt}")


def parse_request(text, fmt=None):
    """Parse a request document to a dict; malformed input raises
    ToolError('format_parse', ...) - never a silent guess."""
    fmt = fmt or detect_format(text)
    if fmt not in SUPPORTED_FORMATS:
        raise ToolError("invalid_format", f"unknown format: {fmt}")
    if fmt == "json":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as err:
            raise ToolError("format_parse",
                            f"invalid json: {err.msg} at char {err.pos}") \
                from err
        if not isinstance(parsed, dict):
            raise ToolError("format_parse", "json request must be an object")
        return parsed
    if fmt == "xml":
        try:
            root = ET.fromstring(text)
        except ET.ParseError as err:
            raise ToolError("format_parse",
                            f"invalid xml: {err.msg or err}") from err
        return _xml_to_obj(root)
    if fmt == "yaml":
        return _yaml_document(text)
    if fmt == "toml":
        if not _HAS_TOMLLIB:
            raise ToolError(
                "unsupported_runtime",
                "toml requests need Python 3.11+ stdlib tomllib; this "
                "runtime lacks it - use json, xml, yaml, csv, or txt")
        try:
            parsed = tomllib.loads(text)
        except tomllib.TOMLDecodeError as err:
            raise ToolError("format_parse", f"invalid toml: {err}") from err
        return parsed
    if fmt == "csv":
        return _csv_document(text)
    return _txt_document(text)


def _xml_to_obj(element):
    children = list(element)
    if children and all(child.tag == "item" for child in children):
        # documented list convention: an element whose children are ALL
        # <item> tags reads back as a plain list (response/list styles)
        return [_xml_to_obj(child) for child in children]
    if not children:
        return element.text if element.text is not None else ""
    tag_groups = {}
    order = []
    for child in children:
        if child.tag not in tag_groups:
            tag_groups[child.tag] = []
            order.append(child.tag)
        tag_groups[child.tag].append(_xml_to_obj(child))
    parsed = {}
    for tag in order:
        values = tag_groups[tag]
        parsed[tag] = values[0] if len(values) == 1 else values
    return parsed


def _txt_document(text):
    document = {}
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(" ")
        if not sep or not _TXT_KEY_RE.match(key):
            raise ToolError("format_parse",
                            f"txt requests need 'key value' lines, got: "
                            f"{line[:40]!r}")
        if key in document:
            raise ToolError("format_parse", f"duplicate txt key: {key}")
        document[key] = value.strip()
    if not document:
        raise ToolError("format_parse", "empty txt request")
    return document


# ------------------------------------------------- yaml (documented subset)

def _yaml_scalar(raw, where):
    text = raw.strip()
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            raise ToolError("format_parse",
                            f"bad double-quoted scalar ({where}): "
                            f"{err.msg}") from err
    if _YAML_INT_RE.fullmatch(text):
        return int(text)
    return text


def _yaml_lines(text):
    rendered = []
    for line in text.split("\n"):
        compact = line.rstrip()
        if not compact.strip() or compact.strip().startswith("#"):
            continue
        if "\t" in compact:
            raise ToolError("format_parse",
                            "TAB is not allowed in the yaml subset")
        rendered.append((len(compact) - len(compact.lstrip(" ")),
                         compact.strip()))
    if not rendered:
        raise ToolError("format_parse", "empty yaml request")
    return rendered


def _yaml_pair(content, where):
    key, sep, raw_value = content.partition(":")
    if not sep or not _TXT_KEY_RE.match(key.strip()):
        raise ToolError(
            "format_parse",
            f"yaml subset needs 'key: value' pairs ({where}): "
            f"{content[:40]!r}")
    if raw_value.strip() == "":
        return key.strip(), None
    return key.strip(), raw_value.strip()


def _next_indent(lines, index, parent_indent):
    if index < len(lines) and lines[index][0] > parent_indent:
        return lines[index][0]
    raise ToolError("format_parse", "'key:' with no indented child block")


def _yaml_value(lines, index, indent, is_sequence=False):
    """Parse one block (mapping or sequence) starting at lines[index];
    returns (value, next_index)."""
    value = [] if is_sequence else {}
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise ToolError("format_parse",
                            f"unexpected indent on: {content[:40]!r}")
        if content.startswith("- "):
            if not is_sequence:
                raise ToolError(
                    "format_parse",
                    f"sequence item {content[2:10]!r} inside a mapping "
                    "block")
            item_content = content[1:].strip()
            index += 1
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:\s", item_content) \
                    or re.match(r"^[A-Za-z_][A-Za-z0-9_]*:$", item_content):
                key, raw = _yaml_pair(item_content, "sequence item")
                item = {key: _yaml_scalar(raw, f"item {key}")}
                while index < len(lines) and lines[index][0] == indent + 2 \
                        and not lines[index][1].startswith("- "):
                    pair_key, pair_raw = _yaml_pair(lines[index][1],
                                                    "sequence item pair")
                    if pair_raw is None:
                        raise ToolError(
                            "format_parse",
                            f"bare key {pair_key} in sequence item")
                    item[pair_key] = _yaml_scalar(pair_raw, f"item {pair_key}")
                    index += 1
                value.append(item)
            else:
                if index < len(lines) and lines[index][0] > indent:
                    extended, index = _yaml_value(lines, index,
                                                  lines[index][0],
                                                  is_sequence=True)
                    value.append(extended)
                else:
                    value.append(_yaml_scalar(item_content, "sequence item"))
            continue
        if content == "-":
            raise ToolError("format_parse", "bare '-' sequence marker")
        if is_sequence:
            raise ToolError("format_parse",
                            f"mapping line {content[:10]!r} in a sequence "
                            "block")
        key, raw_value = _yaml_pair(content, "mapping line")
        if raw_value is None:
            child_indent = _next_indent(lines, index + 1, indent)
            is_child_sequence = lines[index + 1][1].startswith("- ")
            child, index = _yaml_value(lines, index + 1, child_indent,
                                       is_sequence=is_child_sequence)
            value[key] = child
        else:
            value[key] = _yaml_scalar(raw_value, f"key {key!r}")
            index += 1
    if not value:
        raise ToolError("format_parse", "empty mapping or sequence block")
    return value, index


def _yaml_document(text):
    lines = _yaml_lines(text)
    if lines[0][1].startswith("- "):
        value, index = _yaml_value(lines, 0, lines[0][0], is_sequence=True)
    else:
        value, index = _yaml_value(lines, 0, lines[0][0])
    if index != len(lines):
        raise ToolError("format_parse", "stray trailing yaml lines")
    return value


# --------------------------------------------------- csv (flat requests) --

def _csv_document(text):
    """One flat request per document: header row with valid keys, exactly
    one data row; the csv module handles quoted commas in question
    text. Nested values (inline stores) belong in json/xml/yaml/toml."""
    rows = [row for row in csv.reader(io.StringIO(text))
            if any(cell.strip() for cell in row)]
    if not rows:
        raise ToolError("format_parse", "empty csv request")
    if len(rows) != 2:
        raise ToolError(
            "format_parse",
            f"csv requests carry a header row + exactly ONE data row, "
            f"got {len(rows)} rows")
    header = [cell.strip() for cell in rows[0]]
    for name in header:
        if not name or not _TXT_KEY_RE.match(name):
            raise ToolError("format_parse",
                            f"invalid csv header key: {name!r}")
    data = [cell.strip() for cell in rows[1]]
    if len(data) != len(header):
        raise ToolError(
            "format_parse",
            f"csv data row has {len(data)} cells, header has "
            f"{len(header)}")
    document = {}
    for key, value in zip(header, data):
        if key in document:
            raise ToolError("format_parse", f"duplicate csv key: {key}")
        document[key] = value
    return document


# ------------------------------------------- toml (tomllib-gated, subset) --

def render_toml(value):
    """Deterministic TOML emission for the tool document shapes:
    key = value pairs first, then inline scalar arrays, then
    [[key]] array-of-tables / [key] sub-tables for nested units."""
    if isinstance(value, list):
        return render_toml({"addresses": value})
    if not isinstance(value, dict):
        raise ToolError("render_error",
                        f"toml cannot render a bare {type(value).__name__}")
    simple = []
    tables = []
    array_tables = []
    for key, item in value.items():
        if isinstance(item, dict):
            tables.append((key, item))
        elif isinstance(item, list):
            if item and all(isinstance(entry, dict) for entry in item):
                array_tables.append((key, item))
            else:
                joined = ", ".join(_toml_scalar(entry) for entry in item)
                simple.append(f"{key} = [{joined}]")
        else:
            simple.append(f"{key} = {_toml_scalar(item)}")
    rendered = list(simple)
    for key, entries in tables:
        rendered.append(f"[{key}]")
        for sub_key, sub in entries.items():
            if isinstance(sub, (dict, list)):
                raise ToolError(
                    "render_error",
                    f"toml sub-table {key}.{sub_key} nesting is not used "
                    "by the tool document shapes")
            rendered.append(f"{sub_key} = {_toml_scalar(sub)}")
    for key, entries in array_tables:
        for entry in entries:
            rendered.append("")
            rendered.append(f"[[{key}]]")
            for sub_key, sub in entry.items():
                rendered.append(f"{sub_key} = {_toml_scalar(sub)}")
    return "\n".join(rendered) + "\n"


def _toml_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        raise ToolError("render_error", "toml emits no float fields here")
    if value is None:
        raise ToolError("render_error", "toml has no null; use json")
    return json.dumps(value)


# ------------------------------------------------------------- renderers ---

def render_json(value):
    return json.dumps(value)


def render_xml(value):
    root = _xml_string("asm_response", value)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


def _xml_string(tag, value):
    element = ET.Element(tag)
    if isinstance(value, dict):
        for key, item in value.items():
            element.append(_xml_string(_tag_for(key), item))
    elif isinstance(value, list):
        for item in value:
            element.append(_xml_string("item", item))
    else:
        element.text = "" if value is None else str(value)
    return element


def _tag_for(key):
    key = re.sub(r"[^A-Za-z0-9_.-]", "_", str(key))
    if not re.match(r"^[A-Za-z_]", key):
        key = "u" + key
    return key


def render_yaml(value):
    return "\n".join(_yaml_lines_render(value, 0))


def _yaml_lines_render(value, depth):
    pad = " " * depth
    rendered = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                rendered.append(f"{pad}{key}:")
                rendered.extend(_yaml_lines_render(item, depth + 2))
            else:
                rendered.append(f"{pad}{key}: {_yaml_scalar_render(item)}")
        return rendered
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                entries = list(item.items())
                first_key, first_value = entries[0]
                rendered.append(f"{pad}- {first_key}: "
                                f"{_yaml_scalar_render(first_value)}")
                for entry_key, entry_value in entries[1:]:
                    if isinstance(entry_value, (dict, list)):
                        rendered.append(f"{pad}  {entry_key}:")
                        rendered.extend(
                            _yaml_lines_render(entry_value, depth + 4))
                    else:
                        rendered.append(f"{pad}  {entry_key}: "
                                        f"{_yaml_scalar_render(entry_value)}")
            else:
                rendered.append(f"{pad}- {_yaml_scalar_render(item)}")
        return rendered
    raise ToolError("render_error", "a bare scalar cannot be a document")


def _yaml_scalar_render(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(value)  # double-quoted, JSON-compatible scalar


def render_txt(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(str(entry) for entry in value)
    if isinstance(value, dict):
        if "error" in value:
            return (f"error {value['error']['code']}: "
                    f"{value['error']['message']}")
        if "context" in value:
            return value["context"]
        if "text" in value:
            return value["text"]
    raise ToolError("render_error", f"no txt rendering for {type(value)}")


def render_csv(value):
    """csv responses carry tabular data only: list -> address rows
    (explicit `format: csv`), errors -> code/message rows; serve and
    inspect have no row shape, so they refuse honestly."""
    if isinstance(value, dict) and "error" in value:
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["code", "message"])
        writer.writerow([value["error"]["code"],
                         value["error"]["message"]])
        return buffer.getvalue().rstrip("\n")
    if isinstance(value, list):
        if any(not isinstance(entry, str) for entry in value):
            raise ToolError("render_error",
                            "csv list rows are addresses; nested data use "
                            "json/xml/yaml/toml")
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["address"])
        for entry in value:
            writer.writerow([entry])
        return buffer.getvalue().rstrip("\n")
    raise ToolError(
        "render_error",
        "csv responses are address rows or error rows only; serve/inspect "
        "read back as json/xml/yaml/toml/txt")


def render_request(doc, fmt):
    """Serialize a request document in the given format (the inverse of
    parse_request). txt/csv requests are flat - inline unit stores need
    json/xml/yaml/toml."""
    if fmt == "txt":
        lines = []
        for key, value in doc.items():
            if isinstance(value, (dict, list)):
                raise ToolError(
                    "invalid_format",
                    f"txt requests cannot carry nested values ({key}); "
                    "use json, xml, yaml, or toml")
            lines.append(f"{key} {value}")
        return "\n".join(lines)
    if fmt == "xml":
        element = _xml_string("asm_request", doc)
        ET.indent(element, space="  ")
        return ET.tostring(element, encoding="unicode")
    if fmt == "csv":
        for key, value in doc.items():
            if isinstance(value, (dict, list)):
                raise ToolError(
                    "invalid_format",
                    f"csv requests are flat; nested value in {key} - "
                    "use json, xml, yaml, or toml")
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(list(doc.keys()))
        writer.writerow([str(entry) for entry in doc.values()])
        return buffer.getvalue()
    if fmt == "toml":
        return render_toml(doc)
    return render(doc, fmt)


def render(value, fmt):
    if fmt == "json":
        return render_json(value)
    if fmt == "xml":
        return render_xml(value)
    if fmt == "yaml":
        return render_yaml(value)
    if fmt == "toml":
        return render_toml(value)
    if fmt == "csv":
        return render_csv(value)
    if fmt == "txt":
        return render_txt(value)
    raise ToolError("invalid_format", f"unknown response format: {fmt}")


# ----------------------------------------------------------------- store ---

def tool_schema(style="openai"):
    """The function-calling tool definition that binds this CLI:
    openai (tool object), anthropic (tool_use), or jsonschema (bare
    parameter schema). Ladder ops stay out of the enum; their
    unsupported_op behavior is in the description, per DESIGN 6.2."""
    if style not in ("openai", "anthropic", "jsonschema"):
        raise ToolError("invalid_format",
                        f"unknown schema style: {style}")
    parameters = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "op": {
                "type": "string",
                "enum": list(SUPPORTED_OPS),
                "description": "serve/list/inspect (flat-store reference)",
            },
            "question": {
                "type": "string",
                "description": "serve only: the task query, one line",
            },
            "budget": {
                "type": "integer",
                "minimum": 1,
                "description": "serve only: WORD budget (rule R4), "
                               "never tokens",
            },
            "store": {
                "oneOf": [
                    {"type": "string",
                     "description": "path to an asm_input.txt-format store"},
                    {"type": "array",
                     "items": {
                         "type": "object",
                         "required": ["address", "text"],
                         "properties": {
                             "address": {"type": "string"},
                             "text": {"type": "string"},
                         },
                     }},
                ],
                "description": "the addressed corpus: file path or inline "
                               "units {address, text}",
            },
            "address": {
                "type": "string",
                "description": "inspect only: stable unit ID (section 6.1)",
            },
            "format": {
                "type": "string",
                "enum": ["json", "xml", "yaml", "toml", "csv", "txt"],
                "description": "response format; default echoes the "
                               "request format (json for csv)",
            },
        },
        "required": ["op"],
    }
    if style == "openai":
        return {"type": "function",
                "function": {"name": TOOL_NAME,
                             "description": TOOL_DESCRIPTION,
                             "parameters": parameters}}
    if style == "anthropic":
        return {"name": TOOL_NAME,
                "description": TOOL_DESCRIPTION,
                "input_schema": parameters}
    return parameters


def load_fragments(request, input_flag):
    """Store = inline unit list, or a path to asm_input.txt-format text
    (line 1 = question, line 2 = default budget, then address<TAB>text).
    Returns fragments only: question/budget must come from the REQUEST,
    never from the store, so identical requests serve identically on any
    store."""
    store = input_flag if input_flag is not None else request.get("store")
    if store is None:
        raise ToolError("no_store",
                        "request has no store (units array or path) and "
                        "no --input flag")
    if isinstance(store, list):
        fragments = []
        for unit in store:
            if not isinstance(unit, dict) or "address" not in unit \
                    or "text" not in unit:
                raise ToolError("invalid_store",
                                "inline store units need address+text keys")
            fragments.append(Fragment(str(unit["address"]),
                                      str(unit["text"])))
        return fragments
    if not isinstance(store, str):
        raise ToolError("invalid_store", "store must be a path or unit array")
    try:
        raw = Path(store).read_text(encoding="utf-8")
    except OSError:
        raise ToolError("store_not_found",
                        f"store file not found or unreadable: {store}") \
            from None
    fragments = []
    for line in raw.split("\n")[2:]:
        line = line.rstrip("\r")
        if not line or "\t" not in line:
            continue
        address, unit_text = line.split("\t", 1)
        fragments.append(Fragment(address, unit_text))
    return fragments


# ------------------------------------------------------------- dispatch ---

def _coerce_budget(raw):
    if isinstance(raw, bool):
        raise ToolError("invalid_budget",
                        "budget must be a positive integer (WORDS, rule R4); "
                        f"got {raw!r}")
    if isinstance(raw, int):
        budget = raw
    elif isinstance(raw, str) and _YAML_INT_RE.fullmatch(raw.strip()):
        budget = int(raw.strip())
    else:
        raise ToolError("invalid_budget",
                        "budget must be a positive integer (WORDS, rule R4); "
                        f"got {raw!r}")
    if budget <= 0:
        raise ToolError("invalid_budget",
                        f"budget must be >= 1 (WORDS, rule R4); got {budget}")
    return budget


def dispatch(request, request_fmt, input_flag=None):
    """Validate + execute one request; returns (response_value, fmt).
    csv requests answer in json by default (csv is request-only; rows
    exist for the list/error shapes), so identical csv and json requests
    produce identical served contexts."""
    response_fmt = request.get("format") or (
        request_fmt if request_fmt != "csv" else "json")
    if response_fmt not in RESPONSE_FORMATS:
        raise ToolError("invalid_format",
                        f"unknown response format: {response_fmt}")

    op = request.get("op")
    if not isinstance(op, str):
        raise ToolError("invalid_op", f"op must be a string, got {op!r}")
    if op not in SUPPORTED_OPS:
        raise ToolError(
            "unsupported_op",
            f"op {op!r} is not available in the flat-store reference "
            f"implementation; supported ops: {', '.join(SUPPORTED_OPS)}; "
            "ladder ops (expand, list-of-ladder) are queued in WORKQUEUE "
            "T1 until the abstraction ladder exists")

    if op == "serve":
        question = request.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ToolError("missing_question",
                            "serve needs a non-empty question string")
        budget = _coerce_budget(request.get("budget"))
        fragments = load_fragments(request, input_flag)
        value = ASM().run(question, fragments, budget)
    elif op == "list":
        fragments = load_fragments(request, input_flag)
        value = [fragment.address for fragment in fragments]
    else:  # inspect
        address = request.get("address")
        if not isinstance(address, str) or not address:
            raise ToolError("missing_address",
                            "inspect needs an address string (section 6.1)")
        fragments = load_fragments(request, input_flag)
        for fragment in fragments:
            if fragment.address == address:
                value = {
                    "address": address,
                    "text": fragment.text,
                    "words": len(WORD_RE.findall(fragment.text)),
                }
                break
        else:
            raise ToolError(
                "address_not_found",
                f"no stored unit resolves address {address!r}; per section "
                "6.2 report the gap, do not guess")
    return value, response_fmt


def parse_response(text, fmt):
    """Parse a structured response document back to Python (the inverse
    of render for json/xml/yaml/toml/csv; txt responses are display text
    and are not machine-parsed). toml top-level arrays read back under
    the documented `addresses` key; csv reads back header-sized rows."""
    if fmt == "txt":
        raise ToolError("parse_response",
                        "txt responses are display text, not machine-parsed")
    if fmt == "json":
        return json.loads(text)
    if fmt == "yaml":
        return _yaml_document(text)
    if fmt == "toml":
        if not _HAS_TOMLLIB:
            raise ToolError("unsupported_runtime",
                            "toml responses need tomllib (Python 3.11+)")
        return tomllib.loads(text)
    if fmt == "csv":
        rows = [row for row in csv.reader(io.StringIO(text))
                if any(cell.strip() for cell in row)]
        header = [cell.strip() for cell in rows[0]]
        if header == ["address"]:
            return [row[0].strip() for row in rows[1:]]
        if header == ["code", "message"] and len(rows) == 2:
            return {"error": {"code": rows[1][0].strip(),
                              "message": rows[1][1].strip()}}
        raise ToolError("parse_response",
                        f"csv parse handles address or code/message "
                        f"columns, got {header}")
    root = ET.fromstring(text)
    if root.tag != "asm_response":
        raise ToolError("parse_response", f"unexpected xml root: {root.tag}")
    return _xml_to_obj(root)


# ----------------------------------------------------------------- CLI ---

def build_flag_request(request, args):
    """CLI flags override document fields, only where explicitly given."""
    if args.op:
        request["op"] = args.op
    if args.question is not None:
        request["question"] = args.question
    if args.address is not None:
        request["address"] = args.address
    if args.budget is not None:
        request["budget"] = args.budget
    if args.store is not None:
        request["store"] = args.store
    if args.format:
        request["format"] = args.format
    return request


def _emit_error(err, fmt):
    print(render(error_document(err.code, err.message), fmt))
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="ASM LLM tool interface (DESIGN section 6; WORKQUEUE T1)",
        epilog="Formats: json xml yaml toml csv txt. Ops: serve list "
               "inspect. --schema emits the function-calling tool "
               "definition. Exit 0 ok; exit 1 prints the structured "
               "error document.")
    parser.add_argument("--request",
                        help="request document file (format detected)")
    parser.add_argument("--op", choices=SUPPORTED_OPS + ("expand",),
                        help="operation for flag-built requests")
    parser.add_argument("--question")
    parser.add_argument("--budget", type=int)
    parser.add_argument("--address")
    parser.add_argument("--store", help="store path (inline or file)")
    parser.add_argument("--input", dest="store", help="store path alias")
    parser.add_argument("--format", choices=RESPONSE_FORMATS,
                        help="response format override ONLY (default = "
                             "request format; json for csv/flag-built "
                             "requests); the request format is sniffed")
    parser.add_argument(
        "--schema", nargs="?", const="openai",
        choices=("openai", "anthropic", "jsonschema"),
        help="print the LLM function-calling tool definition instead of "
             "executing a request (default style: openai)")
    args = parser.parse_args(argv)

    if args.schema:
        try:
            print(render(tool_schema(args.schema), "json"))
            return 0
        except ToolError as err:
            return _emit_error(err, "json")

    request_fmt = args.format or "json"
    if args.request:
        try:
            text = Path(args.request).read_text(encoding="utf-8")
            # NOTE: --format is the response-format override only; the
            # request format is always sniffed from the document itself.
            request_fmt = detect_format(text)
            request = parse_request(text, request_fmt)
        except ToolError as err:
            return _emit_error(err, args.format or "json")
    elif args.op:
        request = {"op": args.op}
    else:
        text = sys.stdin.read()
        if not text.strip():
            return _emit_error(
                ToolError("no_request",
                          "no --request file, no --op flags, and empty "
                          "stdin (one request document per invocation)"),
                "json")
        try:
            request_fmt = detect_format(text)
            request = parse_request(text, request_fmt)
        except ToolError as err:
            return _emit_error(err, args.format or "json")

    request = build_flag_request(request, args)
    try:
        value, response_fmt = dispatch(request, request_fmt,
                                       input_flag=None)
    except ToolError as err:
        return _emit_error(err, request.get("format")
                           or request_fmt)
    try:
        print(render(value, response_fmt))
    except ToolError as err:
        return _emit_error(err, response_fmt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
