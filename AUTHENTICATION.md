# Authentication & Authorization System

This document describes the comprehensive JWT-based authentication and role-based access control (RBAC) system implemented for the Financial Document Analyzer.

## Features

### 🔐 Authentication

- **JWT-based authentication** with access and refresh tokens
- **Secure password hashing** using Argon2
- **Token refresh mechanism** for seamless user experience
- **Account verification** system (ready for email verification)
- **Password strength validation** with configurable requirements

### 🛡️ Authorization

- **Role-based access control (RBAC)** with three predefined roles:
  - **Admin**: Full system access
  - **Analyst**: Document and analysis management
  - **Viewer**: Read-only access
- **Permission-based authorization** for granular access control
- **Resource-level permissions** (users, documents, analyses, roles, system)

### 🚦 Rate Limiting

- **API rate limiting** per user/IP with Redis backend
- **Upload rate limiting** to prevent abuse
- **Configurable limits** and time windows
- **Automatic retry-after headers**

### 🔍 Security Features

- **Input sanitization** to prevent XSS attacks
- **File upload validation** with type and size restrictions
- **Audit logging** for all user actions
- **Secure file handling** with hash-based deduplication
- **CORS configuration** for cross-origin requests

## Architecture

### Database Models

#### User Management

- `User`: Core user information and authentication
- `Role`: System roles with descriptions
- `Permission`: Granular permissions for resources
- `UserRole`: Many-to-many relationship between users and roles
- `RolePermission`: Many-to-many relationship between roles and permissions
- `RefreshToken`: Secure token management with device tracking

#### Document & Analysis

- `Document`: File metadata and processing status
- `Analysis`: Analysis results and metadata
- `AuditLog`: Comprehensive activity logging

### Security Components

#### JWT Token Management

```python
# Access tokens (short-lived, 15 minutes)
{
  "sub": "user_id",
  "username": "username",
  "exp": timestamp,
  "iat": timestamp,
  "jti": "unique_token_id",
  "type": "access"
}

# Refresh tokens (long-lived, 30 days)
# Stored as hashed values in database
```

#### Password Security

- **Argon2** hashing algorithm (industry standard)
- **Configurable strength requirements**:
  - Minimum length (default: 8 characters)
  - Uppercase, lowercase, digits required
  - Special characters (configurable)
- **Password change** forces token revocation

#### Rate Limiting

- **Redis-backed** distributed rate limiting
- **Per-user and per-IP** limits
- **Sliding window** implementation
- **Configurable limits**:
  - API requests: 100/hour (default)
  - File uploads: 10/hour (default)

## API Endpoints

### Authentication Endpoints

#### POST `/api/v1/auth/register`

Register a new user account.

**Request:**

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:**

```json
{
  "id": "uuid",
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_verified": false,
  "roles": ["viewer"]
}
```

#### POST `/api/v1/auth/login`

Authenticate user and receive tokens.

**Request:**

```json
{
  "username": "johndoe",
  "password": "SecurePass123!"
}
```

**Response:**

```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "refresh_token": "refresh_token",
  "expires_in": 900
}
```

#### POST `/api/v1/auth/refresh`

Refresh access token using refresh token.

**Request:**

```json
{
  "refresh_token": "refresh_token"
}
```

#### POST `/api/v1/auth/logout`

Logout user and revoke all refresh tokens.

#### GET `/api/v1/auth/me`

Get current user information.

#### PUT `/api/v1/auth/me`

Update current user profile.

#### POST `/api/v1/auth/change-password`

Change user password.

### Protected Endpoints

#### POST `/api/v1/analyze`

Analyze financial document (requires analyst or admin role).

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request:**

```
Content-Type: multipart/form-data
file: <file>
query: "Analyze this financial document"
```

### Admin Endpoints

#### GET `/api/v1/auth/users`

List all users (admin only).

#### GET `/api/v1/auth/roles`

List all roles and permissions (admin only).

## Configuration

### Environment Variables

Create a `.env` file based on `env.example`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/financial_analyzer

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET=your-super-secret-jwt-key-that-is-at-least-32-characters-long
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=3600
UPLOAD_RATE_LIMIT=10
UPLOAD_RATE_WINDOW_SECONDS=3600

# File Upload
MAX_UPLOAD_SIZE=10485760  # 10 MB
ALLOWED_UPLOAD_EXTENSIONS=.pdf,.txt,.doc,.docx

# Security
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_SPECIAL_CHARS=true

# API
API_V1_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Database

```bash
# Initialize database with default data
python setup.py init

# Create admin user
python setup.py admin

# Or run full setup
python setup.py full
```

### 3. Start the Application

```bash
python main.py
```

### 4. Access API Documentation

- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`

## Default Roles and Permissions

### Admin Role

- **Full system access**
- User management (create, read, update, delete)
- Document management (all operations)
- Analysis management (all operations)
- Role and permission management
- System administration
- Audit log access

### Analyst Role

- **Document and analysis focus**
- Document operations (read, write, delete)
- Analysis operations (read, write, delete)
- User profile access (read own)

### Viewer Role

- **Read-only access**
- Document viewing
- Analysis viewing
- User profile access (read own)

## Security Best Practices

### Token Security

- Access tokens are short-lived (15 minutes)
- Refresh tokens are long-lived but revocable
- All tokens include unique identifiers (JTI)
- Token rotation on refresh

### Password Security

- Argon2 hashing with secure parameters
- Strong password requirements
- Password change forces re-authentication

### File Upload Security

- File type validation
- Size limits enforced
- Content hashing for deduplication
- Secure file storage

### Rate Limiting

- Per-user and per-IP limits
- Different limits for different operations
- Automatic retry-after headers
- Redis-backed for scalability

### Audit Logging

- All user actions logged
- IP address and user agent tracking
- Success/failure status
- Detailed error information

## Error Handling

### Authentication Errors

- `401 Unauthorized`: Invalid or expired token
- `403 Forbidden`: Insufficient permissions
- `429 Too Many Requests`: Rate limit exceeded

### Validation Errors

- `400 Bad Request`: Invalid input data
- `422 Unprocessable Entity`: Validation errors

### Server Errors

- `500 Internal Server Error`: Unexpected errors
- Comprehensive error logging
- User-friendly error messages

## Monitoring and Observability

### Health Checks

- Database connectivity
- Redis connectivity
- System component status
- User and table counts

### Audit Logs

- User authentication events
- Document operations
- Analysis requests
- Administrative actions
- Error events

### Rate Limiting Metrics

- Request counts per user/IP
- Rate limit violations
- Retry-after headers
- Redis connection status

## Development and Testing

### Database Management

```bash
# Check database health
python setup.py health

# Reset database (WARNING: deletes all data)
python database.py reset

# Create additional admin users
python setup.py admin
```

### Testing Authentication

```bash
# Register a new user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"TestPass123!"}'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=TestPass123!"

# Use token for protected endpoint
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

## Production Considerations

### Security

- Use strong JWT secrets (32+ characters)
- Enable HTTPS in production
- Configure proper CORS origins
- Use environment-specific database credentials
- Enable Redis authentication

### Performance

- Configure database connection pooling
- Use Redis clustering for high availability
- Monitor rate limiting metrics
- Implement proper logging levels

### Monitoring

- Set up health check monitoring
- Monitor authentication failure rates
- Track rate limiting violations
- Monitor database and Redis performance

## Troubleshooting

### Common Issues

#### Database Connection Errors

- Check DATABASE_URL format
- Ensure PostgreSQL is running
- Verify database exists and user has permissions

#### Redis Connection Errors

- Check REDIS_URL format
- Ensure Redis is running
- Verify Redis authentication if configured

#### JWT Token Errors

- Verify JWT_SECRET is set and strong
- Check token expiration settings
- Ensure system clock is synchronized

#### Rate Limiting Issues

- Check Redis connectivity
- Verify rate limit configuration
- Monitor Redis memory usage

### Debug Mode

Set `LOG_LEVEL=DEBUG` in environment for detailed logging.

## Support

For issues or questions about the authentication system:

1. Check the logs for detailed error information
2. Verify environment configuration
3. Test database and Redis connectivity
4. Review rate limiting settings
5. Check JWT token validity and expiration
