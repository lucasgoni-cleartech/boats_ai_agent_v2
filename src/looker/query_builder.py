"""
Query builder for converting natural language to Looker queries.

Maps user intent and parameters to Looker Explore API queries.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LookerQueryBuilder:
    """
    Builds Looker API queries from natural language intent and parameters.
    
    Works with explore schema to generate appropriate queries.
    """

    def __init__(self, explore_schema: Dict[str, Any]):
        """Initialize with Looker Explore schema."""
        self.schema = explore_schema
        # In the schema, dimensions are stored as "filters"
        self.dimensions = {dim.get("name", dim.get("field_name", "")): dim for dim in explore_schema.get("filters", [])}
        self.measures = {measure.get("name", measure.get("field_name", "")): measure for measure in explore_schema.get("measures", [])}
        logger.info(f"QueryBuilder initialized with {len(self.dimensions)} dimensions and {len(self.measures)} measures")

    def build_query_from_intent(self, user_query: str, intent_params: Dict[str, Any]) -> Dict[str, Any]:
        """Build Looker query from user intent and extracted parameters."""
        try:
            query = {
                "model": self.schema.get("model", "default_model"),
                "view": self.schema.get("explore", "default_explore"),
                "explore": self.schema.get("explore", "default_explore"),
                "dimensions": [],
                "measures": [],
                "sorts": [],
                "filters": {},
                "limit": 10
            }
            
            # Extract dimensions and measures from parameters
            self._add_dimensions(query, intent_params, user_query)
            self._add_measures(query, intent_params, user_query)
            self._add_filters(query, intent_params, user_query)
            self._add_sorts(query, intent_params)
            self._set_limit(query, intent_params, user_query)

            # Fallback: Si query está vacía, usar query por defecto
            if not query.get("dimensions") and not query.get("measures"):
                logger.warning("No dimensions/measures detected, using default query")
                return self._get_default_query_with_view()

            logger.info(f"Built query: {query}")
            return query
            
        except Exception as e:
            logger.error(f"Failed to build query: {e}")
            return self._get_default_query()

    def _add_dimensions(self, query: Dict[str, Any], params: Dict[str, Any], user_query: str) -> None:
        """Add dimensions to the query based on parameters and user query."""
        # Check for explicit dimension parameter
        if "dimension" in params:
            dim_name = params["dimension"]
            if dim_name in self.dimensions:
                query["dimensions"].append(dim_name)
                return
        
        # Infer dimensions from user query
        dimension_keywords = {
            "country": ["country", "countries", "region", "location"],
            "date": ["time", "date", "month", "year", "trend", "over time"],
            "product_category": ["product", "category", "type", "item"],
            "customer_segment": ["segment", "customer", "client", "type"]
        }
        
        for dim_name, keywords in dimension_keywords.items():
            if dim_name in self.dimensions and any(kw in user_query.lower() for kw in keywords):
                query["dimensions"].append(dim_name)
                break
        
        # Default dimension if none found
        if not query["dimensions"] and "country" in self.dimensions:
            query["dimensions"].append("country")

    def _add_measures(self, query: Dict[str, Any], params: Dict[str, Any], user_query: str) -> None:
        """Add measures to the query based on parameters and user query."""
        # Check for explicit measure parameter
        if "measure" in params:
            measure_name = params["measure"]
            if measure_name in self.measures:
                query["measures"].append(measure_name)
                return
        
        # Infer measures from user query
        measure_keywords = {
            "revenue": ["revenue", "sales", "income", "money", "dollars"],
            "order_count": ["orders", "transactions", "purchases", "count"],
            "customer_count": ["customers", "users", "people", "clients"]
        }
        
        for measure_name, keywords in measure_keywords.items():
            if measure_name in self.measures and any(kw in user_query.lower() for kw in keywords):
                query["measures"].append(measure_name)
                break
        
        # Default measure if none found
        if not query["measures"] and "revenue" in self.measures:
            query["measures"].append("revenue")

    def _add_filters(self, query: Dict[str, Any], params: Dict[str, Any], user_query: str) -> None:
        """Add filters to the query based on parameters."""
        if "filters" in params:
            query["filters"] = params["filters"]
        
        # Extract date filters from query
        date_patterns = [
            r"last (\d+) days?",
            r"past (\d+) months?",
            r"(\d{4})",  # Year
            r"(january|february|march|april|may|june|july|august|september|october|november|december)",
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, user_query.lower())
            if match:
                # Add appropriate date filter
                if "days" in pattern:
                    query["filters"]["date"] = f"last {match.group(1)} days"
                elif "months" in pattern:
                    query["filters"]["date"] = f"last {match.group(1)} months"
                elif match.group(1).isdigit() and len(match.group(1)) == 4:
                    query["filters"]["date"] = f"year {match.group(1)}"
                break

    def _add_sorts(self, query: Dict[str, Any], params: Dict[str, Any]) -> None:
        """Add sorting to the query."""
        if "sort" in params:
            query["sorts"] = [params["sort"]]
        elif query["measures"]:
            # Default to sorting by first measure descending
            query["sorts"] = [f"{query['measures'][0]} desc"]

    def _set_limit(self, query: Dict[str, Any], params: Dict[str, Any], user_query: str) -> None:
        """Set result limit based on parameters or user query."""
        if "limit" in params:
            query["limit"] = params["limit"]
        else:
            # Extract numbers from user query for limit
            limit_patterns = [
                r"top (\d+)",
                r"first (\d+)",
                r"show (\d+)",
                r"(\d+) results?"
            ]
            
            for pattern in limit_patterns:
                match = re.search(pattern, user_query.lower())
                if match:
                    query["limit"] = int(match.group(1))
                    break

    def build_drill_down_query(self, base_query: Dict[str, Any], drill_down_params: Dict[str, Any]) -> Dict[str, Any]:
        """Build a drill-down query from an existing query."""
        drill_query = base_query.copy()
        
        # Add additional dimensions for drill-down
        if "dimension" in drill_down_params:
            new_dim = drill_down_params["dimension"]
            if new_dim in self.dimensions and new_dim not in drill_query["dimensions"]:
                drill_query["dimensions"].append(new_dim)
        
        # Add filters for drill-down
        if "filters" in drill_down_params:
            drill_query["filters"].update(drill_down_params["filters"])
        
        # Increase limit for more detailed view
        if drill_query["limit"] < 20:
            drill_query["limit"] = 20
        
        return drill_query

    def _get_default_query_with_view(self) -> Dict[str, Any]:
        """Get a clarification request when query is too vague."""
        # En lugar de query genérica, devolver mensaje de aclaración
        return {
            "error": "clarification_needed",
            "message": "I need more specific information. Try asking:\n• 'sessions this month'\n• 'sessions by country'\n• 'sessions today'\n• 'top countries by sessions'\n• 'sessions over time'"
        }

    def _get_default_query(self) -> Dict[str, Any]:
        """Get a default query when building fails."""
        return self._get_default_query_with_view()

    def get_available_dimensions(self) -> List[Dict[str, str]]:
        """Get list of available dimensions with labels."""
        return [{"name": name, "label": dim.get("label", name)} 
                for name, dim in self.dimensions.items()]

    def get_available_measures(self) -> List[Dict[str, str]]:
        """Get list of available measures with labels."""
        return [{"name": name, "label": measure.get("label", name)} 
                for name, measure in self.measures.items()]

    def validate_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix a Looker query."""
        validated_query = query.copy()
        
        # Ensure required fields exist
        if "dimensions" not in validated_query:
            validated_query["dimensions"] = []
        if "measures" not in validated_query:
            validated_query["measures"] = []
        
        # Validate dimensions exist in schema
        validated_query["dimensions"] = [
            dim for dim in validated_query["dimensions"] 
            if dim in self.dimensions
        ]
        
        # Validate measures exist in schema
        validated_query["measures"] = [
            measure for measure in validated_query["measures"] 
            if measure in self.measures
        ]
        
        # Ensure at least one dimension or measure
        if not validated_query["dimensions"] and not validated_query["measures"]:
            if self.dimensions:
                validated_query["dimensions"] = [list(self.dimensions.keys())[0]]
            if self.measures:
                validated_query["measures"] = [list(self.measures.keys())[0]]
        
        return validated_query