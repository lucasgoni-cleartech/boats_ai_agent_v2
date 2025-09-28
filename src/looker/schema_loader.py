"""
Schema loader for Looker explore definitions.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExploreSchemaLoader:
    """Loader for Looker explore schema definitions."""

    def __init__(self, schema_path: str = None):
        """Initialize schema loader."""
        if schema_path is None:
            # Default to config directory
            schema_path = Path(__file__).parent.parent.parent / "config" / "consumer_sessions_explore.json"

        self.schema_path = Path(schema_path)
        self._cached_schema: Optional[Dict[str, Any]] = None
        logger.info(f"ExploreSchemaLoader initialized with schema: {self.schema_path}")

    def load_schema(self) -> Dict[str, Any]:
        """
        Load the explore schema from JSON file.

        Returns:
            Dictionary with explore schema information
        """
        if self._cached_schema is not None:
            return self._cached_schema

        try:
            with open(self.schema_path, 'r') as file:
                schema = json.load(file)

            # Validate required fields
            required_fields = ["explore", "model", "filters"]
            for field in required_fields:
                if field not in schema:
                    raise ValueError(f"Missing required field '{field}' in schema")

            self._cached_schema = schema

            logger.info("Schema loaded successfully", extra={
                "model": schema.get("model"),
                "explore": schema.get("explore"),
                "filters_count": len(schema.get("filters", [])),
                "measures_count": len(schema.get("measures", []))
            })

            return schema

        except FileNotFoundError:
            logger.error(f"Schema file not found: {self.schema_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in schema file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading schema: {e}")
            raise

    def get_available_fields(self) -> List[str]:
        """Get list of available field names."""
        schema = self.load_schema()

        # Get dimension fields from filters
        dimension_fields = [f.get("field_name", f.get("name", "")) for f in schema.get("filters", [])]

        # Get measure fields
        measure_fields = [m.get("field_name", m.get("name", "")) for m in schema.get("measures", [])]

        return dimension_fields + measure_fields

    def get_available_dimensions(self) -> List[Dict[str, Any]]:
        """Get list of available dimensions with metadata."""
        schema = self.load_schema()
        return schema.get("filters", [])

    def get_available_measures(self) -> List[Dict[str, Any]]:
        """Get list of available measures with metadata."""
        schema = self.load_schema()
        return schema.get("measures", [])

    def get_field_info(self, field_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific field."""
        schema = self.load_schema()

        # Check in dimensions (filters)
        for field in schema.get("filters", []):
            if field.get("field_name", field.get("name", "")) == field_name:
                return field

        # Check in measures
        for field in schema.get("measures", []):
            if field.get("field_name", field.get("name", "")) == field_name:
                return field

        return None

    def get_field_type(self, field_name: str) -> Optional[str]:
        """Get the type of a specific field."""
        field_info = self.get_field_info(field_name)
        if field_info:
            return field_info.get("type")
        return None

    def get_field_label(self, field_name: str) -> Optional[str]:
        """Get the human-readable label for a field."""
        field_info = self.get_field_info(field_name)
        if field_info:
            return field_info.get("label")
        return None

    def is_date_field(self, field_name: str) -> bool:
        """Check if a field is a date type."""
        field_type = self.get_field_type(field_name)
        return field_type == "date" if field_type else False

    def is_yesno_field(self, field_name: str) -> bool:
        """Check if a field is a yes/no type."""
        field_type = self.get_field_type(field_name)
        return field_type == "yesno" if field_type else False

    def get_model_explore(self) -> tuple[str, str]:
        """Get model and explore names."""
        schema = self.load_schema()
        return schema["model"], schema["explore"]

    def get_always_filters(self) -> List[Dict[str, str]]:
        """Get default filters that should always be applied."""
        schema = self.load_schema()
        defaults = schema.get("defaults", {})
        return defaults.get("always_filter", [])

    def validate_query_fields(self, fields: List[str]) -> Dict[str, Any]:
        """
        Validate that query fields exist in the schema.

        Args:
            fields: List of field names to validate

        Returns:
            Dictionary with validation results
        """
        available_fields = set(self.get_available_fields())

        valid_fields = []
        invalid_fields = []

        for field in fields:
            if field in available_fields:
                valid_fields.append(field)
            else:
                invalid_fields.append(field)

        return {
            "valid": len(invalid_fields) == 0,
            "valid_fields": valid_fields,
            "invalid_fields": invalid_fields,
            "total_fields": len(fields)
        }

    def validate_query_filters(self, filters: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate that query filters are valid.

        Args:
            filters: Dictionary of field_name -> filter_value

        Returns:
            Dictionary with validation results
        """
        available_fields = set(self.get_available_fields())

        valid_filters = {}
        invalid_filters = {}
        warnings = []

        for field_name, filter_value in filters.items():
            if field_name in available_fields:
                # Check if yesno field has valid values
                if self.is_yesno_field(field_name):
                    if filter_value not in ["Yes", "No"]:
                        warnings.append(f"Field '{field_name}' expects 'Yes' or 'No', got '{filter_value}'")

                valid_filters[field_name] = filter_value
            else:
                invalid_filters[field_name] = filter_value

        return {
            "valid": len(invalid_filters) == 0,
            "valid_filters": valid_filters,
            "invalid_filters": invalid_filters,
            "warnings": warnings,
            "total_filters": len(filters)
        }


# Global instance for easy access
explore_schema_loader = ExploreSchemaLoader()