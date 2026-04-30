import jsonschema


class ExtractionSchemaRegistry:
    """Registry for managing extraction schemas."""

    _schemas: dict[str, dict] = {
        "procedure_metadata_v1": {
            "type": "object",
            "required": ["title", "owner", "department"],
            "properties": {
                "title": {"type": "string"},
                "owner": {"type": "string"},
                "department": {"type": "string"},
                "scope": {"type": "string"},
                "approval_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "effective_date": {"type": "string"},
            },
        },
        "approval_path_v1": {
            "type": "object",
            "required": ["document_title", "approvers"],
            "properties": {
                "document_title": {"type": "string"},
                "approvers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "department": {"type": "string"},
                        },
                        "required": ["role", "department"],
                    },
                },
                "approval_type": {"type": "string"},
            },
        },
        "document_brief_v1": {
            "type": "object",
            "required": ["title", "summary"],
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "document_type": {"type": "string"},
                "target_audience": {"type": "string"},
            },
        },
        "deadline_and_required_documents_v1": {
            "type": "object",
            "required": ["process_name"],
            "properties": {
                "process_name": {"type": "string"},
                "deadline": {"type": "string"},
                "required_documents": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "responsible_department": {"type": "string"},
            },
        },
    }

    @classmethod
    def get(cls, schema_name: str) -> dict:
        """
        Retrieve a schema by name.

        Args:
            schema_name: The name of the schema to retrieve.

        Returns:
            The JSON schema dictionary.

        Raises:
            KeyError: If the schema does not exist.
        """
        if schema_name not in cls._schemas:
            raise KeyError(f"Schema '{schema_name}' not found in registry")
        return cls._schemas[schema_name]

    @classmethod
    def list_schemas(cls) -> list[str]:
        """
        List all available schema names.

        Returns:
            A list of schema names.
        """
        return list(cls._schemas.keys())

    @classmethod
    def validate(cls, schema_name: str, data: dict) -> tuple[bool, list[str]]:
        """
        Validate data against a schema.

        Args:
            schema_name: The name of the schema to validate against.
            data: The data to validate.

        Returns:
            A tuple of (is_valid, error_messages).
            is_valid is True if validation passed.
            error_messages is a list of validation error messages (empty if valid).
        """
        try:
            schema = cls.get(schema_name)
        except KeyError:
            return False, [f"Schema '{schema_name}' not found in registry"]

        try:
            jsonschema.validate(instance=data, schema=schema)
            return True, []
        except jsonschema.ValidationError as e:
            error_msg = f"{e.message} at path: {list(e.absolute_path)}"
            return False, [error_msg]
        except jsonschema.SchemaError as e:
            error_msg = f"Schema error: {e.message}"
            return False, [error_msg]
