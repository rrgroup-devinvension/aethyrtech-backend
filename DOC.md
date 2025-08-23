# API Documentation

This file documents the main API endpoints for the AethyrTech backend, including request and response examples.

---

## Authentication

### Login

**POST** `/api/auth/login/`

**Request:**

```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response:**

```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

---

### Refresh Token

**POST** `/api/auth/refresh/`

**Request:**

```json
{
  "refresh": "<jwt_refresh_token>"
}
```

**Response:**

```json
{
  "access": "<new_jwt_access_token>"
}
```

---

## Users

### Register

**POST** `/api/users/register/`

**Request:**

```json
{
  "email": "newuser@example.com",
  "password": "your_password",
  "name": "New User"
}
```

**Response:**

```json
{
  "id": 2,
  "email": "newuser@example.com",
  "name": "New User"
}
```

---

### Get Profile

**GET** `/api/users/profile/`

**Headers:**  
`Authorization: Bearer <jwt_access_token>`

**Response:**

```json
{
  "id": 2,
  "email": "newuser@example.com",
  "name": "New User"
}
```

---

## Brands

### List Brands

**GET** `/api/brands/`

**Headers:**  
`Authorization: Bearer <jwt_access_token>`

**Response:**

```json
[
  {
    "id": 1,
    "name": "Brand A",
    "description": "Description of Brand A"
  },
  {
    "id": 2,
    "name": "Brand B",
    "description": "Description of Brand B"
  }
]
```

---

### Create Brand

**POST** `/api/brands/`

**Headers:**  
`Authorization: Bearer <jwt_access_token>`

**Request:**

```json
{
  "name": "Brand C",
  "description": "Description of Brand C"
}
```

**Response:**

```json
{
  "id": 3,
  "name": "Brand C",
  "description": "Description of Brand C"
}
```

---

## Example JSON POST Endpoint

**POST** `/api/json-post/`

**Request:**

```json
{
  "key": "value"
}
```

**Response:**

```json
{
  "status": "success",
  "received": {
    "key": "value"
  }
}
```

---

## Error Response Format

**Response:**

```json
{
  "error": "Error message"
}
```

---

> For more details, refer to the code in each app or ask for specific endpoint documentation.
