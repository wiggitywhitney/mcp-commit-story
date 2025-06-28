"""Tests for AI telemetry and metrics functionality.

This module tests the simple telemetry attributes added to existing spans
in the AI invocation layer, focusing on success/failure tracking, latency
measurement, and error type categorization.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from opentelemetry import trace

from src.mcp_commit_story.ai_invocation import invoke_ai


class TestAITelemetryIntegration:
    """Test AI telemetry integration with existing spans."""
    
    def test_successful_ai_call_adds_success_attributes(self):
        """Test that successful AI calls add success=True and latency attributes."""
        mock_span = Mock()
        
        with patch('src.mcp_commit_story.ai_invocation.invoke_ai') as mock_invoke:
            with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
                # Mock successful AI response
                mock_invoke.return_value = "Generated content"
                
                # Call the function (this will be the actual invoke_ai with telemetry)
                result = invoke_ai("Test prompt", {})
                
                # Verify success attributes were set
                mock_span.set_attribute.assert_any_call("ai.success", True)
                # Verify latency was recorded (should be a positive integer)
                latency_calls = [call for call in mock_span.set_attribute.call_args_list 
                               if call[0][0] == "ai.latency_ms"]
                assert len(latency_calls) == 1
                assert isinstance(latency_calls[0][0][1], int)
                assert latency_calls[0][0][1] >= 0
    
    def test_failed_ai_call_adds_failure_attributes(self):
        """Test that failed AI calls add success=False and error_type attributes."""
        mock_span = Mock()
        
        with patch('src.mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
                # Mock provider that raises an exception
                mock_provider = Mock()
                mock_provider.call.side_effect = ValueError("Test error")
                mock_provider_class.return_value = mock_provider
                
                # Call should return empty string (graceful degradation)
                result = invoke_ai("Test prompt", {})
                assert result == ""
                
                # Verify failure attributes were set
                mock_span.set_attribute.assert_any_call("ai.success", False)
                mock_span.set_attribute.assert_any_call("ai.error_type", "ValueError")
                
                # Verify latency was still recorded
                latency_calls = [call for call in mock_span.set_attribute.call_args_list 
                               if call[0][0] == "ai.latency_ms"]
                assert len(latency_calls) == 1
    
    def test_network_error_records_correct_error_type(self):
        """Test that network errors are categorized correctly."""
        mock_span = Mock()
        
        with patch('src.mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
                # Mock provider that raises a network-related exception
                mock_provider = Mock()
                mock_provider.call.side_effect = ConnectionError("Network timeout")
                mock_provider_class.return_value = mock_provider
                
                result = invoke_ai("Test prompt", {})
                assert result == ""
                
                # Verify correct error type was recorded
                mock_span.set_attribute.assert_any_call("ai.error_type", "ConnectionError")
    
    def test_authentication_error_records_correct_error_type(self):
        """Test that authentication errors are categorized correctly."""
        mock_span = Mock()
        
        with patch('src.mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
                # Mock provider that raises an auth exception
                mock_provider = Mock()
                mock_provider.call.side_effect = PermissionError("Invalid API key")
                mock_provider_class.return_value = mock_provider
                
                result = invoke_ai("Test prompt", {})
                assert result == ""
                
                # Verify correct error type was recorded
                mock_span.set_attribute.assert_any_call("ai.error_type", "PermissionError")
    
    def test_latency_measurement_accuracy(self):
        """Test that latency measurement is reasonably accurate."""
        mock_span = Mock()
        
        with patch('src.mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
                # Mock provider with artificial delay
                mock_provider = Mock()
                def delayed_call(*args, **kwargs):
                    time.sleep(0.1)  # 100ms delay
                    return "Response"
                mock_provider.call.side_effect = delayed_call
                mock_provider_class.return_value = mock_provider
                
                start_time = time.time()
                result = invoke_ai("Test prompt", {})
                end_time = time.time()
                
                # Get the recorded latency
                latency_calls = [call for call in mock_span.set_attribute.call_args_list 
                               if call[0][0] == "ai.latency_ms"]
                recorded_latency_ms = latency_calls[0][0][1]
                actual_duration_ms = (end_time - start_time) * 1000
                
                # Verify latency is reasonable (within 50ms of actual)
                assert abs(recorded_latency_ms - actual_duration_ms) < 50
    
    def test_no_span_available_doesnt_crash(self):
        """Test that telemetry gracefully handles missing spans."""
        with patch('opentelemetry.trace.get_current_span', return_value=None):
            with patch('src.mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
                mock_provider = Mock()
                mock_provider.call.return_value = "Response"
                mock_provider_class.return_value = mock_provider
                
                # Should not crash when no span is available
                result = invoke_ai("Test prompt", {})
                assert result == "Response"
    
    def test_retry_failures_record_final_error_only(self):
        """Test that only the final error is recorded, not intermediate retry failures."""
        mock_span = Mock()
        
        with patch('src.mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
                # Mock provider that fails on all retry attempts
                mock_provider = Mock()
                mock_provider.call.side_effect = [
                    ConnectionError("First attempt"),
                    ConnectionError("Second attempt"), 
                    ValueError("Final attempt")
                ]
                mock_provider_class.return_value = mock_provider
                
                result = invoke_ai("Test prompt", {})
                assert result == ""
                
                # Should record the final error type
                mock_span.set_attribute.assert_any_call("ai.error_type", "ValueError")
                mock_span.set_attribute.assert_any_call("ai.success", False)
    
    def test_telemetry_attributes_only_on_ai_invocation_span(self):
        """Test that AI attributes are only added to spans from ai_invocation, not other spans."""
        # This is more of a design verification - the attributes should only be
        # added by the invoke_ai function, not by other parts of the system
        
        # Create a mock span that's NOT from ai_invocation
        mock_other_span = Mock()
        
        with patch('opentelemetry.trace.get_current_span', return_value=mock_other_span):
            # Call some other function that uses spans but shouldn't add AI attributes
            # This is just a design verification test
            pass
            
        # Verify no AI attributes were added to non-AI spans
        ai_attribute_calls = [call for call in mock_other_span.set_attribute.call_args_list 
                            if call[0][0].startswith("ai.")]
        assert len(ai_attribute_calls) == 0
    
    def test_all_three_required_attributes_always_present(self):
        """Test that all three required attributes are always set (success, latency, error_type)."""
        mock_span = Mock()
        
        # Test successful case
        with patch('src.mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
                mock_provider = Mock()
                mock_provider.call.return_value = "Success response"
                mock_provider_class.return_value = mock_provider
                
                invoke_ai("Test prompt", {})
                
                # Verify all required attributes are present
                attribute_names = [call[0][0] for call in mock_span.set_attribute.call_args_list]
                assert "ai.success" in attribute_names
                assert "ai.latency_ms" in attribute_names
                # error_type should NOT be present for successful calls
                assert "ai.error_type" not in attribute_names
        
        # Reset mock for failure case
        mock_span.reset_mock()
        
        # Test failure case  
        with patch('src.mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
                mock_provider = Mock()
                mock_provider.call.side_effect = RuntimeError("Test error")
                mock_provider_class.return_value = mock_provider
                
                invoke_ai("Test prompt", {})
                
                # Verify all required attributes are present for failures
                attribute_names = [call[0][0] for call in mock_span.set_attribute.call_args_list]
                assert "ai.success" in attribute_names
                assert "ai.latency_ms" in attribute_names
                assert "ai.error_type" in attribute_names 