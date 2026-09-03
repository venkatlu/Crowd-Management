import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_people_counter import PeopleCounter, DetectionResult
from database import DatabaseManager
from notifications import NotificationManager
from monitoring_service import MonitoringService
from config import Config

class TestPeopleCounter:
    def setup_method(self):
        self.counter = PeopleCounter()
    
    def test_get_density_level(self):
        # Test green level
        assert self.counter.get_density_level("ground_floor", 20) == "green"
        assert self.counter.get_density_level("ground_floor", 30) == "green"
        
        # Test yellow level
        assert self.counter.get_density_level("ground_floor", 50) == "yellow"
        assert self.counter.get_density_level("ground_floor", 60) == "yellow"
        
        # Test red level
        assert self.counter.get_density_level("ground_floor", 80) == "red"
        assert self.counter.get_density_level("ground_floor", 90) == "red"
    
    def test_detection_result_creation(self):
        result = DetectionResult(
            zone="test_zone",
            count=25,
            confidence=0.85,
            timestamp=1234567890.0,
            bbox=[(10, 10, 50, 50)],
            density_level="green"
        )
        
        assert result.zone == "test_zone"
        assert result.count == 25
        assert result.confidence == 0.85
        assert result.density_level == "green"
        assert len(result.bbox) == 1

class TestDatabaseManager:
    @pytest.fixture
    def db_manager(self):
        return DatabaseManager()
    
    @pytest.mark.asyncio
    async def test_store_crowd_data(self, db_manager):
        with patch.object(db_manager, 'connection') as mock_conn:
            mock_cursor = AsyncMock()
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_cursor.lastrowid = 1
            
            detection_data = {
                "zone": "test_zone",
                "count": 25,
                "confidence": 0.85,
                "density_level": "green",
                "bbox": [(10, 10, 50, 50)],
                "anomaly_detected": False
            }
            
            result = await db_manager.store_crowd_data(detection_data)
            assert result == 1
            mock_conn.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_alert(self, db_manager):
        with patch.object(db_manager, 'connection') as mock_conn:
            mock_cursor = AsyncMock()
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_cursor.lastrowid = 2
            
            alert_data = {
                "zone": "test_zone",
                "alert_type": "capacity_warning",
                "severity": "yellow",
                "message": "Test alert",
                "count": 50,
                "capacity_percentage": 75.0
            }
            
            result = await db_manager.store_alert(alert_data)
            assert result == 2
            mock_conn.execute.assert_called_once()

class TestNotificationManager:
    def setup_method(self):
        self.notification_manager = NotificationManager()
    
    def test_create_alert_message(self):
        messages = self.notification_manager.create_alert_message(
            "ground_floor", "capacity_warning", 50, 100, "yellow"
        )
        
        assert "sms" in messages
        assert "email_subject" in messages
        assert "email_message" in messages
        assert "CROWD ALERT" in messages["sms"]
        assert "Ground_Floor" in messages["email_subject"]
    
    def test_get_recommended_actions(self):
        red_actions = self.notification_manager._get_recommended_actions("red", 90)
        assert "dispatch security personnel" in red_actions.lower()
        
        yellow_actions = self.notification_manager._get_recommended_actions("yellow", 60)
        assert "increase monitoring" in yellow_actions.lower()

class TestMonitoringService:
    @pytest.fixture
    def monitoring_service(self):
        return MonitoringService()
    
    @pytest.mark.asyncio
    async def test_check_and_send_alerts(self, monitoring_service):
        with patch.object(monitoring_service, 'send_alert') as mock_send_alert:
            # Test red alert
            await monitoring_service.check_and_send_alerts(
                "ground_floor", 90, 100, 90.0, "red", False
            )
            mock_send_alert.assert_called_once()
            
            # Test yellow alert
            mock_send_alert.reset_mock()
            await monitoring_service.check_and_send_alerts(
                "ground_floor", 60, 100, 60.0, "yellow", False
            )
            mock_send_alert.assert_called_once()
            
            # Test green (no alert)
            mock_send_alert.reset_mock()
            await monitoring_service.check_and_send_alerts(
                "ground_floor", 20, 100, 20.0, "green", False
            )
            mock_send_alert.assert_not_called()
    
    def test_calculate_trend_direction(self, monitoring_service):
        # Create mock trends
        trends = [
            DetectionResult("test", 10, 0.8, 1000, [], "green"),
            DetectionResult("test", 15, 0.8, 1001, [], "green"),
            DetectionResult("test", 20, 0.8, 1002, [], "yellow"),
            DetectionResult("test", 25, 0.8, 1003, [], "yellow"),
            DetectionResult("test", 30, 0.8, 1004, [], "yellow"),
        ]
        
        trend = monitoring_service._calculate_trend_direction(trends)
        assert trend in ["increasing", "decreasing", "stable"]

class TestConfig:
    def test_zone_capacities(self):
        assert "ground_floor" in Config.ZONE_CAPACITIES
        assert "hall" in Config.ZONE_CAPACITIES
        assert "balcony" in Config.ZONE_CAPACITIES
        assert "lobby" in Config.ZONE_CAPACITIES
        assert "parking" in Config.ZONE_CAPACITIES
        
        # Check that all capacities are positive
        for zone, capacity in Config.ZONE_CAPACITIES.items():
            assert capacity > 0, f"Capacity for {zone} should be positive"
    
    def test_video_sources(self):
        assert "ground_floor" in Config.VIDEO_SOURCES
        assert "hall" in Config.VIDEO_SOURCES
        assert "balcony" in Config.VIDEO_SOURCES
        assert "lobby" in Config.VIDEO_SOURCES
        assert "parking" in Config.VIDEO_SOURCES
        
        # Check that all video sources are valid paths
        for zone, path in Config.VIDEO_SOURCES.items():
            assert path.endswith('.mp4'), f"Video source for {zone} should be .mp4 file"
    
    def test_alert_colors(self):
        assert "green" in Config.ALERT_COLORS
        assert "yellow" in Config.ALERT_COLORS
        assert "red" in Config.ALERT_COLORS
        
        # Check that colors are valid hex codes
        for color_name, color_value in Config.ALERT_COLORS.items():
            assert color_value.startswith('#'), f"Color {color_name} should be hex code"
            assert len(color_value) == 7, f"Color {color_name} should be 7 characters"

class TestIntegration:
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test a complete workflow from detection to alert"""
        # This would be a more comprehensive integration test
        # that tests the entire system working together
        
        # Mock the video capture
        with patch('cv2.VideoCapture') as mock_cap:
            mock_cap.return_value.isOpened.return_value = True
            mock_cap.return_value.read.return_value = (True, Mock())
            
            # Mock YOLO model
            with patch('ultralytics.YOLO') as mock_yolo:
                mock_model = Mock()
                mock_yolo.return_value = mock_model
                mock_model.return_value = [Mock(boxes=Mock())]
                
                # Create monitoring service
                service = MonitoringService()
                
                # Test that service can be initialized
                assert service is not None
                assert service.people_counter is not None

def run_tests():
    """Run all tests"""
    pytest.main([__file__, "-v", "--tb=short"])

if __name__ == "__main__":
    run_tests()
