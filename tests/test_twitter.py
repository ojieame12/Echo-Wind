import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from api.routes.twitter import router
from models.models import User, PlatformAccount, PlatformType

@pytest.fixture
def mock_twitter_client():
    with patch('platforms.twitter.TwitterClient') as mock:
        yield mock

@pytest.fixture
def mock_auth_manager():
    with patch('platforms.auth.PlatformAuthManager') as mock:
        yield mock

def test_twitter_auth_flow(mock_auth_manager, test_db: Session, test_client: TestClient):
    # Mock auth URL generation
    mock_auth_manager.return_value.get_twitter_auth_url.return_value = "https://twitter.com/oauth/authorize"
    
    # Test getting auth URL
    response = test_client.get("/platforms/twitter/auth")
    assert response.status_code == 200
    assert response.json()["auth_url"] == "https://twitter.com/oauth/authorize"

    # Mock callback handling
    mock_credentials = {
        "access_token": "test_token",
        "refresh_token": "test_refresh",
        "username": "test_user",
        "user_id": "12345"
    }
    mock_auth_manager.return_value.handle_twitter_callback.return_value = mock_credentials
    
    # Test callback
    response = test_client.post(
        "/platforms/twitter/callback",
        json={"code": "test_code"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "test_user"
    
    # Verify platform account was created
    platform = test_db.query(PlatformAccount).filter_by(
        platform=PlatformType.TWITTER
    ).first()
    assert platform is not None
    assert platform.username == "test_user"
    assert platform.is_active == True

def test_twitter_post_content(mock_twitter_client, test_db: Session, test_client: TestClient):
    # Mock successful post
    mock_response = {
        "success": True,
        "post_id": "123456",
        "url": "https://twitter.com/user/status/123456"
    }
    mock_twitter_client.return_value.post_content.return_value = mock_response
    
    # Create test content piece
    from models.models import ContentPiece, ContentStatus
    content = ContentPiece(
        content="Test tweet",
        status=ContentStatus.DRAFT,
        meta_data={"hashtags": ["#test"]}
    )
    test_db.add(content)
    test_db.commit()
    
    # Test posting
    response = test_client.post(f"/platforms/twitter/post/{content.id}")
    assert response.status_code == 200
    assert response.json()["post_id"] == "123456"
    
    # Verify content was updated
    content = test_db.query(ContentPiece).filter_by(id=content.id).first()
    assert content.status == ContentStatus.PUBLISHED
    assert content.meta_data["twitter_post_id"] == "123456"

def test_twitter_delete_post(mock_twitter_client, test_db: Session, test_client: TestClient):
    # Mock successful delete
    mock_twitter_client.return_value.delete_post.return_value = True
    
    # Create test content piece with existing Twitter post
    from models.models import ContentPiece, ContentStatus
    content = ContentPiece(
        content="Test tweet",
        status=ContentStatus.PUBLISHED,
        meta_data={
            "twitter_post_id": "123456",
            "twitter_url": "https://twitter.com/user/status/123456"
        }
    )
    test_db.add(content)
    test_db.commit()
    
    # Test deletion
    response = test_client.delete(f"/platforms/twitter/post/{content.id}")
    assert response.status_code == 200
    
    # Verify content was updated
    content = test_db.query(ContentPiece).filter_by(id=content.id).first()
    assert content.status == ContentStatus.DRAFT
    assert "twitter_post_id" not in content.meta_data
