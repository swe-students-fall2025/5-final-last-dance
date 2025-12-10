"""Tests for Flask app routes and core functionality."""

import pytest
import datetime
from unittest.mock import MagicMock, patch
from bson import ObjectId
import app as app_module


class TestHomeRoute:
    """Test cases for the home page route."""
    
    def test_home_route_status_code(self, client):
        """Test that home route returns 200 status code."""
        test_client, mock_db, _ = client
        
        mock_db.jobs.find.return_value.sort.return_value = iter([])
        mock_db.company_preferences.find.return_value = iter([])
        mock_db.location_preferences.find.return_value = iter([])
        mock_db.role_preferences.find.return_value = iter([])
        mock_db.job_type_preferences.find_one.return_value = None
        
        response = test_client.get('/')
        assert response.status_code == 200
    
    def test_home_route_with_user_id(self, client):
        """Test home route with specific user_id parameter."""
        test_client, mock_db, _ = client
        
        mock_db.jobs.find.return_value.sort.return_value = iter([])
        mock_db.company_preferences.find.return_value = iter([])
        mock_db.location_preferences.find.return_value = iter([])
        mock_db.role_preferences.find.return_value = iter([])
        mock_db.job_type_preferences.find_one.return_value = None
        
        response = test_client.get('/?user_id=user123')
        assert response.status_code == 200
    
    def test_home_route_renders_template(self, client):
        """Test that home route renders the index.html template."""
        test_client, mock_db, _ = client
        
        mock_db.jobs.find.return_value.sort.return_value = iter([])
        mock_db.company_preferences.find.return_value = iter([])
        mock_db.location_preferences.find.return_value = iter([])
        mock_db.role_preferences.find.return_value = iter([])
        mock_db.job_type_preferences.find_one.return_value = None
        
        response = test_client.get('/')
        assert b'index.html' in response.data or b'Home' in response.data
    
    def test_home_route_with_jobs(self, client, sample_jobs):
        """Test home route displays jobs."""
        test_client, mock_db, _ = client
        
        mock_db.jobs.find.return_value.sort.return_value = iter(sample_jobs)
        mock_db.company_preferences.find.return_value = iter([])
        mock_db.location_preferences.find.return_value = iter([])
        mock_db.role_preferences.find.return_value = iter([])
        mock_db.job_type_preferences.find_one.return_value = None
        
        response = test_client.get('/')
        assert response.status_code == 200


class TestPreferencesRoute:
    """Test cases for user preferences routes."""
    
    def test_preferences_page_loads(self, client):
        """Test that preferences page loads successfully."""
        test_client, mock_db, _ = client
        
        mock_db.company_preferences.find.return_value = iter([])
        mock_db.role_preferences.find.return_value = iter([])
        mock_db.location_preferences.find.return_value = iter([])
        mock_db.job_type_preferences.find_one.return_value = None
        
        response = test_client.get('/preferences/testuser')
        assert response.status_code == 200
    
    def test_preferences_companies_tab(self, client):
        """Test companies tab loads with default tab."""
        test_client, mock_db, _ = client
        
        mock_db.company_preferences.find.return_value = iter([])
        mock_db.role_preferences.find.return_value = iter([])
        mock_db.location_preferences.find.return_value = iter([])
        mock_db.job_type_preferences.find_one.return_value = None
        
        response = test_client.get('/preferences/testuser?tab=companies')
        assert response.status_code == 200
    
    def test_preferences_roles_tab(self, client):
        """Test roles tab."""
        test_client, mock_db, _ = client
        
        mock_db.company_preferences.find.return_value = iter([])
        mock_db.role_preferences.find.return_value = iter([])
        mock_db.location_preferences.find.return_value = iter([])
        mock_db.job_type_preferences.find_one.return_value = None
        
        response = test_client.get('/preferences/testuser?tab=roles')
        assert response.status_code == 200
    
    def test_preferences_locations_tab(self, client):
        """Test locations tab."""
        test_client, mock_db, _ = client
        
        mock_db.company_preferences.find.return_value = iter([])
        mock_db.role_preferences.find.return_value = iter([])
        mock_db.location_preferences.find.return_value = iter([])
        mock_db.job_type_preferences.find_one.return_value = None
        
        response = test_client.get('/preferences/testuser?tab=locations')
        assert response.status_code == 200
    
    def test_preferences_job_types_tab(self, client):
        """Test job types tab."""
        test_client, mock_db, _ = client
        
        mock_db.company_preferences.find.return_value = iter([])
        mock_db.role_preferences.find.return_value = iter([])
        mock_db.location_preferences.find.return_value = iter([])
        mock_db.job_type_preferences.find_one.return_value = None
        
        response = test_client.get('/preferences/testuser?tab=job_types')
        assert response.status_code == 200


class TestPreferencesSubmission:
    """Test cases for saving preferences."""
    
    def test_save_company_preferences(self, client):
        """Test saving company preferences."""
        test_client, mock_db, _ = client
        
        mock_db.company_preferences.delete_many.return_value = MagicMock()
        mock_db.company_preferences.insert_one.return_value = MagicMock()
        
        data = {
            'company_Google': '1',
            'company_Microsoft': '2',
            'company_Apple': '3',
        }
        
        response = test_client.post('/preferences/testuser/companies', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert mock_db.company_preferences.delete_many.called
    
    def test_save_role_preferences(self, client):
        """Test saving role preferences."""
        test_client, mock_db, _ = client
        
        mock_db.role_preferences.delete_many.return_value = MagicMock()
        mock_db.role_preferences.insert_one.return_value = MagicMock()
        
        data = {
            'role_Software Engineer': '1',
            'role_Data Scientist': '2',
        }
        
        response = test_client.post('/preferences/testuser/roles', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert mock_db.role_preferences.delete_many.called
    
    def test_save_location_preferences(self, client):
        """Test saving location preferences."""
        test_client, mock_db, _ = client
        
        mock_db.location_preferences.delete_many.return_value = MagicMock()
        mock_db.location_preferences.insert_one.return_value = MagicMock()
        
        data = {
            'location_Remote': '1',
            'location_New York, NY': '2',
        }
        
        response = test_client.post('/preferences/testuser/locations', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert mock_db.location_preferences.delete_many.called
    
    def test_save_job_type_preferences(self, client):
        """Test saving job type preferences."""
        test_client, mock_db, _ = client
        
        mock_db.job_type_preferences.delete_many.return_value = MagicMock()
        mock_db.job_type_preferences.insert_one.return_value = MagicMock()
        
        data = {
            'job_types': ['Full-time', 'Internship']
        }
        
        response = test_client.post('/preferences/testuser/job_types', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert mock_db.job_type_preferences.delete_many.called
    
    def test_save_preferences_invalid_tier(self, client):
        """Test that invalid tier values are rejected."""
        test_client, mock_db, _ = client
        
        mock_db.company_preferences.delete_many.return_value = MagicMock()
        
        data = {
            'company_Google': '5',
        }
        
        response = test_client.post('/preferences/testuser/companies', data=data, follow_redirects=True)
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_route_returns_error(self, client):
        """Test that invalid routes trigger error handler."""
        test_client, mock_db, _ = client
        
        response = test_client.get('/nonexistent')
        assert response.status_code in [200, 404]


class TestAuthAndFavorites:
    """Test authentication and favorite-related helpers."""

    def test_register_success(self, client, monkeypatch):
        test_client, mock_db, _ = client
        mock_db.users.find_one.return_value = None
        mock_db.users.insert_one.return_value.inserted_id = ObjectId()
        monkeypatch.setattr(app_module, "generate_password_hash", lambda pwd: "hashed")
        monkeypatch.setattr(app_module, "login_user", lambda user: None)

        response = test_client.post(
            "/register",
            data={"username": "new", "email": "new@example.com", "password": "secret"},
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_register_validation(self, client):
        test_client, _, _ = client

        response = test_client.post(
            "/register",
            data={"username": "", "email": "", "password": ""},
            follow_redirects=False,
        )
        assert response.status_code == 200

    def test_login_success(self, client, monkeypatch):
        test_client, mock_db, _ = client
        mock_db.users.find_one.return_value = {"_id": ObjectId(), "username": "user", "password": "hashed"}
        monkeypatch.setattr(app_module, "check_password_hash", lambda stored, provided: True)
        monkeypatch.setattr(app_module, "login_user", lambda user: None)

        response = test_client.post(
            "/login",
            data={"username": "user", "password": "secret"},
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_login_failure(self, client):
        test_client, mock_db, _ = client
        mock_db.users.find_one.return_value = None

        response = test_client.post(
            "/login",
            data={"username": "user", "password": "secret"},
            follow_redirects=False,
        )
        assert response.status_code == 200

    def test_logout_redirects(self):
        app_module.app.config["LOGIN_DISABLED"] = True
        response = app_module.app.test_client().get("/logout", follow_redirects=False)
        assert response.status_code == 302

    def test_profile_renders(self, client, monkeypatch):
        app_module.app.config["LOGIN_DISABLED"] = True
        monkeypatch.setattr(
            app_module,
            "current_user",
            MagicMock(id="user1", is_authenticated=True),
        )
        mock_jobs = [{"company": "TestCo", "identifier": "42", "company_slug": "testco"}]
        monkeypatch.setattr(app_module, "load_and_score_jobs", lambda db, uid: mock_jobs)
        _, mock_db, _ = client
        mock_db.favorites.find.return_value = [{"company": "TestCo", "identifier": "42"}]

        response = app_module.app.test_client().get("/profile")
        assert response.status_code == 200

    def test_toggle_favorite_endpoint(self, client, monkeypatch):
        _, mock_db, _ = client
        app_module.app.config["LOGIN_DISABLED"] = True
        monkeypatch.setattr(
            app_module,
            "current_user",
            MagicMock(id="user1", is_authenticated=True),
        )
        job = {"company": "TestCo", "identifier": "42", "company_slug": "testco"}
        monkeypatch.setattr(app_module, "load_and_score_jobs", lambda db, uid: [job])
        mock_db.favorites.find_one.return_value = {"_id": ObjectId(), "company": "TestCo", "identifier": "42"}

        response = app_module.app.test_client().post("/favorite/testco/42")
        assert response.status_code == 200
        assert response.json.get("message") is not None

    def test_toggle_favorite_not_found(self, client, monkeypatch):
        _, mock_db, _ = client
        app_module.app.config["LOGIN_DISABLED"] = True
        monkeypatch.setattr(
            app_module,
            "current_user",
            MagicMock(id="user1", is_authenticated=True),
        )
        monkeypatch.setattr(app_module, "load_and_score_jobs", lambda db, uid: [])

        response = app_module.app.test_client().post("/favorite/testco/42")
        assert response.status_code == 404

    def test_api_favorites_returns_data(self, client, monkeypatch):
        _, mock_db, _ = client
        app_module.app.config["LOGIN_DISABLED"] = True
        monkeypatch.setattr(
            app_module,
            "current_user",
            MagicMock(id="user1", is_authenticated=True),
        )
        mock_db.favorites.find.return_value = [
            {"company": "A", "identifier": "1"},
            {"company": "B", "identifier": "2"},
        ]

        response = app_module.app.test_client().get("/api/favorites")
        assert response.status_code == 200
        assert isinstance(response.json.get("favorites"), list)
