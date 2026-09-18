"""Validate generated JSON before it reaches storage or clients."""
import json
import re
from fastapi import HTTPException
from pydantic import ValidationError


def parse_generation(text, schema):
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    try:
        return schema.model_validate(json.loads(clean))
    except (ValueError, TypeError, ValidationError) as error:
        raise HTTPException(502, "The AI returned an incomplete response. Please try again.") from error
