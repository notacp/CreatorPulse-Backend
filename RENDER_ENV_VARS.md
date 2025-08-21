# Required Environment Variables for Render Deployment

## Supabase Configuration (Required)

Add these environment variables to your Render backend service:

```bash
# Supabase Configuration
SUPABASE_URL=https://abgwjbqfhrbmzotwabne.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiZ3dqYnFmaHJibXpvdHdhYm5lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjQ2NjI4NzMsImV4cCI6MjA0MDIzODg3M30.SIp6NjGjUBk0jl5b7J6vJLvL2V5bQ4Wq3vX6Q7cV9Y8
SUPABASE_SERVICE_KEY=your_supabase_service_key_here

# Database (should already be set)
DATABASE_URL=your_render_postgresql_url

# JWT Secret (should already be set)
JWT_SECRET_KEY=your_jwt_secret_key

# Optional: Other environment variables
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

## Important Notes

1. **SUPABASE_SERVICE_KEY**: You need to get this from your Supabase dashboard
   - Go to Project Settings → API
   - Copy the "service_role" key (NOT the anon key)
   - This key has admin privileges to create/manage users

2. **Email Configuration**: Supabase will handle email verification
   - Make sure email templates are configured in Supabase
   - Set up your domain for email sending if needed

3. **Authentication Flow**:
   - Registration: Creates user in both Supabase and your database
   - Login: Authenticates via Supabase, requires email verification
   - Password Reset: Handled entirely by Supabase

## Testing

After setting environment variables:

1. **Register a new user** → Should appear in Supabase Auth users
2. **Check email** → Should receive verification email from Supabase
3. **Verify email** → Click link in email
4. **Login** → Should work after email verification

## Getting Supabase Service Key

1. Go to your Supabase project dashboard
2. Click on "Settings" in the sidebar
3. Click on "API" in the settings menu
4. Under "Project API keys", copy the "service_role" key
5. Add it as `SUPABASE_SERVICE_KEY` environment variable in Render
