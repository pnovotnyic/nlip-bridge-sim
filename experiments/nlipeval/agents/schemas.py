"""Turn-contract JSON Schemas for the client and server agents (stage 06).

These schemas are appended to the system prompts so models know exactly what
they must return.  They are also used by the harness to validate every model
response before acting on it.
"""

CLIENT_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ClientTurn",
    "type": "object",
    "required": ["action", "message"],
    "additionalProperties": False,
    "properties": {
        "action": {
            "type": "string",
            "enum": ["request", "answer", "confirm", "correct", "abort", "final"],
            "description": (
                "request: open the session with your intent; "
                "answer: provide a value the server asked for; "
                "confirm: approve the server's restatement; "
                "correct: revise the server's restatement; "
                "abort: end the session without a result; "
                "final: report your result to the harness (not sent to the server)"
            ),
        },
        "message": {
            "type": "string",
            "description": "Natural-language text sent to the server (empty string when action is 'final').",
        },
        "final": {
            "oneOf": [
                {
                    "type": "object",
                    "required": ["status", "explanation"],
                    "additionalProperties": False,
                    "properties": {
                        "status": {"type": "string", "enum": ["done", "declined", "unrepresentable"]},
                        "result": {},
                        "explanation": {"type": "string"},
                    },
                },
                {"type": "null"},
            ],
            "description": "Required only when action is 'final'; null otherwise.",
        },
    },
}

SERVER_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ServerTurn",
    "type": "object",
    "required": ["action", "message"],
    "additionalProperties": False,
    "properties": {
        "action": {
            "type": "string",
            "enum": ["ask", "restate", "execute", "decline", "report"],
            "description": (
                "ask: request a missing or unclear value from the client; "
                "restate: describe the call you plan to execute; "
                "execute: (NLIP-0 only) proceed directly without interaction; "
                "decline: refuse to process the request; "
                "report: report the outcome of the executed call"
            ),
        },
        "message": {
            "type": "string",
            "description": "Natural-language text sent back to the client.",
        },
        "plan": {
            "oneOf": [
                {
                    "type": "object",
                    "required": ["method", "path"],
                    "additionalProperties": True,
                    "properties": {
                        "method": {"type": "string"},
                        "path": {"type": "string",
                                 "description": "Full request path: the base path of the servers URL, then the operation path. Starts with \"/\"; no scheme or host."},
                        "body": {"type": "object"},
                    },
                },
                {"type": "null"},
            ],
            "description": "Required with 'restate' and 'execute'; null otherwise.",
        },
        "asked_fields": {
            "oneOf": [
                {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Server-version field paths that the agent is asking about.",
                },
                {"type": "null"},
            ],
            "description": "Required with 'ask'; null otherwise.",
        },
    },
}
