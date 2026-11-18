"""Pure-Python compatibility implementation for protobuf3-to-dict.

The PyPI release protobuf3-to-dict 0.1.5 is published as a source archive
only. This local distribution keeps the expected distribution/import names
available to Chaquopy 17+, which installs index packages as wheels only.

The implementation delegates protobuf wire-format conversion to Google's
official json_format helpers, and provides the common API exported by the
original package.
"""

import datetime
import inspect

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.json_format import MessageToDict, ParseDict

__all__ = [
    "protobuf_to_dict", "TYPE_CALLABLE_MAP", "dict_to_protobuf",
    "REVERSE_TYPE_CALLABLE_MAP", "datetime_to_timestamp",
    "timestamp_to_datetime", "get_field_names_and_options",
    "FieldsMissing", "validate_dict_for_required_pb_fields",
]

TYPE_CALLABLE_MAP = {
    FieldDescriptor.TYPE_DOUBLE: float,
    FieldDescriptor.TYPE_FLOAT: float,
    FieldDescriptor.TYPE_INT32: int,
    FieldDescriptor.TYPE_INT64: int,
    FieldDescriptor.TYPE_UINT32: int,
    FieldDescriptor.TYPE_UINT64: int,
    FieldDescriptor.TYPE_SINT32: int,
    FieldDescriptor.TYPE_SINT64: int,
    FieldDescriptor.TYPE_FIXED32: int,
    FieldDescriptor.TYPE_FIXED64: int,
    FieldDescriptor.TYPE_SFIXED32: int,
    FieldDescriptor.TYPE_SFIXED64: int,
    FieldDescriptor.TYPE_BOOL: bool,
    FieldDescriptor.TYPE_STRING: str,
    FieldDescriptor.TYPE_BYTES: bytes,
    FieldDescriptor.TYPE_ENUM: int,
}
REVERSE_TYPE_CALLABLE_MAP = {}
EXTENSION_CONTAINER = "___X"

def datetime_to_timestamp(value):
    result = Timestamp()
    result.FromDatetime(value)
    return result

def timestamp_to_datetime(value):
    return value.ToDatetime()

def _lower_enum_values(message):
    """Convert enum integer values to lowercase names recursively."""
    result = {}
    for field, value in message.ListFields():
        if field.label == FieldDescriptor.LABEL_REPEATED:
            if field.type == FieldDescriptor.TYPE_ENUM:
                result[field.name] = [field.enum_type.values_by_number[int(v)].name.lower() for v in value]
            elif field.type == FieldDescriptor.TYPE_MESSAGE:
                result[field.name] = [_lower_enum_values(v) for v in value]
            else:
                result[field.name] = list(value)
        elif field.type == FieldDescriptor.TYPE_ENUM:
            result[field.name] = field.enum_type.values_by_number[int(value)].name.lower()
        elif field.type == FieldDescriptor.TYPE_MESSAGE:
            if field.message_type and field.message_type.name == "Timestamp":
                result[field.name] = timestamp_to_datetime(value)
            else:
                result[field.name] = _lower_enum_values(value)
        elif field.type == FieldDescriptor.TYPE_BYTES:
            result[field.name] = value
        else:
            result[field.name] = value
    return result

def protobuf_to_dict(pb, type_callable_map=None, use_enum_labels=False,
                     including_default_value_fields=False,
                     lowercase_enum_lables=False, lowercase_enum_labels=False):
    """Convert a protobuf Message into a Python dictionary."""
    if not isinstance(pb, Message):
        raise TypeError("pb must be a google.protobuf.message.Message")
    if use_enum_labels:
        result = _lower_enum_values(pb)
        if lowercase_enum_lables or lowercase_enum_labels:
            return result
        # Restore canonical enum labels when lowercasing was not requested.
        return MessageToDict(pb, preserving_proto_field_name=True,
                             use_integers_for_enums=False)
    kwargs = {"preserving_proto_field_name": True, "use_integers_for_enums": True}
    params = inspect.signature(MessageToDict).parameters
    if including_default_value_fields:
        if "always_print_fields_with_no_presence" in params:
            kwargs["always_print_fields_with_no_presence"] = True
        elif "including_default_value_fields" in params:
            kwargs["including_default_value_fields"] = True
    return MessageToDict(pb, **kwargs)

def dict_to_protobuf(pb_klass_or_instance, values, type_callable_map=None,
                     strict=True, ignore_none=False, **kwargs):
    """Populate a protobuf message from a dictionary."""
    if isinstance(pb_klass_or_instance, Message):
        instance = pb_klass_or_instance
    else:
        instance = pb_klass_or_instance()
    if ignore_none:
        values = {key: value for key, value in values.items() if value is not None}
    return ParseDict(values, instance, ignore_unknown_fields=not strict)

def get_field_names_and_options(pb):
    """Yield protobuf fields with their custom options."""
    descriptor = getattr(pb, "DESCRIPTOR", None)
    if descriptor is None and hasattr(pb, "__class__"):
        descriptor = getattr(pb.__class__, "DESCRIPTOR", None)
    if descriptor is None:
        raise TypeError("pb must be a protobuf message or message class")
    for field in descriptor.fields:
        options = {}
        try:
            for option_field, value in field.GetOptions().ListFields():
                options[option_field.name] = value
        except Exception:
            pass
        yield field, field.name, options

class FieldsMissing(ValueError):
    """Raised when a required protobuf field is missing from a dictionary."""

def validate_dict_for_required_pb_fields(pb, dic):
    missing = [name for _, name, options in get_field_names_and_options(pb)
               if not options.get("is_optional", False) and name not in dic]
    if missing:
        raise FieldsMissing("Missing fields: " + ", ".join(missing))
