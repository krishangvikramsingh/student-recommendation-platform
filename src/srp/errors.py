class PlatformError(Exception):
    message = "The request could not be completed."


class DuplicateAccount(PlatformError):
    message = "An account with this email already exists."


class InvalidCollegeEmail(PlatformError):
    message = "Please use your college email address."


class InvalidCredentials(PlatformError):
    message = "Incorrect email or password."


class AccountLocked(PlatformError):
    message = "Too many failed attempts. Try again in 15 minutes."


class AccountSuspended(PlatformError):
    message = "This account has been suspended. Contact an administrator."


class NotVerified(PlatformError):
    message = "Complete college verification before posting reviews."


class NotAuthorised(PlatformError):
    message = "You do not have permission to do this."


class InvalidReview(PlatformError):
    message = "The review could not be accepted."


class DuplicateReview(PlatformError):
    message = "You have already reviewed this place."


class DuplicateReport(PlatformError):
    message = "You have already reported this review."


class InvalidInput(PlatformError):
    message = "Some fields are missing or invalid."


class NotFound(PlatformError):
    message = "The requested item does not exist."


class EmailNotVerified(PlatformError):
    message = "Please confirm your email address first. Check your inbox for the verification link."


class InvalidToken(PlatformError):
    message = "This link is invalid or has expired. Request a new one."


class RateLimited(PlatformError):
    message = "Too many attempts. Please wait a moment and try again."

    def __init__(self, retry_after=60):
        super().__init__(retry_after)
        self.retry_after = retry_after
