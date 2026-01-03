import unittest
from unittest.mock import MagicMock, patch
from flask import Flask, session
from backend.routes.admin_routes import admin_bp, init_admin_routes

class TestAdminSecurity(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'test_secret'
        self.db_mock = MagicMock()
        init_admin_routes(self.app, self.db_mock)
        self.client = self.app.test_client()

    def test_get_users_unauthorized(self):
        """Test that accessing /users without login returns 401"""
        response = self.client.get('/api/admin/users')
        self.assertEqual(response.status_code, 401)
        self.assertIn('Authentication required', response.json['error'])

    def test_get_users_authorized_admin(self):
        """Test that accessing /users with Admin role works"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'admin_123'
            sess['role'] = 'Admin'

        # Mock the stream for get_users
        mock_user = MagicMock()
        mock_user.id = 'user1'
        mock_user.to_dict.return_value = {'name': 'Alice', 'role': 'Student', 'email': 'alice@example.com'}
        
        # Mock logic: db.collection('users').where(...).stream() or just .start()
        # The code does: users_ref = db.collection('users'); query...; query.stream()
        
        # We need to act carefully on the mock chain
        # If no search is provided, query = users_ref.
        # users_ref.stream() is called.
        
        self.db_mock.collection.return_value.stream.return_value = [mock_user]
        self.db_mock.collection.return_value.order_by.return_value.limit.return_value.offset.return_value.stream.return_value = [mock_user]

        response = self.client.get('/api/admin/users')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['users']), 1)

    def test_get_users_unauthorized_student(self):
        """Test that accessing admin routes as a Student returns 401"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'student_123'
            sess['role'] = 'Student'
            
        response = self.client.get('/api/admin/users')
        self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
    unittest.main()
