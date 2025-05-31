"""
Test configuration and fixtures for MCP Commit Story tests.

This file provides fixtures for both unit and integration testing,
with special support for OpenTelemetry integration testing.
"""

import pytest
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource


@pytest.fixture
def otel_integration_setup():
    """
    Fixture for integration tests that need real OpenTelemetry providers.
    Only use this for integration tests, not unit tests.
    
    This fixture creates fresh providers that work independently of global state.
    It doesn't try to override global providers since OpenTelemetry doesn't allow this.
    
    Usage:
        def test_real_spans(self, otel_integration_setup):
            tracer = otel_integration_setup['tracer']
            with tracer.start_as_current_span("test") as span:
                # Test with real span that should have valid IDs
    """
    # Create fresh providers with proper configuration
    resource = Resource.create({"service.name": "test-service"})
    tracer_provider = TracerProvider(resource=resource)
    
    # Add processor so spans are actually recorded and get proper IDs
    tracer_provider.add_span_processor(
        SimpleSpanProcessor(ConsoleSpanExporter())
    )
    
    meter_provider = MeterProvider(resource=resource)
    
    # Get tracers directly from our providers (not global state)
    tracer = tracer_provider.get_tracer("test-tracer")
    
    yield {
        'tracer_provider': tracer_provider,
        'meter_provider': meter_provider,
        'tracer': tracer
    }
    
    # Clean shutdown
    try:
        tracer_provider.shutdown()
        meter_provider.shutdown()
    except Exception:
        pass  # Ignore shutdown errors in tests 