# REST API Documentation

## Authentication

All API requests require a valid JWT token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

Tokens expire after 24 hours. Use the `/auth/refresh` endpoint to obtain a new token.

## Endpoints

### GET /api/v1/users

List all users with pagination support.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number |
| limit | integer | 20 | Results per page |
| sort | string | created_at | Sort field |
| filter | string | - | Filter expression |

**Response:**
```json
{
  "data": [{"id": 1, "username": "john", "email": "john@example.com"}],
  "pagination": {"page": 1, "limit": 20, "total": 150, "pages": 8}
}
```

### POST /api/v1/users

Create a new user account.

**Request Body:**
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Validation Rules:**
- username: required, 3-50 characters
- email: required, valid email format
- password: required, minimum 8 characters

**Response:** 201 Created with user object (excluding password).

### DELETE /api/v1/users/:id

Delete a user account. Requires admin role.

**Response:** 200 OK with confirmation message.

## Error Handling

All errors follow a consistent format:

```json
{
  "error": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE",
  "details": {}
}
```

**Common Error Codes:**
- 400: Validation error
- 401: Missing authentication
- 403: Insufficient permissions
- 404: Resource not found
- 409: Conflict (duplicate resource)
- 429: Rate limit exceeded
- 500: Internal server error

## Rate Limiting

API requests are limited to 100 requests per minute per IP address. When the limit is exceeded, the API returns a 429 status code with a `Retry-After` header indicating seconds until the limit resets.

## Webhooks

Configure webhooks to receive real-time notifications for events:

- `user.created` - New user registration
- `user.deleted` - User account deletion
- `payment.completed` - Successful payment
- `payment.failed` - Failed payment attempt

Webhook payloads are signed with HMAC-SHA256 using your webhook secret.
