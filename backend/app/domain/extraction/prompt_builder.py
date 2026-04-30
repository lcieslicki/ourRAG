import json


class ExtractionPromptBuilder:
    """Builder for structured extraction prompts."""

    @staticmethod
    def build_extraction_prompt(
        schema: dict,
        context_chunks: list[str],
        schema_name: str,
    ) -> str:
        """
        Build a prompt for structured extraction.

        Args:
            schema: The JSON schema for extraction.
            context_chunks: List of document chunks to extract from.
            schema_name: Name of the extraction schema.

        Returns:
            A formatted prompt string.
        """
        schema_json = json.dumps(schema, indent=2)
        context = "\n\n".join(f"[Chunk {i + 1}]\n{chunk}" for i, chunk in enumerate(context_chunks))

        prompt = f"""You are a data extraction expert. Your task is to extract structured information from the provided documents.

Schema: {schema_name}
Expected JSON Schema:
{schema_json}

Document Context:
{context}

Instructions:
1. Carefully read the provided document context.
2. Extract information that matches the required schema.
3. Use only information present in the documents.
4. Ensure all required fields are populated.
5. Return ONLY a valid JSON object that conforms to the schema above.
6. Do not include any explanation or markdown formatting.

Return the extracted data as valid JSON:"""

        return prompt
