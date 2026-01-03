import unittest
from unittest.mock import MagicMock, patch
from flask import Flask, session
from backend.routes.login_route import login_bp, init_login_routes

class TestAuth(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'test_secret'
        self.db_mock = MagicMock()
        init_login_routes(self.app, self.db_mock)
        self.client = self.app.test_client()

    def test_login_success_existing_user(self):
        # Mock Firestore response for an existing user
        mock_user_doc = MagicMock()
        mock_user_doc.id = 'test_uid'
        mock_user_doc.to_dict.return_value = {
            'email': 'test@example.com',
            'password': 'password123',
            'role': 'Student',
            'name': 'Test User'
        }
        
        # Mock the query: db.collection('users').where(...).limit(1).get()
        self.db_mock.collection.return_value.where.return_value.limit.return_value.get.return_value = [mock_user_doc]

        response = self.client.post('/api/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['success'])
        self.assertEqual(response.json['user']['uid'], 'test_uid')

    def test_login_failure_wrong_password(self):
        # Mock Firestore response
        mock_user_doc = MagicMock()
        mock_user_doc.to_dict.return_value = {
            'email': 'test@example.com',
            'password': 'password123'
        }
        self.db_mock.collection.return_value.where.return_value.limit.return_value.get.return_value = [mock_user_doc]

        response = self.client.post('/api/login', json={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json['success'])

    def test_first_time_login_student(self):
        # Mock Firestore response for a user WITHOUT a password field
        mock_user_doc = MagicMock()
        mock_user_doc.id = 'new_student_uid'
        mock_user_doc.to_dict.return_value = {
            'email': 'new@student.edu.in',
            'role': 'Student'
            # No 'password' field
        }
        self.db_mock.collection.return_value.where.return_value.limit.return_value.get.return_value = [mock_user_doc]

        response = self.client.post('/api/login', json={
            'email': 'new@student.edu.in',
            'password': 'student123' # Default password
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['success'])
        self.assertTrue(response.json.get('password_update_required'))

if __name__ == '__main__':
    unittest.main()
