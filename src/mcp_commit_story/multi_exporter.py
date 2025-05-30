"""
Multi-Exporter Configuration System for OpenTelemetry

This module implements the enhanced multi-exporter configuration system with:
- Environment variable precedence hierarchy
- Partial success error handling
- Comprehensive validation rules  
- Support for console, OTLP, and Prometheus exporters
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHTTPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as OTLPHTTPMetricExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ExporterConfigurationError(Exception):
    """Raised when exporter configuration fails."""
    pass


@dataclass
class PartialSuccessResult:
    """Result object for partial success scenarios."""
    status: str  # "success", "partial_success", "failure"
    successful_exporters: List[str] = field(default_factory=list)
    failed_exporters: Dict[str, Dict[str, str]] = field(default_factory=dict)


class ExporterConfigManager:
    """Manages multi-exporter configuration with enhanced features."""
    
    # Built-in defaults (lowest priority)
    DEFAULT_CONFIG = {
        "telemetry": {
            "enabled": True,
            "service_name": "mcp-commit-story",
            "exporters": {
                "console": {
                    "enabled": True,
                    "traces": True,
                    "metrics": True
                },
                "otlp": {
                    "enabled": False,
                    "endpoint": "http://localhost:4317",
                    "protocol": "grpc",
                    "headers": {},
                    "timeout": 30,
                    "traces": True,
                    "metrics": True
                },
                "prometheus": {
                    "enabled": False,
                    "port": 8888,
                    "endpoint": "/metrics",
                    "metrics": True,
                    "traces": False
                }
            }
        }
    }
    
    def resolve_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve configuration with environment variable precedence hierarchy."""
        # Start with defaults, then merge with provided config
        resolved = self._deep_merge(self.DEFAULT_CONFIG.copy(), config)
        
        # Apply environment variables in precedence order (lowest to highest priority)
        # 1. Standard OTel env vars (lower priority)
        standard_otel_vars = {
            'OTEL_EXPORTER_OTLP_ENDPOINT': ('telemetry.exporters.otlp.endpoint', str),
            'OTEL_EXPORTER_OTLP_HEADERS': ('telemetry.exporters.otlp.headers', lambda x: dict(h.split('=') for h in x.split(',') if '=' in h)),
            'OTEL_EXPORTER_OTLP_TIMEOUT': ('telemetry.exporters.otlp.timeout', int),
            'OTEL_SERVICE_NAME': ('telemetry.service_name', str),
        }
        
        # 2. MCP-specific env vars (higher priority)
        mcp_specific_vars = {
            'MCP_PROMETHEUS_PORT': ('telemetry.exporters.prometheus.port', int),
            'MCP_CONSOLE_ENABLED': ('telemetry.exporters.console.enabled', lambda x: x.lower() == 'true'),
            'MCP_OTLP_ENDPOINT': ('telemetry.exporters.otlp.endpoint', str),
            'MCP_OTLP_ENABLED': ('telemetry.exporters.otlp.enabled', lambda x: x.lower() == 'true'),
            'MCP_PROMETHEUS_ENABLED': ('telemetry.exporters.prometheus.enabled', lambda x: x.lower() == 'true'),
        }
        
        # Apply in order: standard OTel first, then MCP-specific (which can override)
        for env_vars in [standard_otel_vars, mcp_specific_vars]:
            for env_var, (config_path, converter) in env_vars.items():
                env_value = os.environ.get(env_var)
                if env_value is not None:
                    try:
                        converted_value = converter(env_value)
                        self._set_nested_value(resolved, config_path, converted_value)
                        logger.debug(f"Applied env var {env_var}={env_value} to {config_path}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to convert env var {env_var}={env_value}: {e}")
        
        return resolved
    
    def validate_configuration(self, config: Dict[str, Any]) -> None:
        """Validate configuration with comprehensive rules."""
        telemetry_config = config.get('telemetry', {})
        exporters = telemetry_config.get('exporters', {})
        
        # Validate Prometheus configuration
        if 'prometheus' in exporters:
            prometheus_config = exporters['prometheus']
            
            # Port range validation (1-65535)
            if 'port' in prometheus_config:
                port = prometheus_config['port']
                if not isinstance(port, int) or port < 1 or port > 65535:
                    raise ValidationError("Port must be between 1 and 65535")
            
            # Endpoint must start with '/'
            if 'endpoint' in prometheus_config:
                endpoint = prometheus_config['endpoint']
                if not isinstance(endpoint, str) or not endpoint.startswith('/'):
                    raise ValidationError("Endpoint must start with '/'")
        
        # Validate OTLP configuration
        if 'otlp' in exporters:
            otlp_config = exporters['otlp']
            
            # Protocol must be 'grpc' or 'http'
            if 'protocol' in otlp_config:
                protocol = otlp_config['protocol']
                if protocol not in ['grpc', 'http']:
                    raise ValidationError("Protocol must be 'grpc' or 'http'")
            
            # Timeout must be positive integer
            if 'timeout' in otlp_config:
                timeout = otlp_config['timeout']
                if not isinstance(timeout, int) or timeout <= 0:
                    raise ValidationError("Timeout must be a positive integer")
            
            # Headers must be valid key-value pairs
            if 'headers' in otlp_config:
                headers = otlp_config['headers']
                if not isinstance(headers, dict):
                    raise ValidationError("Headers must be valid key-value pairs")
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any) -> None:
        """Set a nested value in config using dot notation."""
        keys = path.split('.')
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value


def setup_console_exporter(config: Dict[str, Any]) -> List[Union[BatchSpanProcessor, PeriodicExportingMetricReader]]:
    """Set up console exporter for traces and metrics."""
    processors = []
    
    console_config = config['telemetry']['exporters']['console']
    
    if console_config.get('traces', True):
        span_exporter = ConsoleSpanExporter()
        processors.append(BatchSpanProcessor(span_exporter))
        logger.info("Console trace exporter configured")
    
    if console_config.get('metrics', True):
        metric_exporter = ConsoleMetricExporter()
        metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=10000)
        processors.append(metric_reader)
        logger.info("Console metric exporter configured")
    
    return processors


def setup_otlp_exporter(config: Dict[str, Any]) -> List[Union[BatchSpanProcessor, PeriodicExportingMetricReader]]:
    """Set up OTLP exporter for traces and metrics."""
    processors = []
    
    otlp_config = config['telemetry']['exporters']['otlp']
    endpoint = otlp_config['endpoint']
    protocol = otlp_config.get('protocol', 'grpc')
    headers = otlp_config.get('headers', {})
    timeout = otlp_config.get('timeout', 30)
    
    if otlp_config.get('traces', True):
        if protocol == 'grpc':
            span_exporter = OTLPSpanExporter(
                endpoint=endpoint,
                headers=headers,
                timeout=timeout
            )
        else:  # http
            span_exporter = OTLPHTTPSpanExporter(
                endpoint=endpoint,
                headers=headers,
                timeout=timeout
            )
        processors.append(BatchSpanProcessor(span_exporter))
        logger.info(f"OTLP trace exporter configured: {endpoint} ({protocol})")
    
    if otlp_config.get('metrics', True):
        if protocol == 'grpc':
            metric_exporter = OTLPMetricExporter(
                endpoint=endpoint,
                headers=headers,
                timeout=timeout
            )
        else:  # http
            metric_exporter = OTLPHTTPMetricExporter(
                endpoint=endpoint,
                headers=headers,
                timeout=timeout
            )
        metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=10000)
        processors.append(metric_reader)
        logger.info(f"OTLP metric exporter configured: {endpoint} ({protocol})")
    
    return processors


def setup_prometheus_exporter(config: Dict[str, Any]) -> List[PeriodicExportingMetricReader]:
    """Set up Prometheus exporter for metrics."""
    processors = []
    
    prometheus_config = config['telemetry']['exporters']['prometheus']
    
    if prometheus_config.get('metrics', True):
        port = prometheus_config.get('port', 8888)
        endpoint = prometheus_config.get('endpoint', '/metrics')
        
        # Prometheus only supports metrics, not traces
        metric_reader = PrometheusMetricReader(port=port, endpoint=endpoint)
        processors.append(metric_reader)
        logger.info(f"Prometheus metric exporter configured: port {port}, endpoint {endpoint}")
    
    return processors


def configure_exporters(config: Dict[str, Any]) -> PartialSuccessResult:
    """Configure all enabled exporters with partial success handling."""
    manager = ExporterConfigManager()
    
    # Resolve configuration with environment variable precedence
    resolved_config = manager.resolve_configuration(config)
    
    # Validate configuration
    manager.validate_configuration(resolved_config)
    
    result = PartialSuccessResult(status="success")
    exporters_config = resolved_config['telemetry']['exporters']
    
    # Set up each enabled exporter
    for exporter_name, exporter_config in exporters_config.items():
        if not exporter_config.get('enabled', False):
            continue
            
        try:
            if exporter_name == 'console':
                processors = setup_console_exporter(resolved_config)
                result.successful_exporters.append('console')
                
            elif exporter_name == 'otlp':
                processors = setup_otlp_exporter(resolved_config)
                result.successful_exporters.append('otlp')
                
            elif exporter_name == 'prometheus':
                processors = setup_prometheus_exporter(resolved_config)
                result.successful_exporters.append('prometheus')
                
        except Exception as e:
            # Enhanced error handling with detailed information
            error_message = str(e)
            details = error_message
            
            # Add more specific details for common errors
            if "Connection" in error_message or "timeout" in error_message.lower():
                if 'endpoint' in exporter_config:
                    details = f"Failed to connect to {exporter_config['endpoint']} after {exporter_config.get('timeout', 30)} seconds"
            
            result.failed_exporters[exporter_name] = {
                "error": error_message,
                "details": details
            }
            logger.error(f"Failed to configure {exporter_name} exporter: {error_message}")
    
    # Determine final status
    if result.failed_exporters and result.successful_exporters:
        result.status = "partial_success"
    elif result.failed_exporters and not result.successful_exporters:
        result.status = "failure"
    else:
        result.status = "success"
    
    logger.info(f"Exporter configuration completed: {result.status}")
    logger.info(f"Successful exporters: {result.successful_exporters}")
    if result.failed_exporters:
        logger.warning(f"Failed exporters: {list(result.failed_exporters.keys())}")
    
    return result 