import requests
import unittest
import uuid
import time
import io
import os
from datetime import datetime

# Get the backend URL from the frontend .env file
BACKEND_URL = "https://fc8e6737-f906-4400-bfd6-e1c7562ef7ca.preview.emergentagent.com"
API_URL = f"{BACKEND_URL}/api"

class VNCManagementAPITest(unittest.TestCase):
    def setUp(self):
        # Create a unique test connection for testing
        self.test_connection_name = f"Test Connection {uuid.uuid4().hex[:8]}"
        self.test_connection_data = {
            "name": self.test_connection_name,
            "location": "Test Lab",
            "country": "Russia",
            "city": "Moscow"
        }
        
        # Create a test connection
        response = requests.post(f"{API_URL}/connections", json=self.test_connection_data)
        self.assertEqual(response.status_code, 200, "Failed to create test connection")
        self.test_connection = response.json()
        self.connection_id = self.test_connection["id"]
        print(f"Created test connection with ID: {self.connection_id}")

    def tearDown(self):
        # Clean up - delete the test connection
        try:
            requests.delete(f"{API_URL}/connections/{self.connection_id}")
            print(f"Deleted test connection with ID: {self.connection_id}")
        except Exception as e:
            print(f"Error deleting test connection: {e}")

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        response = requests.get(f"{API_URL}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "VNC Management System API")
        self.assertEqual(data["version"], "1.0.0")
        print("✅ Root API endpoint test passed")

    def test_health_endpoint(self):
        """Test the health check endpoint"""
        response = requests.get(f"{API_URL}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("timestamp", data)
        print("✅ Health endpoint test passed")

    def test_connection_crud_operations(self):
        """Test CRUD operations for VNC connections"""
        # CREATE - Already done in setUp
        print("✅ Connection creation test passed")
        
        # READ - Get all connections
        response = requests.get(f"{API_URL}/connections")
        self.assertEqual(response.status_code, 200)
        connections = response.json()
        self.assertIsInstance(connections, list)
        connection_ids = [conn["id"] for conn in connections]
        self.assertIn(self.connection_id, connection_ids)
        print("✅ Get all connections test passed")
        
        # READ - Get specific connection
        response = requests.get(f"{API_URL}/connections/{self.connection_id}")
        self.assertEqual(response.status_code, 200)
        connection = response.json()
        self.assertEqual(connection["id"], self.connection_id)
        self.assertEqual(connection["name"], self.test_connection_name)
        print("✅ Get connection by ID test passed")
        
        # UPDATE - Update connection status
        response = requests.put(f"{API_URL}/connections/{self.connection_id}/status?status=active")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Status updated successfully")
        
        # Verify status was updated
        response = requests.get(f"{API_URL}/connections/{self.connection_id}")
        connection = response.json()
        self.assertEqual(connection["status"], "active")
        print("✅ Update connection status test passed")
        
        # DELETE - Tested in tearDown
        # Test invalid connection ID
        invalid_id = str(uuid.uuid4())
        response = requests.get(f"{API_URL}/connections/{invalid_id}")
        self.assertEqual(response.status_code, 404)
        print("✅ Invalid connection ID test passed")

    def test_generate_installer(self):
        """Test generating a PowerShell installer"""
        response = requests.get(f"{API_URL}/generate-installer/{self.connection_id}")
        self.assertEqual(response.status_code, 200)
        
        # Check that we got a PowerShell script
        self.assertTrue(response.text.startswith("# VNC Auto-Installation Script"))
        self.assertIn(self.test_connection["installation_key"], response.text)
        
        # Verify TightVNC setup is included
        self.assertIn("TightVNC", response.text)
        self.assertIn("$TightVNC_URL", response.text)
        self.assertIn("Installing TightVNC", response.text)
        
        # Verify registration with server is included
        self.assertIn("Registering with management server", response.text)
        self.assertIn("/api/register-machine", response.text)
        
        print("✅ Generate installer test passed")

    def test_register_machine(self):
        """Test registering a machine after installation"""
        registration_data = {
            "installation_key": self.test_connection["installation_key"],
            "machine_name": f"Test Machine {uuid.uuid4().hex[:8]}",
            "ip_address": "192.168.1.123",
            "status": "active"
        }
        
        response = requests.post(f"{API_URL}/register-machine", json=registration_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Machine registered successfully")
        self.assertEqual(data["connection_id"], self.connection_id)
        
        # Verify the connection status was updated
        response = requests.get(f"{API_URL}/connections/{self.connection_id}")
        connection = response.json()
        self.assertEqual(connection["status"], "active")
        self.assertEqual(connection["ip_address"], "192.168.1.123")
        
        # Test with invalid installation key
        invalid_registration = {
            "installation_key": "invalid_key",
            "machine_name": "Test Machine",
            "ip_address": "192.168.1.100"
        }
        response = requests.post(f"{API_URL}/register-machine", json=invalid_registration)
        self.assertEqual(response.status_code, 404)
        
        print("✅ Register machine test passed")

    def test_stats_endpoint(self):
        """Test the statistics endpoint"""
        response = requests.get(f"{API_URL}/stats")
        self.assertEqual(response.status_code, 200)
        stats = response.json()
        self.assertIn("total_connections", stats)
        self.assertIn("active_connections", stats)
        self.assertIn("inactive_connections", stats)
        self.assertIn("recent_activity_24h", stats)
        self.assertIn("timestamp", stats)
        
        # Verify stats are numbers
        self.assertIsInstance(stats["total_connections"], int)
        self.assertIsInstance(stats["active_connections"], int)
        self.assertIsInstance(stats["inactive_connections"], int)
        self.assertIsInstance(stats["recent_activity_24h"], int)
        
        print("✅ Stats endpoint test passed")

    def test_activity_logs(self):
        """Test activity logs retrieval"""
        # First, register the machine to generate some activity
        registration_data = {
            "installation_key": self.test_connection["installation_key"],
            "machine_name": f"Test Machine {uuid.uuid4().hex[:8]}",
            "ip_address": "192.168.1.123",
            "status": "active"
        }
        requests.post(f"{API_URL}/register-machine", json=registration_data)
        
        # Test getting all logs
        response = requests.get(f"{API_URL}/logs")
        self.assertEqual(response.status_code, 200)
        logs = response.json()
        self.assertIsInstance(logs, list)
        
        # Test getting logs for specific connection
        response = requests.get(f"{API_URL}/logs/{self.connection_id}")
        self.assertEqual(response.status_code, 200)
        connection_logs = response.json()
        self.assertIsInstance(connection_logs, list)
        
        # Verify log structure
        if connection_logs:
            log = connection_logs[0]
            self.assertIn("id", log)
            self.assertIn("connection_id", log)
            self.assertIn("action", log)
            self.assertIn("details", log)
            self.assertIn("timestamp", log)
            
            # Verify this log is for our connection
            self.assertEqual(log["connection_id"], self.connection_id)
        
        print("✅ Activity logs test passed")

    def test_file_management(self):
        """Test file management operations"""
        # First, register the machine to make it active
        registration_data = {
            "installation_key": self.test_connection["installation_key"],
            "machine_name": f"Test Machine {uuid.uuid4().hex[:8]}",
            "ip_address": "192.168.1.123",
            "status": "active"
        }
        requests.post(f"{API_URL}/register-machine", json=registration_data)
        
        # Test file listing
        response = requests.get(f"{API_URL}/files/{self.connection_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["connection_id"], self.connection_id)
        self.assertIn("files", data)
        self.assertIsInstance(data["files"], list)
        print("✅ Files listing test passed")
        
        # Test file upload
        test_file_content = b"This is a test file for VNC Management System"
        test_file = io.BytesIO(test_file_content)
        files = {"file": ("test_file.txt", test_file, "text/plain")}
        
        response = requests.post(
            f"{API_URL}/files/{self.connection_id}/upload",
            files=files
        )
        self.assertEqual(response.status_code, 200)
        upload_data = response.json()
        self.assertEqual(upload_data["filename"], "test_file.txt")
        self.assertEqual(upload_data["size"], len(test_file_content))
        self.assertIn("checksum", upload_data)
        print("✅ File upload test passed")
        
        # Test file download
        response = requests.get(
            f"{API_URL}/files/{self.connection_id}/download",
            params={"file_path": "/test_file.txt"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Content-Disposition", response.headers)
        self.assertIn("attachment; filename=", response.headers["Content-Disposition"])
        print("✅ File download test passed")
        
        # Test file transfer history
        response = requests.get(f"{API_URL}/files/{self.connection_id}/transfers")
        self.assertEqual(response.status_code, 200)
        transfers = response.json()
        self.assertIsInstance(transfers, list)
        
        if transfers:
            transfer = transfers[0]
            self.assertIn("id", transfer)
            self.assertIn("connection_id", transfer)
            self.assertIn("filename", transfer)
            self.assertIn("file_size", transfer)
            self.assertIn("transfer_type", transfer)
            self.assertIn("timestamp", transfer)
            
            # Verify this transfer is for our connection
            self.assertEqual(transfer["connection_id"], self.connection_id)
        
        print("✅ File transfer history test passed")

    def test_vnc_connection(self):
        """Test VNC connection initiation"""
        # First, register the machine to make it active
        registration_data = {
            "installation_key": self.test_connection["installation_key"],
            "machine_name": f"Test Machine {uuid.uuid4().hex[:8]}",
            "ip_address": "192.168.1.123",
            "status": "active"
        }
        requests.post(f"{API_URL}/register-machine", json=registration_data)
        
        # Test VNC connection
        response = requests.post(f"{API_URL}/connect/{self.connection_id}")
        self.assertEqual(response.status_code, 200)
        connection_data = response.json()
        
        self.assertEqual(connection_data["connection_id"], self.connection_id)
        self.assertEqual(connection_data["ip_address"], "192.168.1.123")
        self.assertIn("port", connection_data)
        self.assertIn("password", connection_data)
        self.assertIn("websocket_url", connection_data)
        
        print("✅ VNC connection test passed")

    def test_vnc_screenshot(self):
        """Test getting a VNC screenshot"""
        # First, register the machine to make it active
        registration_data = {
            "installation_key": self.test_connection["installation_key"],
            "machine_name": f"Test Machine {uuid.uuid4().hex[:8]}",
            "ip_address": "192.168.1.123",
            "status": "active"
        }
        requests.post(f"{API_URL}/register-machine", json=registration_data)
        
        # Now test screenshot
        response = requests.get(f"{API_URL}/vnc/{self.connection_id}/screenshot")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "image/svg+xml")
        self.assertIn("<svg", response.text)
        
        # Verify screenshot contains connection name instead of ID
        self.assertIn(self.test_connection_name, response.text)
        
        print("✅ VNC screenshot test passed")

    def test_system_info(self):
        """Test getting system information"""
        response = requests.get(f"{API_URL}/system/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("vnc_management_version", data)
        self.assertIn("system_time", data)
        self.assertIn("features", data)
        self.assertIn("total_websocket_connections", data)
        
        # Verify features
        features = data["features"]
        self.assertIn("vnc_viewer", features)
        self.assertIn("file_manager", features)
        self.assertIn("websocket_proxy", features)
        self.assertIn("screenshot_capture", features)
        
        print("✅ System info test passed")

    def test_mongodb_integration(self):
        """Test MongoDB integration by verifying data persistence"""
        # Create a unique connection for this test
        test_name = f"MongoDB Test {uuid.uuid4().hex[:8]}"
        test_data = {
            "name": test_name,
            "location": "Database Lab",
            "country": "Russia",
            "city": "St. Petersburg"
        }
        
        # Create connection
        response = requests.post(f"{API_URL}/connections", json=test_data)
        self.assertEqual(response.status_code, 200)
        connection = response.json()
        test_id = connection["id"]
        
        try:
            # Verify connection was stored in MongoDB by retrieving it
            response = requests.get(f"{API_URL}/connections/{test_id}")
            self.assertEqual(response.status_code, 200)
            retrieved = response.json()
            self.assertEqual(retrieved["name"], test_name)
            self.assertEqual(retrieved["location"], "Database Lab")
            
            # Update status
            requests.put(f"{API_URL}/connections/{test_id}/status?status=active")
            
            # Verify update was persisted
            response = requests.get(f"{API_URL}/connections/{test_id}")
            updated = response.json()
            self.assertEqual(updated["status"], "active")
            
            # Check logs were created
            response = requests.get(f"{API_URL}/logs/{test_id}")
            logs = response.json()
            self.assertIsInstance(logs, list)
            
            print("✅ MongoDB integration test passed")
            
        finally:
            # Clean up
            requests.delete(f"{API_URL}/connections/{test_id}")

    def test_websocket_endpoints(self):
        """Test WebSocket endpoints existence (actual WebSocket testing would require a WebSocket client)"""
        # We can't fully test WebSockets here, but we can check system info for WebSocket data
        response = requests.get(f"{API_URL}/system/info")
        data = response.json()
        
        # Verify WebSocket features are enabled
        self.assertTrue(data["features"]["websocket_proxy"])
        
        # Check WebSocket connection count is available
        self.assertIn("total_websocket_connections", data)
        self.assertIn("active_websockets", data)
        
        print("✅ WebSocket endpoints verification passed")

if __name__ == "__main__":
    unittest.main(verbosity=2)