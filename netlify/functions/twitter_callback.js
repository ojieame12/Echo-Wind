const { PythonBridge } = require('python-bridge');

exports.handler = async function(event, context) {
  try {
    const python = new PythonBridge();
    
    // Import our Python code
    await python.ex`
      import sys
      sys.path.append('.')
      from platforms.auth import PlatformAuthManager
      from models.models import User, PlatformAccount, PlatformType
      from api.deps import get_db
    `;
    
    // Get query parameters
    const { code, state, email } = event.queryStringParameters;
    
    // Handle the callback in Python
    const result = await python.ex`
      auth_manager = PlatformAuthManager()
      credentials = await auth_manager.handle_twitter_callback(code, state)
      
      # Get database session
      db = next(get_db())
      
      # Get user
      user = db.query(User).filter_by(email=email).first()
      if not user:
          raise Exception("User not found")
      
      # Create or update platform account
      platform = db.query(PlatformAccount).filter_by(
          user_id=user.id,
          platform=PlatformType.TWITTER
      ).first()
      
      if platform:
          platform.credentials = credentials
          platform.is_active = True
          platform.username = credentials["username"]
      else:
          platform = PlatformAccount(
              user_id=user.id,
              platform=PlatformType.TWITTER,
              username=credentials["username"],
              credentials=credentials,
              is_active=True
          )
          db.add(platform)
          
      db.commit()
      
      result = {
          "success": True,
          "username": credentials["username"]
      }
    `;
    
    return {
      statusCode: 200,
      body: JSON.stringify(result)
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message })
    };
  }
}
