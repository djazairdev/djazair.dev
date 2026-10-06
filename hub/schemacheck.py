"""Check a value against a JSON Schema, for the keywords ``hub/projects.schema.json`` uses
(ticket #15). Standard library only.

Supported: ``$ref`` (local, ``#/$defs/...``), ``type``, ``enum``, ``const``, ``properties``,
``required``, ``additionalProperties``, ``items``, ``minItems``, ``maxItems``, ``uniqueItems``,
``minLength``, ``maxLength``, ``pattern`` and ``format: date``. A schema that uses any other
validation keyword is refused, so the file can't silently promise a check that never runs.
Each error names the field by its path (``projects[2].category``) and says what to write
instead, using the schema's ``description`` as the hint.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

SUPPORTED = {'$schema', '$id', '$ref', '$defs', '$comment', 'title', 'description', 'examples', 'default', 'type', 'enum',
             'const', 'properties', 'required', 'additionalProperties', 'items', 'minItems', 'maxItems', 'uniqueItems',
             'minLength', 'maxLength', 'pattern', 'format'}
TYPES = {'object': dict, 'array': list, 'string': str, 'boolean': bool, 'null': type(None)}


@dataclass(frozen=True)
class Error:
    path: tuple            # ('projects', 2, 'category')
    message: str

    @property
    def where(self) -> str:
        return path_text(self.path)

    def __str__(self) -> str:
        return f'{self.where}: {self.message}' if self.path else self.message


def path_text(path: tuple) -> str:
    out = ''
    for part in path:
        out += f'[{part}]' if isinstance(part, int) else (f'.{part}' if out else part)
    return out or '(top level)'


def kind(value) -> str:
    if isinstance(value, bool):
        return 'true/false'
    if isinstance(value, int):
        return 'a number'
    if isinstance(value, float):
        return 'a number'
    if isinstance(value, str):
        return 'text'
    if isinstance(value, list):
        return 'a list'
    if isinstance(value, dict):
        return 'a mapping (key: value lines)'
    return 'nothing (an empty value)'


def show(value) -> str:
    return f'"{value}"' if isinstance(value, str) else ('true' if value is True else 'false' if value is False else
                                                         'nothing' if value is None else repr(value))


def check_schema(schema, at='#') -> None:
    """Refuse a schema that uses a keyword this checker doesn't apply."""
    if isinstance(schema, dict):
        unknown = sorted(set(schema) - SUPPORTED - {k for k in schema if k.startswith('x-')})
        if unknown:
            raise ValueError(f'{at}: unsupported schema keyword(s): {", ".join(unknown)}')
        for key, sub in schema.items():
            if key in ('properties', '$defs'):
                for name, s in sub.items():
                    check_schema(s, f'{at}/{key}/{name}')
            elif key in ('items', 'additionalProperties') and isinstance(sub, dict):
                check_schema(sub, f'{at}/{key}')


class Checker:
    def __init__(self, schema: dict):
        check_schema(schema)
        self.root = schema

    def resolve(self, schema: dict) -> dict:
        while '$ref' in schema:
            ref = schema['$ref']
            if not ref.startswith('#/'):
                raise ValueError(f'only local references are supported: {ref}')
            target = self.root
            for part in ref[2:].split('/'):
                target = target[part]
            schema = {**target, **{k: v for k, v in schema.items() if k != '$ref'}}
        return schema

    def errors(self, value, schema: dict = None, path: tuple = ()) -> list:
        schema = self.resolve(self.root if schema is None else schema)
        hint = f' {schema["description"]}' if schema.get('description') else ''
        out = []

        expected = schema.get('type')
        if expected is not None:
            types = expected if isinstance(expected, list) else [expected]
            if not any(self._is(value, t) for t in types):
                names = ' or '.join({'object': 'a mapping', 'array': 'a list', 'string': 'text', 'boolean': 'true or false',
                                     'integer': 'a whole number', 'number': 'a number', 'null': 'nothing'}[t] for t in types)
                return [Error(path, f'expected {names}, found {kind(value)}.{hint}')]

        if 'const' in schema and value != schema['const']:
            out.append(Error(path, f'must be {show(schema["const"])}, not {show(value)}.{hint}'))
        if 'enum' in schema and value not in schema['enum']:
            out.append(Error(path, f'{show(value)} is not one of: {", ".join(str(v) for v in schema["enum"])}.{hint}'))

        if isinstance(value, str):
            if 'minLength' in schema and len(value) < schema['minLength']:
                out.append(Error(path, f'is too short (at least {schema["minLength"]} characters).{hint}'))
            if 'maxLength' in schema and len(value) > schema['maxLength']:
                out.append(Error(path, f'is too long (at most {schema["maxLength"]} characters).{hint}'))
            if 'pattern' in schema and not re.search(schema['pattern'], value):
                out.append(Error(path, f'{show(value)} is not in the expected form.{hint}'))
            if schema.get('format') == 'date' and not _is_date(value):
                out.append(Error(path, f'{show(value)} is not a date written YYYY-MM-DD.{hint}'))

        if isinstance(value, list):
            if 'minItems' in schema and len(value) < schema['minItems']:
                out.append(Error(path, f'needs at least {schema["minItems"]} item{"s" if schema["minItems"] != 1 else ""}.{hint}'))
            if 'maxItems' in schema and len(value) > schema['maxItems']:
                out.append(Error(path, f'has {len(value)} items; at most {schema["maxItems"]} are allowed.{hint}'))
            if schema.get('uniqueItems'):
                seen = []
                for i, item in enumerate(value):
                    if item in seen:
                        out.append(Error(path + (i,), f'{show(item)} is listed twice.'))
                    seen.append(item)
            if isinstance(schema.get('items'), dict):
                for i, item in enumerate(value):
                    out += self.errors(item, schema['items'], path + (i,))

        if isinstance(value, dict):
            props = schema.get('properties', {})
            for key in schema.get('required', []):
                if key not in value:
                    sub = self.resolve(props.get(key, {}))
                    extra = f' {sub["description"]}' if sub.get('description') else ''
                    out.append(Error(path + (key,), f'is missing.{extra}'))
            extra_schema = schema.get('additionalProperties', True)
            for key, item in value.items():
                if key in props:
                    out += self.errors(item, props[key], path + (key,))
                elif extra_schema is False:
                    allowed = ', '.join(props)
                    note = schema.get('x-unknown', {}).get(key, f'Allowed fields: {allowed}.')
                    out.append(Error(path + (key,), f'is not a field of this entry. {note}'))
                elif isinstance(extra_schema, dict):
                    out += self.errors(item, extra_schema, path + (key,))
        return out

    @staticmethod
    def _is(value, t: str) -> bool:
        if t == 'integer':
            return isinstance(value, int) and not isinstance(value, bool)
        if t == 'number':
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        return isinstance(value, TYPES[t])


def _is_date(text: str) -> bool:
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        return False
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True
