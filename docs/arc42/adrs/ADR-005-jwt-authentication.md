# ADR 005: JWT Authentication

## Status

Accepted

## Context

The eRechnung system requires a secure, scalable authentication mechanism for its APIs that:
- Supports stateless authentication
- Works well with RESTful APIs
- Provides sufficient security
- Handles authorization efficiently
- Supports integration with different client applications
- Scales horizontally

## Decision

We will use JSON Web Token (JWT) based authentication for securing the eRechnung APIs.

## Rationale

- **Stateless Architecture**: JWTs enable stateless authentication, eliminating the need to store session data on the server, which simplifies scaling and reduces database load.

- **Self-Contained**: JWTs contain all necessary information about the user, including identity and authorization claims, reducing the need for additional database queries.

- **Cross-Domain Support**: JWTs work well across different domains, making them suitable for distributed systems and microservices.

- **Django REST Framework Integration**: DRF provides built-in support for JWT authentication through libraries like `djangorestframework-simplejwt`.

- **Industry Standard**: JWT is a widely adopted standard (RFC 7519) with implementations in many languages and frameworks.

- **Fine-grained Authorization**: Claims within JWTs can be used to implement detailed permission controls.

- **Expiration Control**: JWTs have built-in expiration mechanisms, improving security through token lifecycle management.

## Consequences

### Positive

- Simplified authentication flow for API clients
- Reduced database queries for authentication checks
- Better scalability due to stateless nature
- Consistent authentication mechanism across all APIs
- Support for mobile apps and SPAs

### Negative

- Cannot invalidate individual tokens before expiration without additional infrastructure
- Token size can become large if too many claims are included
- Need to carefully manage secret keys

### Risks

- Improper implementation could lead to security vulnerabilities
- Need to ensure proper token expiration and refresh mechanisms
- Must protect against XSS and CSRF attacks despite using tokens
- Token leakage risks if not properly secured in transmission and storage

## Alternatives Considered

- **Session-based Authentication**: Rejected due to scalability concerns and stateful nature.
- **OAuth 2.0**: Considered but deemed too complex for the current requirements. May be adopted later for third-party integrations.
- **API Keys**: Rejected due to limitations in user-specific authentication and authorization granularity.

## Implementation Details

- **Library**: We will use `djangorestframework-simplejwt` for JWT implementation.
- **Token Lifetime**: Access tokens will have a short lifetime (15-60 minutes) with refresh tokens for obtaining new access tokens.
- **Storage**: Tokens will be stored in HttpOnly cookies or secure local storage on the client side.
- **Claims**: Will include user ID, roles, and permissions in the token payload.

## References

- [JSON Web Tokens](https://jwt.io/)
- [RFC 7519](https://tools.ietf.org/html/rfc7519)
- [djangorestframework-simplejwt Documentation](https://django-rest-framework-simplejwt.readthedocs.io/)
