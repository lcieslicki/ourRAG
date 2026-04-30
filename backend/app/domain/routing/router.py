"""Request router for classifying and dispatching queries to appropriate capabilities."""

import logging
from typing import TYPE_CHECKING

from app.core.config.routing_config import RoutingConfig
from app.domain.routing.models import RequestContext, ResponseMode, RouteDecision

if TYPE_CHECKING:
    from app.domain.classification.service import ClassificationService

logger = logging.getLogger(__name__)


class RequestRouter:
    """Routes incoming requests to appropriate capabilities based on query intent and configuration."""

    def __init__(
        self,
        classification_service: "ClassificationService | None" = None,
        settings: RoutingConfig | None = None,
    ) -> None:
        """Initialize the request router.

        Args:
            classification_service: Optional classification service for intent detection.
            settings: Routing configuration with feature flags and thresholds.
        """
        self.classification_service = classification_service
        self.settings = settings or RoutingConfig()

    def route(self, context: RequestContext) -> RouteDecision:
        """Route a request to the appropriate capability.

        If routing is disabled, returns QA mode as safe default.
        If classification is available and intent is detected with sufficient confidence,
        maps intent to response mode.
        Falls back to QA if confidence is too low.

        Args:
            context: The request context containing query and optional metadata.

        Returns:
            RouteDecision with selected mode, confidence, and explanation.
        """
        # Step 1: Check if routing is enabled
        if not self.settings.routing_enabled:
            return RouteDecision(
                selected_mode=ResponseMode.qa,
                confidence=1.0,
                router_strategy="disabled_default",
                router_reason="Routing is disabled; using safe default mode (qa).",
                is_fallback=False,
            )

        # Step 2: Check UI mode hint (soft signal if allowed)
        ui_hint_mode = None
        if context.ui_mode_hint and self.settings.routing_allow_ui_mode_hint:
            ui_hint_mode = self._parse_ui_mode_hint(context.ui_mode_hint)

        # Step 3: Try to get classification result
        if self.classification_service is not None:
            try:
                classification = self.classification_service.classify_query(
                    query=context.query,
                    workspace_context={"conversation_id": context.conversation_id},
                )

                if classification is not None:
                    # Map classification intent to response mode
                    selected_mode = self._intent_to_mode(classification.intent)
                    confidence = classification.confidence

                    # Step 4: Apply confidence threshold
                    if confidence < self.settings.routing_min_confidence:
                        return RouteDecision(
                            selected_mode=ResponseMode.qa,
                            confidence=confidence,
                            router_strategy="classification_low_confidence_fallback",
                            router_reason=f"Classification intent '{classification.intent}' has confidence {confidence:.2f} below threshold {self.settings.routing_min_confidence}; falling back to qa.",
                            is_fallback=True,
                        )

                    # Use UI hint as a preference override if available and classification agrees
                    if ui_hint_mode is not None and ui_hint_mode != selected_mode:
                        # Log that UI hint conflicts with classification
                        logger.debug(
                            f"UI hint suggests {ui_hint_mode} but classification prefers {selected_mode}; "
                            f"using classification with confidence {confidence:.2f}"
                        )

                    return RouteDecision(
                        selected_mode=selected_mode,
                        confidence=confidence,
                        router_strategy="classification_based",
                        router_reason=f"Classified as '{classification.intent}' (confidence {confidence:.2f}) → {selected_mode.value}.",
                        is_fallback=False,
                    )
            except Exception as e:
                logger.exception(f"Classification failed, falling back to default: {e}")

        # Step 5: Fall back to UI hint or safe default
        if ui_hint_mode is not None:
            return RouteDecision(
                selected_mode=ui_hint_mode,
                confidence=0.5,
                router_strategy="ui_hint_fallback",
                router_reason=f"Classification unavailable; using UI hint mode ({ui_hint_mode.value}).",
                is_fallback=True,
            )

        # Step 6: Safe default
        return RouteDecision(
            selected_mode=ResponseMode.qa,
            confidence=0.0,
            router_strategy="safe_default",
            router_reason="No classification available; using safe default mode (qa).",
            is_fallback=True,
        )

    @staticmethod
    def _intent_to_mode(intent: str) -> ResponseMode:
        """Map classification intent to response mode.

        Args:
            intent: The query intent from classification.

        Returns:
            The corresponding response mode.
        """
        intent_lower = intent.lower()

        if "summary" in intent_lower or intent == "summary":
            return ResponseMode.summarization
        elif "extraction" in intent_lower or intent == "extraction":
            return ResponseMode.structured_extraction
        elif "admin" in intent_lower or intent == "admin_lookup":
            return ResponseMode.admin_lookup
        elif "out_of_scope" in intent_lower or intent == "out_of_scope":
            return ResponseMode.refuse_out_of_scope
        else:
            # Default to QA for unknown intents
            return ResponseMode.qa

    @staticmethod
    def _parse_ui_mode_hint(hint: str) -> ResponseMode | None:
        """Parse UI mode hint string to ResponseMode.

        Args:
            hint: The UI mode hint string.

        Returns:
            The parsed ResponseMode, or None if invalid.
        """
        hint_lower = hint.lower().strip()
        try:
            return ResponseMode(hint_lower)
        except ValueError:
            logger.warning(f"Invalid UI mode hint: {hint}; ignoring")
            return None
