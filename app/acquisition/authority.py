from enum import Enum


class SourceAuthority(str, Enum):
    """
    Authority classification asserted at acquisition time.

    Authority describes the institutional standing of the source, not whether
    any particular claim in the source is correct.
    """

    INSTITUTIONAL_PRIMARY = "institutional_primary"
    STATE_AUTHORITY = "state_authority"
    FEDERAL_AUTHORITY = "federal_authority"
    ACCREDITATION_AUTHORITY = "accreditation_authority"
    PEER_INSTITUTION = "peer_institution"
    EXTERNAL_SECONDARY = "external_secondary"
    USER_SUPPLIED = "user_supplied"
    UNKNOWN = "unknown"
