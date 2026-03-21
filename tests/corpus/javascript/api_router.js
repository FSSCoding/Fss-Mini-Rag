/**
 * API Router - Express-style route handling for REST endpoints.
 *
 * Handles user CRUD operations, authentication middleware,
 * rate limiting, and request validation.
 */

const express = require('express');
const router = express.Router();

// Rate limiting configuration
const RATE_LIMIT_WINDOW = 60 * 1000; // 1 minute
const MAX_REQUESTS_PER_WINDOW = 100;
const requestCounts = new Map();

/**
 * Rate limiting middleware.
 * Tracks requests per IP address and blocks excessive traffic.
 * Returns 429 Too Many Requests when limit exceeded.
 */
function rateLimiter(req, res, next) {
    const clientIp = req.ip || req.connection.remoteAddress;
    const now = Date.now();

    if (!requestCounts.has(clientIp)) {
        requestCounts.set(clientIp, { count: 1, windowStart: now });
        return next();
    }

    const clientData = requestCounts.get(clientIp);

    if (now - clientData.windowStart > RATE_LIMIT_WINDOW) {
        clientData.count = 1;
        clientData.windowStart = now;
        return next();
    }

    clientData.count++;
    if (clientData.count > MAX_REQUESTS_PER_WINDOW) {
        return res.status(429).json({
            error: 'Too many requests',
            retryAfter: Math.ceil((RATE_LIMIT_WINDOW - (now - clientData.windowStart)) / 1000)
        });
    }

    next();
}

/**
 * Authentication middleware.
 * Validates JWT tokens from Authorization header.
 * Attaches decoded user data to request object.
 */
function authMiddleware(req, res, next) {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'Missing or invalid authorization header' });
    }

    const token = authHeader.substring(7);

    try {
        const decoded = validateToken(token);
        req.user = decoded;
        next();
    } catch (error) {
        return res.status(403).json({ error: 'Invalid or expired token' });
    }
}

/**
 * Request validation middleware.
 * Validates request body against a schema definition.
 */
function validateRequest(schema) {
    return (req, res, next) => {
        const errors = [];

        for (const [field, rules] of Object.entries(schema)) {
            const value = req.body[field];

            if (rules.required && (value === undefined || value === null)) {
                errors.push(`${field} is required`);
                continue;
            }

            if (value !== undefined && rules.type && typeof value !== rules.type) {
                errors.push(`${field} must be of type ${rules.type}`);
            }

            if (value && rules.minLength && value.length < rules.minLength) {
                errors.push(`${field} must be at least ${rules.minLength} characters`);
            }

            if (value && rules.maxLength && value.length > rules.maxLength) {
                errors.push(`${field} must be at most ${rules.maxLength} characters`);
            }
        }

        if (errors.length > 0) {
            return res.status(400).json({ errors });
        }

        next();
    };
}

// User schema for validation
const userSchema = {
    username: { required: true, type: 'string', minLength: 3, maxLength: 50 },
    email: { required: true, type: 'string' },
    password: { required: true, type: 'string', minLength: 8 }
};

/**
 * GET /users - List all users with pagination.
 * Supports query parameters: page, limit, sort, filter.
 */
router.get('/users', authMiddleware, rateLimiter, async (req, res) => {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 20;
    const sort = req.query.sort || 'created_at';

    try {
        const users = await UserModel.find()
            .sort(sort)
            .skip((page - 1) * limit)
            .limit(limit);

        const total = await UserModel.countDocuments();

        res.json({
            data: users,
            pagination: {
                page,
                limit,
                total,
                pages: Math.ceil(total / limit)
            }
        });
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch users' });
    }
});

/**
 * POST /users - Create a new user account.
 * Validates input, hashes password, sends welcome email.
 */
router.post('/users', validateRequest(userSchema), async (req, res) => {
    const { username, email, password } = req.body;

    try {
        const existing = await UserModel.findOne({ email });
        if (existing) {
            return res.status(409).json({ error: 'Email already registered' });
        }

        const hashedPassword = await bcrypt.hash(password, 12);
        const user = new UserModel({
            username,
            email,
            password: hashedPassword,
            created_at: new Date()
        });

        await user.save();
        await sendWelcomeEmail(email, username);

        res.status(201).json({
            id: user._id,
            username: user.username,
            email: user.email
        });
    } catch (error) {
        res.status(500).json({ error: 'Failed to create user' });
    }
});

/**
 * DELETE /users/:id - Delete a user account.
 * Requires admin role. Soft-deletes by default.
 */
router.delete('/users/:id', authMiddleware, async (req, res) => {
    if (req.user.role !== 'admin') {
        return res.status(403).json({ error: 'Admin access required' });
    }

    try {
        const user = await UserModel.findByIdAndUpdate(
            req.params.id,
            { deleted: true, deleted_at: new Date() },
            { new: true }
        );

        if (!user) {
            return res.status(404).json({ error: 'User not found' });
        }

        res.json({ message: 'User deleted successfully' });
    } catch (error) {
        res.status(500).json({ error: 'Failed to delete user' });
    }
});

module.exports = router;
