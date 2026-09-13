"""Shared data models for Smith IT Company Network Diagnostic Toolkit."""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class DiagnosticResult:
    """Standardized result of a single diagnostic check."""
    name: str
    status: str  # "PASS", "WARN", "FAIL", "UNKNOWN"
    value: str
    severity: str = "info"  # "info", "warning", "error"
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AdapterInfo:
    """Network adapter and local host configuration."""
    hostname: str = "Unknown"
    os_name: str = "Unknown"
    adapter_name: str = "Unknown"
    mac_address: str = "Unknown"
    ipv4_address: str = "Unknown"
    subnet_mask: str = "Unknown"
    default_gateway: str = "Unknown"
    dns_servers: List[str] = field(default_factory=list)
    is_apipa: bool = False
    is_connected: bool = False
    wifi_info: Dict[str, str] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DiagnosisItem:
    """An issue identified by the root-cause diagnosis engine."""
    rule_id: str
    title: str
    description: str
    recommendations: List[str] = field(default_factory=list)
    severity: str = "warning"  # "info", "warning", "critical"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HealthScoreResult:
    """Network health score evaluation breakdown."""
    total_score: int = 0  # 0 to 100
    grade: str = "Poor"  # "Excellent", "Good", "Needs Attention", "Poor"
    breakdown: Dict[str, int] = field(default_factory=dict)
    max_breakdown: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScanReport:
    """Complete diagnostic report for CLI, JSON, and HTML rendering."""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    version: str = "1.0.0"
    adapter_info: AdapterInfo = field(default_factory=AdapterInfo)
    results: List[DiagnosticResult] = field(default_factory=list)
    health_score: HealthScoreResult = field(default_factory=HealthScoreResult)
    diagnosed_issues: List[DiagnosisItem] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    public_ip_info: Dict[str, Any] = field(default_factory=dict)
    is_privacy_masked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "version": self.version,
            "is_privacy_masked": self.is_privacy_masked,
            "adapter_info": self.adapter_info.to_dict(),
            "results": [r.to_dict() for r in self.results],
            "health_score": self.health_score.to_dict(),
            "diagnosed_issues": [i.to_dict() for i in self.diagnosed_issues],
            "recommendations": self.recommendations,
            "public_ip_info": self.public_ip_info,
        }
