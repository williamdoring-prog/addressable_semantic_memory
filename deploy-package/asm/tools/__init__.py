# ASM Tools Interface

Core dispatch and rendering functions for ASM operations.

Public API:
- dispatch(request, request_fmt) — process a request dict, return (response_value, response_fmt)
- render(value, fmt) — serialize a response value to the given format
- render_request(doc, fmt) — serialize a request document to the given format
- parse_request(text, fmt) — parse a request document from the given format
- load_fragments(request, input_flag) — load store units from a path or inline array
- tool_schema(style) — get the function-calling tool definition