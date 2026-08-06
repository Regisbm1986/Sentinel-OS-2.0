# Copied from Sentinel OS backend/jobs/exceptions.py
class JobValidationError(Exception):
    pass

class JobParseError(Exception):
    pass

class JobScoringError(Exception):
    pass
