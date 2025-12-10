"""Pytest configuration and fixtures for Last Dance tests."""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pymongo.errors import ConnectionFailure


@pytest.fixture
def app():
    """Create and configure a test Flask app."""
    with patch('pymongo.MongoClient') as mock_client:
        mock_db = MagicMock()
        mock_client.return_value.admin.command.return_value = None
        mock_client.return_value.__getitem__.return_value = mock_db
        
        os.environ['MONGO_URI'] = 'mongodb://test:test@localhost:27017/'
        os.environ['MONGO_DBNAME'] = 'test_db'
        
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        
        return app, mock_db, mock_client


@pytest.fixture
def client(app):
    """Create a test client."""
    app_instance, mock_db, mock_client = app
    return app_instance.test_client(), mock_db, mock_client


@pytest.fixture
def sample_job():
    """Create a sample job document."""
    import datetime
    from bson import ObjectId
    
    return {
        '_id': ObjectId(),
        'title': 'Software Engineer',
        'company': 'Google',
        'location': 'San Francisco, CA',
        'type': 'Full-time',
        'summary': 'Build amazing products',
        'tags': ['python', 'backend'],
        'posted_date': datetime.datetime.now(datetime.timezone.utc),
        'match_score': 85
    }


@pytest.fixture
def sample_jobs(sample_job):
    """Create multiple sample jobs."""
    import datetime
    from bson import ObjectId
    
    job2 = sample_job.copy()
    job2['_id'] = ObjectId()
    job2['title'] = 'Data Scientist'
    job2['company'] = 'Meta'
    job2['location'] = 'Remote'
    job2['match_score'] = 72
    
    job3 = sample_job.copy()
    job3['_id'] = ObjectId()
    job3['title'] = 'DevOps Engineer'
    job3['company'] = 'Amazon'
    job3['location'] = 'New York, NY'
    job3['match_score'] = 65
    
    return [sample_job, job2, job3]
