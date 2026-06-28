from rest_framework.throttling import AnonRateThrottle


class OTPRequestRateThrottle(AnonRateThrottle):
    """Rate limiting for OTP request endpoint - 5 requests per hour per IP"""
    rate = '20/hour'
    
    scope = 'otp_request'


class OTPVerifyRateThrottle(AnonRateThrottle):
    """Rate limiting for OTP verify endpoint - 20 requests per hour per IP"""
    rate = '40/hour'
    scope = 'otp_verify'
