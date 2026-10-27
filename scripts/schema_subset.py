"""Dependency-free interpreter for the intentionally small schema vocabulary."""
from datetime import datetime
import math
import re

KEYWORDS={'$schema','title','description','type','required','properties','additionalProperties','enum','const','pattern','minLength','minItems','items','minimum','format'}
TYPE_MAP={'object':dict,'array':list,'string':str,'integer':int,'number':(int,float),'boolean':bool,'null':type(None)}

def audit_schema(schema,path='$'):
    if not isinstance(schema,dict): raise ValueError(f'{path}: schema must be an object')
    unknown=set(schema)-KEYWORDS
    if unknown: raise ValueError(f'{path}: unsupported schema keyword(s): {sorted(unknown)}')
    for key,value in schema.get('properties',{}).items(): audit_schema(value,f'{path}.properties.{key}')
    if isinstance(schema.get('items'),dict): audit_schema(schema['items'],f'{path}.items')

def validate(instance,schema,path='$'):
    errors=[]; expected=schema.get('type')
    if expected is not None:
        choices=expected if isinstance(expected,list) else [expected]; valid=False
        for choice in choices:
            typ=TYPE_MAP[choice]
            valid |= isinstance(instance,typ) and (choice not in ('integer','number') or not isinstance(instance,bool))
        if not valid: return [f'{path}: expected type {choices}']
    if 'const' in schema and instance != schema['const']: errors.append(f'{path}: expected {schema["const"]!r}')
    if 'enum' in schema and instance not in schema['enum']: errors.append(f'{path}: not in allowed values')
    if isinstance(instance,str):
        if len(instance)<schema.get('minLength',0): errors.append(f'{path}: too short')
        if 'pattern' in schema and re.fullmatch(schema['pattern'],instance) is None: errors.append(f'{path}: pattern mismatch')
        if schema.get('format')=='date-time':
            try:
                if not instance.endswith('Z'): raise ValueError
                datetime.fromisoformat(instance[:-1]+'+00:00')
            except ValueError: errors.append(f'{path}: expected UTC RFC 3339 date-time ending in Z')
    if isinstance(instance,(int,float)) and not isinstance(instance,bool) and 'minimum' in schema and instance<schema['minimum']: errors.append(f'{path}: below minimum')
    if isinstance(instance,(int,float)) and not isinstance(instance,bool) and not math.isfinite(instance): errors.append(f'{path}: number must be finite')
    if isinstance(instance,list):
        if len(instance)<schema.get('minItems',0): errors.append(f'{path}: too few items')
        if 'items' in schema:
            for index,value in enumerate(instance): errors += validate(value,schema['items'],f'{path}[{index}]')
    if isinstance(instance,dict):
        for key in schema.get('required',[]):
            if key not in instance: errors.append(f'{path}: missing {key!r}')
        properties=schema.get('properties',{})
        if schema.get('additionalProperties') is False:
            for key in instance.keys()-properties.keys(): errors.append(f'{path}: unexpected property {key!r}')
        for key,value in instance.items():
            if key in properties: errors += validate(value,properties[key],f'{path}.{key}')
    return errors
