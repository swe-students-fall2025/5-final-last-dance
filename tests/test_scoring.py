"""Tests for job scoring algorithm."""

import pytest
import datetime
from unittest.mock import MagicMock, patch
from bson import ObjectId


class TestJobScoringAlgorithm:
    """Test cases for score_jobs_for_user function."""
    
    def setup_method(self):
        """Set up test fixtures before each test."""
        from app import score_jobs_for_user
        self.score_jobs_for_user = score_jobs_for_user
    
    def create_mock_db(self):
        """Create a mock database object."""
        mock_db = MagicMock()
        return mock_db
    
    def test_empty_jobs_list(self):
        """Test scoring with empty jobs list."""
        mock_db = self.create_mock_db()
        mock_db.company_preferences.find.return_value = []
        mock_db.location_preferences.find.return_value = []
        mock_db.role_preferences.find.return_value = []
        mock_db.job_type_preferences.find_one.return_value = None
        
        result = self.score_jobs_for_user(mock_db, 'user1', [])
        assert result == []
    
    def test_jobs_without_preferences(self):
        """Test scoring jobs when user has no preferences."""
        mock_db = self.create_mock_db()
        mock_db.company_preferences.find.return_value = []
        mock_db.location_preferences.find.return_value = []
        mock_db.role_preferences.find.return_value = []
        mock_db.job_type_preferences.find_one.return_value = None
        
        jobs = [
            {
                'title': 'Software Engineer',
                'company': 'Google',
                'location': 'San Francisco, CA',
                'type': 'Full-time',
                'posted_date': datetime.datetime.now(datetime.timezone.utc),
            }
        ]
        
        result = self.score_jobs_for_user(mock_db, 'user1', jobs)
        assert len(result) == 1
        assert 'match_score' in result[0]
        assert 0 <= result[0]['match_score'] <= 100
    
    def test_company_preference_scoring(self):
        """Test that company preferences affect scoring."""
        mock_db = self.create_mock_db()
        
        mock_db.company_preferences.find.return_value = [
            {'company': 'Google', 'rank': 1}
        ]
        mock_db.location_preferences.find.return_value = []
        mock_db.role_preferences.find.return_value = []
        mock_db.job_type_preferences.find_one.return_value = None
        
        jobs = [
            {
                'title': 'Engineer',
                'company': 'Google',
                'posted_date': datetime.datetime.now(datetime.timezone.utc),
            },
            {
                'title': 'Engineer',
                'company': 'Microsoft',
                'posted_date': datetime.datetime.now(datetime.timezone.utc),
            }
        ]
        
        result = self.score_jobs_for_user(mock_db, 'user1', jobs)
        
        google_job = next(j for j in result if j['company'] == 'Google')
        microsoft_job = next(j for j in result if j['company'] == 'Microsoft')
        
        assert google_job['match_score'] > microsoft_job['match_score']
    
    def test_location_preference_scoring(self):
        """Test that location preferences affect scoring."""
        mock_db = self.create_mock_db()
        
        mock_db.company_preferences.find.return_value = []
        mock_db.location_preferences.find.return_value = [
            {'location': 'Remote', 'rank': 1}
        ]
        mock_db.role_preferences.find.return_value = []
        mock_db.job_type_preferences.find_one.return_value = None
        
        jobs = [
            {
                'title': 'Engineer',
                'location': 'Remote',
                'posted_date': datetime.datetime.now(datetime.timezone.utc),
            },
            {
                'title': 'Engineer',
                'location': 'New York, NY',
                'posted_date': datetime.datetime.now(datetime.timezone.utc),
            }
        ]
        
        result = self.score_jobs_for_user(mock_db, 'user1', jobs)
        
        remote_job = next(j for j in result if j.get('location') == 'Remote')
        ny_job = next(j for j in result if j.get('location') == 'New York, NY')
        
        assert remote_job['match_score'] > ny_job['match_score']
    
    def test_role_preference_scoring(self):
        """Test that role preferences affect scoring."""
        mock_db = self.create_mock_db()
        
        mock_db.company_preferences.find.return_value = []
        mock_db.location_preferences.find.return_value = []
        mock_db.role_preferences.find.return_value = [
            {'role': 'Backend Developer', 'rank': 1}
        ]
        mock_db.job_type_preferences.find_one.return_value = None
        
        jobs = [
            {
                'title': 'Backend Developer',
                'posted_date': datetime.datetime.now(datetime.timezone.utc),
            },
            {
                'title': 'Frontend Developer',
                'posted_date': datetime.datetime.now(datetime.timezone.utc),
            }
        ]
        
        result = self.score_jobs_for_user(mock_db, 'user1', jobs)
        
        backend_job = next(j for j in result if 'Backend' in j['title'])
        frontend_job = next(j for j in result if 'Frontend' in j['title'])
        
        assert backend_job['match_score'] > frontend_job['match_score']
    
    def test_job_type_preference_scoring(self):
        """Test that job type preferences affect scoring."""
        mock_db = self.create_mock_db()
        
        mock_db.company_preferences.find.return_value = []
        mock_db.location_preferences.find.return_value = []
        mock_db.role_preferences.find.return_value = []
        mock_db.job_type_preferences.find_one.return_value = {
            'types': ['Full-time', 'Internship']
        }
        
        jobs = [
            {
                'title': 'Engineer',
                'type': 'Full-time',
                'posted_date': datetime.datetime.now(datetime.timezone.utc),
            },
            {
                'title': 'Engineer',
                'type': 'Contract',
                'posted_date': datetime.datetime.now(datetime.timezone.utc),
            }
        ]
        
        result = self.score_jobs_for_user(mock_db, 'user1', jobs)
        
        fulltime_job = next(j for j in result if j.get('type') == 'Full-time')
        contract_job = next(j for j in result if j.get('type') == 'Contract')
        
        assert fulltime_job['match_score'] > contract_job['match_score']
    
    def test_score_bounded_0_to_100(self):
        """Test that scores are always between 0 and 100."""
        mock_db = self.create_mock_db()
        
        mock_db.company_preferences.find.return_value = [
            {'company': 'Google', 'rank': 1}
        ]
        mock_db.location_preferences.find.return_value = [
            {'location': 'Remote', 'rank': 1}
        ]
        mock_db.role_preferences.find.return_value = [
            {'role': 'Software Engineer', 'rank': 1}
        ]
        mock_db.job_type_preferences.find_one.return_value = {
            'types': ['Full-time']
        }
        
        jobs = [
            {
                'title': 'Software Engineer',
                'company': 'Google',
                'location': 'Remote',
                'type': 'Full-time',
                'posted_date': datetime.datetime.now(datetime.timezone.utc),
            }
        ]
        
        result = self.score_jobs_for_user(mock_db, 'user1', jobs)
        
        assert result[0]['match_score'] <= 100
        assert result[0]['match_score'] >= 0
    
    def test_recency_boost_for_new_jobs(self):
        """Test that newer jobs get a recency boost."""
        mock_db = self.create_mock_db()
        mock_db.company_preferences.find.return_value = []
        mock_db.location_preferences.find.return_value = []
        mock_db.role_preferences.find.return_value = []
        mock_db.job_type_preferences.find_one.return_value = None
        
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        old_date = today - datetime.timedelta(days=30)
        
        jobs = [
            {
                'title': 'Engineer',
                'posted_date': now,
            },
            {
                'title': 'Engineer',
                'posted_date': old_date,
            }
        ]
        
        result = self.score_jobs_for_user(mock_db, 'user1', jobs)
        
        assert result[0]['match_score'] > result[1]['match_score']
    
    def test_posted_date_formatting(self):
        """Test that posted_date is formatted as 'posted' field."""
        mock_db = self.create_mock_db()
        mock_db.company_preferences.find.return_value = []
        mock_db.location_preferences.find.return_value = []
        mock_db.role_preferences.find.return_value = []
        mock_db.job_type_preferences.find_one.return_value = None
        
        now = datetime.datetime.now(datetime.timezone.utc)
        
        jobs = [
            {
                'title': 'Engineer',
                'posted_date': now,
            }
        ]
        
        result = self.score_jobs_for_user(mock_db, 'user1', jobs)
        
        assert 'posted' in result[0]
        assert isinstance(result[0]['posted'], str)
